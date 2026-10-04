#!/usr/bin/env python3
"""Dispatch the bounded engineering source-export exercise after lease admission."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


PROJECT = Path("/home/user/src/colour-index-compression")
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v2"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/distribution-engineering-v2"
SOURCE_ROOT = PROJECT / "rust/cix-native"


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("distribution engineering dispatch requires CIX_RELEASE_LEASE=1")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse distribution engineering work root: {WORK}")

    command = [
        "/usr/bin/python3",
        str(SOURCE_ROOT / "packaging/export/engineering_export_job.py"),
        "--source-root", str(SOURCE_ROOT),
        "--manifest", str(SOURCE_ROOT / "packaging/export/source-allowlist.json"),
        "--provider-closure", str(JOB / "selected-provider-closure.json"),
        "--work-directory", str(WORK),
        "--cargo", "/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo",
        "--cmake", "/usr/bin/cmake",
        "--make", "/usr/bin/make",
        "--jobs", "2",
    ]
    environment = os.environ.copy()
    environment.update({
        "CARGO_BUILD_JOBS": "2",
        "CARGO_INCREMENTAL": "0",
        "CARGO_NET_OFFLINE": "true",
    })
    subprocess.run(command, cwd=PROJECT, env=environment, check=True)


if __name__ == "__main__":
    main()
