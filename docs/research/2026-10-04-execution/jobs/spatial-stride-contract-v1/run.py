#!/usr/bin/env python3
"""Lease-gated focused qualification for the CharLS row-stride guard."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import shutil
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
WORK = PROJECT / "benchmark-work/native-rc-check-v1/spatial-stride-contract-v1"
CURRENT_SOURCE = PROJECT / "rust/cix-native/codecs/spatial"
SOURCE = WORK / "source"
SDK = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], receipt: dict, label: str, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False, env=env)
    receipt["commands"].append({"label": label, "argv": command,
                                "returncode": result.returncode,
                                "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(f"{label} failed")


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse work root: {WORK}")
    WORK.mkdir(parents=True)
    shutil.copytree(CURRENT_SOURCE, SOURCE)
    required = [SOURCE / "CMakeLists.txt", SOURCE / "cix_spatial_bridge.cpp",
                SOURCE / "tests/spatial_stride_contract.cpp", SOURCE / "cix_spatial_bridge.h",
                SDK / "usr/lib/x86_64-linux-gnu/libcharls.so",
                SDK / "usr/lib/x86_64-linux-gnu/libopenjp2.so"]
    if not all(path.is_file() for path in required):
        raise RuntimeError("required CIX source or retained codec SDK is missing")
    build, prefix = WORK / "build", WORK / "prefix"
    receipt = {"schema": "cix-focused-spatial-stride-contract-v1", "status": "running",
               "source_sha256": {str(path.relative_to(PROJECT)): digest(path) for path in required[:4]},
               "sdk_sha256": {str(path.relative_to(PROJECT)): digest(path) for path in required[4:]},
               "commands": []}
    try:
        run(["cmake", "-S", str(SOURCE), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             f"-DCIX_SPATIAL_ROOT={SDK}", f"-DCMAKE_INSTALL_PREFIX={prefix}"], receipt, "configure")
        run(["cmake", "--build", str(build), "--parallel", "2"], receipt, "build")
        run(["cmake", "--install", str(build)], receipt, "install")
        executable = WORK / "spatial_stride_contract"
        run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
             str(SOURCE / "tests/spatial_stride_contract.cpp"), "-I", str(prefix / "include/cix"),
             "-L", str(prefix / "lib"), "-Wl,-rpath," + str(prefix / "lib"),
             "-lcix_spatial_bridge", "-o", str(executable)], receipt, "compile-contract")
        run([str(executable)], receipt, "execute-contract", {**os.environ, "LD_LIBRARY_PATH": str(SDK / "usr/lib/x86_64-linux-gnu")})
        receipt["contract_executable_sha256"] = digest(executable)
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
