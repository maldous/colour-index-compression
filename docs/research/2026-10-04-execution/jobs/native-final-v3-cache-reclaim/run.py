#!/usr/bin/env python3
"""Preserve the one v2 Cargo metadata delta before reclaiming its duplicate cache."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[5]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
OUT = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1"
COPY = WORK / "native-final-source-v2/target"
RETAINED = WORK / "distribution-engineering-v4/target"
SOURCE_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/native-final-source-v2/receipt.json"
CLIPPY_STDERR = COPY.parent / "clippy.stderr.log"
PRESERVED = WORK / "preserved-native-final-source-v2-cache-v1"
PRESERVED_MEMBER = PRESERVED / "target/.rustc_info.json"
PRESERVED_MANIFEST = PRESERVED / "manifest.json"
RECEIPT = OUT / "receipt.json"
CHANGED_MEMBER = ".rustc_info.json"
EXPECTED_CLIPPY_STDERR_SHA256 = "b4d3cec97c193622370e0e01a1a330560618d24c538ec1f059d731254e71f483"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()}


def symlinks(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): os.readlink(path) for path in sorted(root.rglob("*"))
            if path.is_symlink()}


def inode_ids(root: Path) -> set[tuple[int, int]]:
    return {(path.stat().st_dev, path.stat().st_ino) for path in root.rglob("*")
            if path.is_file() and not path.is_symlink()}


def assert_no_active_writer() -> None:
    executable = shutil.which("lsof")
    if executable is None:
        raise RuntimeError("lsof is required to reject active duplicate-cache users")
    result = subprocess.run([executable, "+D", str(COPY)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inspect duplicate-cache users: " + result.stderr.strip())
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError("active duplicate-cache user prevents reclaim: " + result.stdout.splitlines()[0])


def source_expected() -> tuple[dict[str, str], str, str]:
    value = json.loads(SOURCE_RECEIPT.read_text(encoding="utf-8"))
    if value.get("status") != "fail" or value.get("phases", {}).get("clippy", {}).get("returncode") != 101:
        raise RuntimeError("v2 receipt is not the expected pre-compilation Clippy failure")
    expected = value.get("copied_lto_target", {}).get("files_sha256")
    if not isinstance(expected, dict) or not all(isinstance(key, str) and isinstance(item, str)
                                                 for key, item in expected.items()):
        raise RuntimeError("v2 receipt has no valid copied-target file hashes")
    if not CLIPPY_STDERR.is_file() or sha256(CLIPPY_STDERR) != EXPECTED_CLIPPY_STDERR_SHA256:
        raise RuntimeError("v2 Clippy configuration-failure evidence differs from the reviewed raw log")
    return dict(expected), sha256(SOURCE_RECEIPT), sha256(CLIPPY_STDERR)


def validate_delta(expected: dict[str, str]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    if not COPY.is_dir() or COPY.is_symlink() or COPY.resolve() != COPY:
        raise RuntimeError("duplicate target is not the exact non-symlink v2 cache root")
    if not RETAINED.is_dir() or RETAINED.is_symlink() or RETAINED.resolve() != RETAINED:
        raise RuntimeError("retained target is not the exact non-symlink immutable cache root")
    copied, retained = file_hashes(COPY), file_hashes(RETAINED)
    if retained != expected:
        raise RuntimeError("retained cache no longer equals the v2 copied-target receipt")
    if set(copied) != set(expected):
        raise RuntimeError("v2 duplicate has added or missing regular-file members")
    changed = {path: copied[path] for path in copied if copied[path] != expected[path]}
    if changed != {CHANGED_MEMBER: copied.get(CHANGED_MEMBER)}:
        raise RuntimeError("v2 duplicate has a delta beyond the sole permitted Cargo metadata member")
    if symlinks(COPY) != symlinks(RETAINED):
        raise RuntimeError("v2 duplicate symlink mapping differs from retained cache")
    if inode_ids(COPY) & inode_ids(RETAINED):
        raise RuntimeError("v2 duplicate shares a hardlink with retained evidence")
    return copied, retained, changed


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    receipt = {"status": "started", "removed": False, "copy": str(COPY), "retained": str(RETAINED)}
    may_write_receipt = not RECEIPT.exists()
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or COPY.parent.parent != WORK or RETAINED.parent.parent != WORK:
            raise RuntimeError("unexpected repository or cache roots")
        if PRESERVED.exists() or RECEIPT.exists():
            raise RuntimeError("refuse to overwrite prior preservation evidence")
        expected, source_receipt_sha, clippy_stderr_sha = source_expected()
        assert_no_active_writer()
        copied, retained, changed = validate_delta(expected)
        source = COPY / CHANGED_MEMBER
        detail = source.stat()
        PRESERVED_MEMBER.parent.mkdir(parents=True, mode=0o700)
        shutil.copy2(source, PRESERVED_MEMBER)
        if sha256(PRESERVED_MEMBER) != copied[CHANGED_MEMBER] or stat.S_IMODE(PRESERVED_MEMBER.stat().st_mode) != stat.S_IMODE(detail.st_mode):
            raise RuntimeError("preserved Cargo metadata member failed byte or mode verification")
        manifest = {
            "schema": "cix-native-final-v3-cache-reclaim-v1",
            "source_receipt": str(SOURCE_RECEIPT), "source_receipt_sha256": source_receipt_sha,
            "clippy_stderr": str(CLIPPY_STDERR), "clippy_stderr_sha256": clippy_stderr_sha,
            "copy": str(COPY), "retained": str(RETAINED), "expected_member_count": len(expected),
            "changed_member": {"path": CHANGED_MEMBER, "copy_sha256": copied[CHANGED_MEMBER],
                               "retained_sha256": retained[CHANGED_MEMBER], "bytes": detail.st_size,
                               "mode": stat.S_IMODE(detail.st_mode), "preserved_path": str(PRESERVED_MEMBER),
                               "preserved_sha256": sha256(PRESERVED_MEMBER)},
            "all_other_members_match_retained": True,
        }
        atomic_json(PRESERVED_MANIFEST, manifest)
        if not PRESERVED_MANIFEST.is_file():
            raise RuntimeError("preservation manifest was not retained")
        assert_no_active_writer()
        copied_after, retained_after, changed_after = validate_delta(expected)
        if copied_after != copied or retained_after != retained or changed_after != changed:
            raise RuntimeError("cache changed after preservation and before deletion")
        shutil.rmtree(COPY)
        if COPY.exists():
            raise RuntimeError("duplicate cache removal was incomplete")
        if file_hashes(RETAINED) != retained or sha256(PRESERVED_MEMBER) != copied[CHANGED_MEMBER]:
            raise RuntimeError("retained cache or preserved metadata changed after deletion")
        receipt.update({"status": "pass", "removed": str(COPY), "preserved_manifest": str(PRESERVED_MANIFEST),
                        "preserved_member": str(PRESERVED_MEMBER), "changed_member": manifest["changed_member"],
                        "source_receipt_sha256": source_receipt_sha, "clippy_stderr_sha256": clippy_stderr_sha,
                        "scope": "only v2 duplicate cache reclaimed after preserving the sole pre-compilation Cargo metadata delta"})
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        if may_write_receipt:
            atomic_json(RECEIPT, receipt)


if __name__ == "__main__":
    main()
