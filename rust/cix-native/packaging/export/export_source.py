#!/usr/bin/env python3
"""Materialise a validated, allowlisted CIX source tree; never publish or package it."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from validate_source_allowlist import (
    ENGINEERING_PROFILE,
    FULL_ENGINE_PROFILE,
    read_manifest,
    source_members,
    validate,
)


FORBIDDEN_EXPORT_TEXT = (
    "/home/user/",
    "benchmark-work/",
    "docs/research/",
    "colour-index-compression/",
)
EXPORT_TOOL_PREFIX = "rust/cix-native/packaging/export/"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def portable_members(native_root: Path, manifest: dict) -> tuple[Path, list[str]]:
    specification = manifest["portable_crate"]
    portable_root = (native_root / specification["source_relative_to_native"]).resolve()
    if not portable_root.is_dir():
        raise ValueError(f"portable crate source root is missing: {portable_root}")
    missing = [
        relative for relative in specification["required_exact_files"]
        if not (portable_root / relative).is_file()
    ]
    if missing:
        raise ValueError("portable crate files missing: " + ", ".join(missing))
    allowed = specification["allowed_globs"]
    excluded_prefixes = specification["excluded_path_prefixes"]
    excluded_suffixes = tuple(specification["excluded_suffixes"])
    selected: list[str] = []
    unexpected: list[str] = []
    for path in sorted(portable_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(portable_root).as_posix()
        if any(relative == prefix or relative.startswith(f"{prefix}/")
               for prefix in excluded_prefixes):
            continue
        if relative.endswith(excluded_suffixes):
            continue
        if any(relative == pattern or
               (pattern.endswith("/**") and relative.startswith(pattern[:-2]))
               for pattern in allowed):
            selected.append(relative)
        else:
            unexpected.append(relative)
    if unexpected:
        raise ValueError("unallowlisted portable source files: " + ", ".join(unexpected))
    return portable_root, selected


def copy_members(source_root: Path, destination_root: Path,
                 members: list[str], digests: dict[str, str], prefix: str) -> None:
    for relative in members:
        source = source_root / relative
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        digests[f"{prefix}/{relative}"] = file_digest(destination)


def relocate_member_release_profile(native_manifest: Path) -> None:
    """Move the qualified profile declaration to the generated workspace root.

    Cargo ignores package profiles once a crate is a workspace member. The
    maintained standalone manifest stays unchanged; this exact export rewrite
    prevents an ignored-profile warning while preserving the same three values
    in ROOT-Cargo.toml.in.
    """
    profile = """[profile.release-lto]\ninherits = \"release\"\nlto = true\ncodegen-units = 1\n"""
    content = native_manifest.read_text(encoding="utf-8")
    if not content.endswith(profile):
        raise ValueError("native release-lto profile no longer matches export contract")
    native_manifest.write_text(content.removesuffix(profile), encoding="utf-8")


def sanitize_exported_provider_notice_manifest(exported_root: Path, digests: dict[str, str]) -> None:
    """Remove private evidence locations while retaining provider identity inputs."""
    notices_root = exported_root / "rust/cix-native/packaging/notices"
    notice_path = notices_root / "provider-notices.json"
    if notice_path.is_file():
        document = json.loads(notice_path.read_text(encoding="utf-8"))
        document.pop("closure", None)
        providers = document.get("providers")
        if isinstance(providers, dict):
            for provider in providers.values():
                if isinstance(provider, dict):
                    provider.pop("source_receipt", None)
        document["export_note"] = (
            "Private evidence locations are excluded from this source export. "
            "Provider identities, notice hashes, and unresolved items are retained."
        )
        notice_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        digests["rust/cix-native/packaging/notices/provider-notices.json"] = file_digest(notice_path)

    provenance_path = notices_root / "provider-provenance-v3.json"
    if provenance_path.is_file():
        document = json.loads(provenance_path.read_text(encoding="utf-8"))
        selected = document.get("selected_closure")
        if isinstance(selected, dict):
            selected.pop("path", None)
        evidence = document.get("evidence_receipts")
        if isinstance(evidence, dict):
            for item in evidence.values():
                if isinstance(item, dict):
                    item.pop("path", None)
        identities = document.get("source_identities")
        if isinstance(identities, dict):
            for identity in identities.values():
                if isinstance(identity, dict):
                    identity.pop("local_tree", None)
        providers = document.get("providers")
        if isinstance(providers, dict):
            for provider in providers.values():
                if not isinstance(provider, dict):
                    continue
                source = provider.get("source")
                if isinstance(source, dict):
                    source.pop("local_root", None)
                    source.pop("receipt", None)
                    source.pop("cix_receipt", None)
                    source_build = source.get("cix_source_build_receipt")
                    if isinstance(source_build, dict):
                        source_build.pop("receipt", None)
        document["export_note"] = (
            "Private evidence paths are excluded from this source export. "
            "Selected hashes, public upstream identities, notice mappings, package "
            "identities, and unresolved obligations remain visible."
        )
        provenance_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        digests["rust/cix-native/packaging/notices/provider-provenance-v3.json"] = file_digest(provenance_path)


def reject_private_references(exported_root: Path) -> None:
    references: list[str] = []
    for path in sorted(exported_root.rglob("*")):
        if not path.is_file():
            continue
        if path.relative_to(exported_root).as_posix().startswith(EXPORT_TOOL_PREFIX):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(marker in text for marker in FORBIDDEN_EXPORT_TEXT):
            references.append(path.relative_to(exported_root).as_posix())
    if references:
        raise ValueError(
            "export contains private checkout or research references: " +
            ", ".join(references)
        )


def materialise(source_root: Path, manifest_path: Path, output_directory: Path,
                profile: str) -> Path:
    manifest = read_manifest(manifest_path)
    report = validate(source_root, manifest, profile)
    source_root = source_root.resolve()
    output_directory = output_directory.resolve()
    if output_directory.exists():
        raise ValueError(f"output directory already exists: {output_directory}")
    if output_directory == source_root or source_root in output_directory.parents:
        raise ValueError("output directory must not be inside the source root")

    version = manifest["export_prefix"].format(version=manifest.get("version", "0.1.0"))
    exported_root = output_directory / version
    exported_root.mkdir(parents=True)
    try:
        members = source_members(source_root, manifest)
        digests: dict[str, str] = {}
        native_destination = exported_root / "rust" / "cix-native"
        copy_members(source_root, native_destination, members, digests, "rust/cix-native")
        relocate_member_release_profile(native_destination / "Cargo.toml")
        digests["rust/cix-native/Cargo.toml"] = file_digest(native_destination / "Cargo.toml")
        portable_root, portable = portable_members(source_root, manifest)
        portable_destination = exported_root / "rust" / "cix-portable"
        copy_members(portable_root, portable_destination, portable, digests, "rust/cix-portable")

        templates = source_root / "packaging" / "export"
        root_files = {
            "Cargo.toml": "ROOT-Cargo.toml.in",
            "Makefile": "ROOT-Makefile.in",
            "README.md": "ROOT-README.md.in",
        }
        for destination_name, template_name in root_files.items():
            destination = exported_root / destination_name
            shutil.copy2(templates / template_name, destination)
            digests[destination_name] = file_digest(destination)
        for legal in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "THIRD_PARTY_NOTICES_RUST.md"):
            destination = exported_root / legal
            shutil.copy2(source_root / legal, destination)
            digests[legal] = file_digest(destination)

        # Debian source tools require this conventional root directory. The
        # maintained recipe remains under packaging/ in the maintained source tree;
        # this is a byte-for-byte export projection, not a second recipe.
        debian_recipe = native_destination / "packaging" / "debian"
        if not debian_recipe.is_dir():
            raise ValueError("validated source export lacks packaging/debian")
        shutil.copytree(debian_recipe, exported_root / "debian")
        sanitize_exported_provider_notice_manifest(exported_root, digests)
        reject_private_references(exported_root)
    except Exception:
        shutil.rmtree(output_directory)
        raise

    record = {
        "schema": "cix-native-materialised-source-export-v1",
        "profile": profile,
        "dependency_closure_status": report["dependency_closure_status"],
        "member_count": len(members) + len(portable),
        "members_sha256": digests,
        "layout_projections": {
            "debian": "rust/cix-native/packaging/debian copied byte-for-byte for dpkg-source",
            "workspace": "native and portable crates retained under rust/",
            "release_lto_profile": (
                "The canonical standalone native manifest retains its profile; "
                "the export moves its exact declaration to the generated workspace root "
                "because Cargo only reads workspace-root profiles."
            )
        },
        "source_export_only": True,
        "publication": "not performed",
        "archive": "not created",
    }
    (exported_root / "EXPORT-MANIFEST.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return exported_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True,
                        help="new directory that will contain cix-{version}")
    parser.add_argument("--profile", default=FULL_ENGINE_PROFILE,
                        choices=("source-members", "native-core-optional", ENGINEERING_PROFILE, FULL_ENGINE_PROFILE))
    args = parser.parse_args()
    root = materialise(args.source_root, args.manifest, args.output_directory, args.profile)
    print(root)


if __name__ == "__main__":
    main()
