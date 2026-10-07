#!/usr/bin/env python3
"""Preserve the terminal PAQ supervisor target before lease-authorized reclaim."""
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
TARGET = WORK / "paq-supervisor-groups-v1/target"
PRESERVED = WORK / "preserved-paq-supervisor-groups-v1-target-v1"
JOB = Path(__file__).resolve().parent
RECEIPT = JOB / "receipt.json"
V2_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/paq-supervisor-groups-v2/receipt.json"
V2_RAW_RESULT = V2_RECEIPT.parent / "raw/result.json"
HELPER_PATH = ROOT / "docs/research/2026-10-04-execution/jobs/preserve-native-final-v3-target-v1/run.py"
ARCHIVE_CAP = 60_000_000
MANIFEST_CAP = 4_000_000
SHARED_LIMIT = 4_000_000_000
METADATA_MARGIN = 1_048_576
DEBUG_CIX = TARGET / "debug/cix"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location("cix_paq_target_preservation", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load reviewed preservation helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_receipt(receipt: dict[str, object]) -> None:
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def terminal_v2_authority() -> tuple[str, dict[str, object]]:
    if not V2_RECEIPT.is_file() or not V2_RAW_RESULT.is_file():
        raise RuntimeError("terminal v2 authority is absent")
    receipt = json.loads(V2_RECEIPT.read_text())
    raw = json.loads(V2_RAW_RESULT.read_text())
    if receipt.get("status") != "pass":
        raise RuntimeError("v2 continuation is not a terminal pass")
    phases = receipt.get("phases", {})
    required = ("build-cix-v2", "supervisor-v2", "provider-dispatch-v2")
    if any(phases.get(name, {}).get("returncode") != 0 for name in required):
        raise RuntimeError("v2 continuation lacks a passing required phase")
    if raw.get("exit_code") != 0 or raw.get("child_status", {}).get("child_exit_code") != 0:
        raise RuntimeError("v2 outer execution is not a terminal pass")
    cix = receipt.get("providers_before", {}).get("cix", {})
    expected = cix.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise RuntimeError("v2 providers_before.cix.sha256 is absent")
    return expected, {
        "receipt_sha256": sha256(V2_RECEIPT),
        "raw_result_sha256": sha256(V2_RAW_RESULT),
        "required_phases": list(required),
        "providers_before_cix": cix,
    }


@contextlib.contextmanager
def selected_target_helper(helper):
    names = ("WORK", "TARGET", "PRESERVED", "ARCHIVE", "MANIFEST",
             "ARCHIVE_CAP", "MANIFEST_CAP", "RETAINED_BINARIES")
    original = {name: getattr(helper, name) for name in names}
    try:
        helper.WORK = WORK
        helper.TARGET = TARGET
        helper.PRESERVED = PRESERVED
        helper.ARCHIVE = PRESERVED / "paq-supervisor-groups-target.tar.xz"
        helper.MANIFEST = PRESERVED / "paq-supervisor-groups-target.manifest.json"
        helper.ARCHIVE_CAP = ARCHIVE_CAP
        helper.MANIFEST_CAP = MANIFEST_CAP
        helper.RETAINED_BINARIES = {}
        yield
    finally:
        for name, value in original.items():
            setattr(helper, name, value)


def main() -> int:
    receipt: dict[str, object] = {
        "status": "started",
        "selected_root": str(TARGET),
        "preservation_root": str(PRESERVED),
        "removed": False,
        "excluded_from_reclaim": [str(TARGET.parent / name) for name in ("source", "tmp")],
    }
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK != ROOT / "benchmark-work/native-rc-check-v1":
            raise RuntimeError("unexpected repository or shared work root")
        if PRESERVED.exists() or RECEIPT.exists():
            raise RuntimeError("refusing to overwrite preservation evidence")
        if not TARGET.is_dir() or TARGET.is_symlink() or TARGET.resolve() != TARGET:
            raise RuntimeError("selected PAQ target is absent or not a direct directory")
        if not DEBUG_CIX.is_file() or not HELPER_PATH.is_file():
            raise RuntimeError("required target binary or preservation helper is absent")

        expected_cix_sha, authority = terminal_v2_authority()
        if sha256(DEBUG_CIX) != expected_cix_sha:
            raise RuntimeError("debug cix differs from v2 providers_before.cix.sha256")
        helper = load_helper()
        with selected_target_helper(helper):
            cix_bytes = DEBUG_CIX.stat().st_size
            if helper.work_bytes() + ARCHIVE_CAP + MANIFEST_CAP + cix_bytes + METADATA_MARGIN > SHARED_LIMIT:
                raise RuntimeError("bounded archive and retained cix cannot be admitted within shared work limit")
            helper.assert_no_active_writer()
            manifest, links = helper.collect_manifest()
            entry = next((row for row in manifest["entries"] if row["path"] == "debug/cix"), None)
            if entry is None or entry.get("type") != "file" or entry.get("sha256") != expected_cix_sha:
                raise RuntimeError("target manifest does not bind the v2 debug cix")
            inputs = {
                str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                str(HELPER_PATH.relative_to(ROOT)): sha256(HELPER_PATH),
                str(V2_RECEIPT.relative_to(ROOT)): authority["receipt_sha256"],
                str(V2_RAW_RESULT.relative_to(ROOT)): authority["raw_result_sha256"],
            }
            receipt.update({"authority": authority, "input_sha256": inputs,
                            "selected_allocated_bytes": manifest["selected_allocated_bytes"],
                            "member_count": len(manifest["entries"])})

            PRESERVED.mkdir(mode=0o700)
            preserved_cix = PRESERVED / "cix"
            shutil.copy2(DEBUG_CIX, preserved_cix)
            if sha256(preserved_cix) != expected_cix_sha or stat.S_IMODE(preserved_cix.stat().st_mode) != entry["mode"]:
                raise RuntimeError("separate debug cix preservation differs from v2 authority")
            helper.write_archive(manifest, links)
            archive_sha256 = helper.verify_archive(manifest)
            if helper.ARCHIVE.stat().st_size > ARCHIVE_CAP or helper.MANIFEST.stat().st_size > MANIFEST_CAP:
                raise RuntimeError("preservation output exceeds declared archive or manifest cap")
            helper.assert_no_active_writer()
            if not helper.unchanged(manifest):
                raise RuntimeError("PAQ supervisor target changed after archive verification")
            current_inputs = {
                str(Path(__file__).relative_to(ROOT)): sha256(Path(__file__)),
                str(HELPER_PATH.relative_to(ROOT)): sha256(HELPER_PATH),
                str(V2_RECEIPT.relative_to(ROOT)): sha256(V2_RECEIPT),
                str(V2_RAW_RESULT.relative_to(ROOT)): sha256(V2_RAW_RESULT),
            }
            if current_inputs != inputs:
                raise RuntimeError("preservation runner, helper, or terminal authority changed during operation")

            before_reclaim = helper.work_bytes()
            shutil.rmtree(TARGET)
            if TARGET.exists():
                raise RuntimeError("PAQ supervisor target removal was incomplete")
            after_reclaim = helper.work_bytes()
            receipt.update({
                "status": "pass",
                "removed": True,
                "archive": str(helper.ARCHIVE),
                "archive_sha256": archive_sha256,
                "archive_bytes": helper.ARCHIVE.stat().st_size,
                "manifest": str(helper.MANIFEST),
                "manifest_sha256": sha256(helper.MANIFEST),
                "separate_debug_cix": {
                    "path": str(preserved_cix), "sha256": sha256(preserved_cix),
                    "bytes": preserved_cix.stat().st_size, "mode": entry["mode"],
                    "authority": "v2.providers_before.cix.sha256",
                },
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
