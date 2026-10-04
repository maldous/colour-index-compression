#!/usr/bin/env python3
"""Stage only receipt-verified PAQ source files for an engineering export.

The source receipts identify the exact upstream files used for the qualified
bridge builds. This tool deliberately does not copy a working tree: unrecorded
build products and local files are excluded from the export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any


VARIANTS = ("v215", "v216", "joint_discount", "store_state")
GPL2_SHA256 = "8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_relative_path(value: str) -> PurePosixPath:
    """Reject receipt paths that could escape a selected source root."""
    relative = PurePosixPath(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe receipt path: {value!r}")
    return relative


def regular_file(path: Path, label: str) -> Path:
    """Require a non-symlink regular input file."""
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a non-symlink regular file: {path}")
    return path


def load_receipted_files(receipt_path: Path, expected_sha256: str) -> dict[str, str]:
    """Read and validate one immutable source receipt's file map."""
    regular_file(receipt_path, "source receipt")
    actual_sha256 = sha256_file(receipt_path)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"source receipt hash mismatch for {receipt_path}: {actual_sha256}"
        )

    document = json.loads(receipt_path.read_text(encoding="utf-8"))
    files = document.get("vendor", {}).get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError(f"source receipt has no vendor.files map: {receipt_path}")

    verified: dict[str, str] = {}
    for relative_name, expected_file_sha256 in files.items():
        if not isinstance(relative_name, str) or not isinstance(expected_file_sha256, str):
            raise ValueError(f"malformed source receipt entry in {receipt_path}")
        checked_relative_path(relative_name)
        if len(expected_file_sha256) != 64:
            raise ValueError(f"invalid file digest in {receipt_path}: {relative_name}")
        verified[relative_name] = expected_file_sha256
    return verified


def verify_receipted_tree(source_root: Path, files: dict[str, str]) -> dict[str, Path]:
    """Verify all receipt members before any file is copied."""
    verified: dict[str, Path] = {}
    for relative_name in sorted(files):
        relative = checked_relative_path(relative_name)
        source = regular_file(source_root.joinpath(*relative.parts), "receipted source")
        actual_sha256 = sha256_file(source)
        expected_sha256 = files[relative_name]
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"source hash mismatch for {source}: expected {expected_sha256}, "
                f"got {actual_sha256}"
            )
        verified[relative_name] = source
    return verified


def copy_receipted_tree(
    destination: Path, verified_sources: dict[str, Path]
) -> dict[str, str]:
    """Copy exactly the already verified receipt members and bind their hashes."""
    staged_hashes: dict[str, str] = {}
    for relative_name in sorted(verified_sources):
        relative = checked_relative_path(relative_name)
        source = verified_sources[relative_name]
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_sha256 = sha256_file(target)
        source_sha256 = sha256_file(source)
        if copied_sha256 != source_sha256:
            raise ValueError(f"copied source hash mismatch for {target}")
        staged_hashes[relative_name] = copied_sha256
    return staged_hashes


def resolve_receipt(receipt_root: Path, value: object) -> Path:
    """Resolve a receipt path only within the declared project evidence root."""
    if not isinstance(value, str) or not value:
        raise ValueError("PAQ source entry has no source_receipt")
    relative = checked_relative_path(value)
    root = receipt_root.resolve()
    candidate = root.joinpath(*relative.parts).resolve()
    if root not in candidate.parents:
        raise ValueError(f"source receipt escapes declared evidence root: {value}")
    return candidate


def stage_variant(
    variant: str,
    entry: dict[str, Any],
    receipt_root: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Bind one PAQ source snapshot to its receipt and stage it."""
    source_value = entry.get("path")
    source = Path(source_value) if isinstance(source_value, str) else Path()
    if not source.is_absolute() or not source.is_dir() or source.is_symlink():
        raise ValueError(f"missing selected PAQ source root: {variant}")

    expected_receipt_sha256 = entry.get("source_receipt_sha256")
    if not isinstance(expected_receipt_sha256, str) or len(expected_receipt_sha256) != 64:
        raise ValueError(f"PAQ source receipt hash missing for {variant}")
    receipt = resolve_receipt(receipt_root, entry.get("source_receipt"))
    files = load_receipted_files(receipt, expected_receipt_sha256)

    destination = output_root / variant
    if destination.exists():
        raise ValueError(f"PAQ export destination already exists: {destination}")
    verified_sources = verify_receipted_tree(source, files)
    destination.mkdir(parents=True)
    staged_hashes = copy_receipted_tree(destination, verified_sources)

    expected_readme_sha256 = entry.get("readme_sha256")
    if staged_hashes.get("README.md") != expected_readme_sha256:
        raise ValueError(f"PAQ README identity mismatch: {variant}")
    return {
        "variant": variant,
        "source_receipt_sha256": expected_receipt_sha256,
        "readme_sha256": expected_readme_sha256,
        "bridge_sha256": entry.get("bridge_sha256"),
        "file_count": len(staged_hashes),
        "files": staged_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--gpl2-text", type=Path, required=True)
    args = parser.parse_args()

    closure = json.loads(args.closure.read_text(encoding="utf-8"))
    if closure.get("status") != "engineering_inputs_selected":
        raise ValueError("selected engineering closure required")
    roots = closure.get("paq_source_roots")
    if not isinstance(roots, dict):
        raise ValueError("engineering closure has no PAQ source roots")

    gpl_text = regular_file(args.gpl2_text.resolve(), "GPL-2 text")
    if sha256_file(gpl_text) != GPL2_SHA256:
        raise ValueError("expected GPL-2 text hash not supplied")

    output = args.export_root.resolve() / "third_party" / "paq"
    output.mkdir(parents=True, exist_ok=True)
    variants: list[dict[str, Any]] = []
    for variant in VARIANTS:
        entry = roots.get(variant)
        if not isinstance(entry, dict):
            raise ValueError(f"engineering closure missing PAQ variant: {variant}")
        variants.append(stage_variant(variant, entry, args.receipt_root, output))

    copied_gpl = output / "COPYING.GPL-2.0"
    shutil.copy2(gpl_text, copied_gpl)
    if sha256_file(copied_gpl) != GPL2_SHA256:
        raise ValueError("staged GPL-2 text hash mismatch")
    identity = {
        "schema": "cix-paq-engineering-source-identity-v2",
        "scope": (
            "Only receipt-verified selected PAQ source files and the declared GPL-2 "
            "text are staged. This is identity evidence, not a licence conclusion."
        ),
        "variants": variants,
        "gpl_text_sha256": GPL2_SHA256,
    }
    (output / "SOURCE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
