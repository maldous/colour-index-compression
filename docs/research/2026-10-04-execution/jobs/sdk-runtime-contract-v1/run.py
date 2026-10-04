#!/usr/bin/env python3
"""Dispatch the frozen SDK/runtime layout contract after toolchain admission."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
CHECK = PROJECT / "docs/research/2026-10-04-execution/jobs/sdk-runtime-contract-v1/check.py"
V4 = PROJECT / "benchmark-work/native-rc-check-v1/distribution-engineering-v4"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/sdk-runtime-contract-v1"


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    command = [
        "/usr/bin/python3", str(CHECK),
        "--sdk-source", str(PROJECT / "rust/cix-native/packaging/sdk"),
        "--runtime-source", str(PROJECT / "rust/cix-native/packaging/runtime"),
        "--unix-shared", str(V4 / "target/release-lto/libcix_native.so"),
        "--unix-static", str(V4 / "target/release-lto/libcix_native.a"),
        "--cix", str(V4 / "target/release-lto/cix"),
        "--provider-closure", str(PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"),
        "--work", str(WORK),
    ]
    subprocess.run(command, cwd=PROJECT, check=True)


if __name__ == "__main__":
    main()
