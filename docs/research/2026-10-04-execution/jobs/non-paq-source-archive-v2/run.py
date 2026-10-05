#!/usr/bin/env python3
"""Schedule the bounded streaming non-PAQ provider source-archive verification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


JOB = Path(__file__).resolve().parent
ROOT = JOB.parents[4]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
WORK_ROOT = ROOT / "benchmark-work/native-rc-check-v1"
SOURCE_INPUT_JOB = WORK_ROOT / "ubuntu-codec-source-inputs-v1"
OUTPUT = WORK_ROOT / "non-paq-provider-sources-v1.tar.gz"
RECEIPT = JOB / "receipt.json"
ARCHIVE_LIMIT = 250_000_000
RECEIPT_RESERVE = 4_000_000
SHARED_LIMIT = 4_000_000_000
NATIVE = ROOT / "rust/cix-native"
ARCHIVER = NATIVE / "packaging/export/archive_non_paq_provider_sources.py"
STAGER = NATIVE / "packaging/export/stage_non_paq_provider_sources.py"
METADATA = ROOT / "docs/research/2026-10-04-execution/reviews/non-paq-provider-sources-v1.json"
CLOSURE = ROOT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"
JXL_SOURCE = ROOT / "benchmark-work/references/libjxl-v0.12.0"
SPATIAL_SNAPSHOT = WORK_ROOT / "execution-spatial-counts-v2"
CODEC_ARCHIVES = WORK_ROOT / "codec-sdk-v1/archives"
NOTICES = NATIVE / "packaging/notices"
UBUNTU_MANIFEST = ROOT / "docs/research/2026-10-04-execution/jobs/ubuntu-codec-source-inputs-v1/sources.json"
UBUNTU_RECEIPT = SOURCE_INPUT_JOB / "receipt.json"
UBUNTU_DOWNLOADS = SOURCE_INPUT_JOB / "downloads"


def sha256(path: Path) -> str:
    """Hash a direct regular file."""
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"expected direct regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocated_bytes(root: Path) -> int:
    """Measure allocated shared work bytes once per inode, including directories."""
    total = 0
    seen: set[tuple[int, int]] = set()
    for path in (root, *root.rglob("*")):
        status = path.lstat()
        identity = (status.st_dev, status.st_ino)
        if identity not in seen:
            total += status.st_blocks * 512
            seen.add(identity)
    return total


def inputs() -> dict[str, str]:
    """Bind all scripts, maps, receipts, and notice inputs used by the archive."""
    files = (
        Path(__file__), ARCHIVER, STAGER, METADATA, CLOSURE, NOTICES / "provider-notices.json",
        UBUNTU_MANIFEST, UBUNTU_RECEIPT,
    )
    return {str(path.relative_to(ROOT)): sha256(path) for path in files}


def source_receipt_is_complete() -> None:
    """Require the exact prior source-input identity result before archive creation."""
    receipt = json.loads(UBUNTU_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "pass_source_inputs_retained_not_built":
        raise RuntimeError("Ubuntu source inputs are not retained under their successful receipt")
    if not UBUNTU_DOWNLOADS.is_dir() or UBUNTU_DOWNLOADS.is_symlink():
        raise RuntimeError("Ubuntu source download directory is unavailable")


def write_receipt(document: dict[str, Any]) -> None:
    """Retain a small result document for pass, block, or failure."""
    RECEIPT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    receipt: dict[str, Any] = {"schema": "cix-non-paq-source-archive-job-v2", "status": "started"}
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or not WORK_ROOT.is_dir() or OUTPUT.exists() or RECEIPT.exists():
            raise RuntimeError("unexpected repository/work root or existing archive evidence")
        source_receipt_is_complete()
        before = inputs()
        allocated = allocated_bytes(WORK_ROOT)
        admission = allocated + ARCHIVE_LIMIT + RECEIPT_RESERVE
        receipt.update({
            "input_sha256_before": before,
            "work_allocated_before": allocated,
            "archive_allowance_bytes": ARCHIVE_LIMIT,
            "receipt_reserve_bytes": RECEIPT_RESERVE,
            "shared_limit_bytes": SHARED_LIMIT,
            "admission_total_bytes": admission,
        })
        if admission > SHARED_LIMIT:
            receipt.update({"status": "blocked_storage", "reason": "bounded source archive cannot be admitted in shared work"})
            return 2
        command = [
            "/usr/bin/python3", str(ARCHIVER), "--metadata", str(METADATA), "--closure", str(CLOSURE),
            "--receipt-root", str(ROOT), "--jxl-source-root", str(JXL_SOURCE),
            "--spatial-snapshot-root", str(SPATIAL_SNAPSHOT), "--codec-archive-root", str(CODEC_ARCHIVES),
            "--notices-root", str(NOTICES), "--ubuntu-manifest", str(UBUNTU_MANIFEST),
            "--ubuntu-receipt", str(UBUNTU_RECEIPT), "--ubuntu-downloads-root", str(UBUNTU_DOWNLOADS),
            "--archive", str(OUTPUT), "--archive-byte-limit", str(ARCHIVE_LIMIT), "--receipt", str(WORK_ROOT / "non-paq-provider-sources-v1.receipt.json"),
        ]
        subprocess.run(command, check=True, stdin=subprocess.DEVNULL, timeout=840, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        archive_receipt = WORK_ROOT / "non-paq-provider-sources-v1.receipt.json"
        archive = json.loads(archive_receipt.read_text(encoding="utf-8"))
        if archive.get("status") != "pass_source_identity_archive_not_reproducible_build":
            raise RuntimeError("source archive did not retain its non-reproducibility status")
        if archive.get("member_count", 0) < 4100:
            raise RuntimeError("source archive did not retain the expected source-member closure")
        after = inputs()
        if after != before:
            raise RuntimeError("archive inputs changed during execution")
        final_allocated = allocated_bytes(WORK_ROOT)
        if final_allocated > SHARED_LIMIT:
            raise RuntimeError("source archive exceeded shared work limit")
        receipt.update({
            "status": "pass_source_identity_archive_not_reproducible_build",
            "input_sha256_after": after,
            "archive_receipt_sha256": sha256(archive_receipt),
            "archive_sha256": sha256(OUTPUT),
            "work_allocated_after": final_allocated,
        })
        return 0
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        write_receipt(receipt)


if __name__ == "__main__":
    raise SystemExit(main())
