#!/usr/bin/env python3
"""Preserve one completed Go module cache before lease-authorized reclaim."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys


ROOT = Path(__file__).resolve().parents[5]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
WORK = ROOT / "benchmark-work/native-rc-check-v1"
TARGET = WORK / "go-mod-cache"
PRESERVED = WORK / "preserved-go-module-cache-v1"
JOB = Path(__file__).resolve().parent
RECEIPT = JOB / "receipt.json"
ARCHIVE_CAP = 180_000_000
MANIFEST_CAP = 4_000_000
SHARED_LIMIT = 4_000_000_000
METADATA_MARGIN = 1_048_576
HELPER_PATH = ROOT / "docs/research/2026-10-04-execution/jobs/preserve-native-final-v3-target-v1/run.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location("cix_preservation_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load preserved-target helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_receipt(receipt: dict[str, object]) -> None:
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


@contextlib.contextmanager
def selected_cache_helper(helper):
    """Temporarily bind the reviewed archive helper to this cache only."""
    names = ("WORK", "TARGET", "PRESERVED", "ARCHIVE", "MANIFEST",
             "ARCHIVE_CAP", "MANIFEST_CAP", "RETAINED_BINARIES")
    original = {name: getattr(helper, name) for name in names}
    try:
        helper.WORK = WORK
        helper.TARGET = TARGET
        helper.PRESERVED = PRESERVED
        helper.ARCHIVE = PRESERVED / "go-mod-cache.tar.xz"
        helper.MANIFEST = PRESERVED / "go-mod-cache.manifest.json"
        helper.ARCHIVE_CAP = ARCHIVE_CAP
        helper.MANIFEST_CAP = MANIFEST_CAP
        helper.RETAINED_BINARIES = {}
        yield
    finally:
        for name, value in original.items():
            setattr(helper, name, value)


def restore_instructions(archive_sha256: str, manifest_sha256: str) -> str:
    return f"""# Go module cache restoration

This directory preserves the completed `go-mod-cache` that was reclaimed to
make room in the shared qualification work root. Any future Go job that would
reuse that cache must restore and verify it before using the cache path.

Expected archive SHA-256: `{archive_sha256}`
Expected manifest SHA-256: `{manifest_sha256}`

1. Verify the archive and manifest hashes above.
2. Extract `go-mod-cache.tar.xz` into a fresh, empty temporary directory. The
   archive contains a top-level `target/` directory because the reviewed
   preservation helper uses a generic target archive layout.
3. Verify the extracted member hashes, modes, symlinks, and hardlinks against
   `go-mod-cache.manifest.json` using the preservation verifier before reuse.
4. Move the verified extracted `target/` directory to
   `benchmark-work/native-rc-check-v1/go-mod-cache` without merging it into an
   existing directory.
5. Recheck that no Go process is using the restored path before a future job
   modifies it.

The archive is a cache recovery artifact. It is not a source, dependency, or
binary distribution.
"""


def main() -> int:
    receipt: dict[str, object] = {
        "status": "started",
        "selected_root": str(TARGET),
        "preservation_root": str(PRESERVED),
        "removed": False,
        "restore_required_before_future_go_cache_use": True,
        "limits": {
            "archive_bytes": ARCHIVE_CAP,
            "manifest_bytes": MANIFEST_CAP,
            "shared_work_bytes": SHARED_LIMIT,
        },
    }
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK != ROOT / "benchmark-work/native-rc-check-v1":
            raise RuntimeError("unexpected repository or shared work root")
        if PRESERVED.exists() or RECEIPT.exists():
            raise RuntimeError("refusing to overwrite preservation evidence")
        if not TARGET.is_dir() or TARGET.is_symlink() or TARGET.resolve() != TARGET:
            raise RuntimeError("selected Go module cache is absent or not a direct directory")
        if not HELPER_PATH.is_file():
            raise RuntimeError("reviewed preservation helper is absent")

        helper = load_helper()
        with selected_cache_helper(helper):
            if helper.work_bytes() + ARCHIVE_CAP + MANIFEST_CAP + METADATA_MARGIN > SHARED_LIMIT:
                raise RuntimeError("bounded archive output cannot be admitted within shared work limit")
            helper.assert_no_active_writer()
            manifest, links = helper.collect_manifest()
            manifest_bytes = helper.encoded_manifest(manifest)
            receipt["input_sha256"] = {
                str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                str(HELPER_PATH.relative_to(ROOT)): sha256(HELPER_PATH),
            }
            receipt["selected_allocated_bytes"] = manifest["selected_allocated_bytes"]
            receipt["member_count"] = len(manifest["entries"])

            PRESERVED.mkdir(mode=0o700)
            helper.write_archive(manifest, links)
            archive_sha256 = helper.verify_archive(manifest)
            manifest_sha256 = sha256(helper.MANIFEST)
            (PRESERVED / "RESTORE.md").write_text(
                restore_instructions(archive_sha256, manifest_sha256), encoding="utf-8")

            if helper.ARCHIVE.stat().st_size > ARCHIVE_CAP:
                raise RuntimeError("verified XZ archive exceeds its declared cap")
            if helper.MANIFEST.stat().st_size > MANIFEST_CAP:
                raise RuntimeError("verified manifest exceeds its declared cap")
            if helper.MANIFEST.read_bytes() != manifest_bytes:
                raise RuntimeError("written manifest differs from admitted manifest")
            helper.assert_no_active_writer()
            if not helper.unchanged(manifest):
                raise RuntimeError("Go module cache changed after archive verification")
            if {str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                str(HELPER_PATH.relative_to(ROOT)): sha256(HELPER_PATH)} != receipt["input_sha256"]:
                raise RuntimeError("preservation runner or helper changed during operation")

            preserved_size = sum(path.stat().st_size for path in PRESERVED.rglob("*") if path.is_file())
            if preserved_size > ARCHIVE_CAP + MANIFEST_CAP + METADATA_MARGIN:
                raise RuntimeError("preservation output exceeds its bounded allocation")
            before_reclaim = helper.work_bytes()
            # Go makes extracted module directories read-only. Original modes
            # are already verified in the archive; make only these selected
            # cache directories removable, without following any symlink.
            for entry in manifest["entries"]:
                if entry["type"] == "directory":
                    directory = TARGET / entry["path"]
                    os.chmod(directory, entry["mode"] | stat.S_IWUSR | stat.S_IXUSR)
            os.chmod(TARGET, stat.S_IMODE(TARGET.stat().st_mode) | stat.S_IWUSR | stat.S_IXUSR)
            shutil.rmtree(TARGET)
            if TARGET.exists():
                raise RuntimeError("Go module cache removal was incomplete")
            after_reclaim = helper.work_bytes()
            receipt.update({
                "status": "pass",
                "removed": True,
                "archive": str(helper.ARCHIVE),
                "archive_sha256": archive_sha256,
                "archive_bytes": helper.ARCHIVE.stat().st_size,
                "manifest": str(helper.MANIFEST),
                "manifest_sha256": manifest_sha256,
                "restore_instructions": str(PRESERVED / "RESTORE.md"),
                "preservation_output_bytes": preserved_size,
                "retained_work_before_reclaim_bytes": before_reclaim,
                "retained_work_after_reclaim_bytes": after_reclaim,
                "shared_headroom_after_reclaim_bytes": SHARED_LIMIT - after_reclaim,
                "archive_verification": "member order, hashes, modes, symbolic links, and hardlinks verified by reviewed helper",
                "external_hardlinks": "rejected by reviewed helper before archive creation and again before reclaim",
            })
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        write_receipt(receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
