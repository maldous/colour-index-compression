#!/usr/bin/env python3
"""Complete only the spatial bridge missing from bridge-portability-v1."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
V1_WORK = PROJECT / "benchmark-work/native-rc-check-v1/bridge-portability-v1"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/bridge-portability-v2"
CLOSURE = PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def run(command: list[str], receipt: dict, label: str) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    receipt["commands"].append({"label": label, "argv": command,
                                "returncode": result.returncode,
                                "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError(f"{label} failed")


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists() or not (V1_WORK / "receipt.json").is_file():
        raise RuntimeError("new v2 work directory and preserved v1 receipt are required")

    prior = json.loads((V1_WORK / "receipt.json").read_text(encoding="utf-8"))
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    WORK.mkdir(parents=True)
    receipt = {
        "schema": "cix-linux-bridge-portability-v2",
        "status": "running",
        "scope": "spatial-only continuation; v1 PAQ/JXL outputs are indexed, not rebuilt",
        "v1_receipt_sha256": digest(V1_WORK / "receipt.json"),
        "completed_v1": {key: prior.get(key, {}) for key in ("commands", "artifacts", "compile_commands")},
        "commands": [],
    }
    try:
        source = PROJECT / "rust/cix-native/codecs/spatial"
        codec_prefix = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix"
        build, prefix = WORK / "build", WORK / "prefix"
        run(["/usr/bin/cmake", "-S", str(source), "-B", str(build),
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
             f"-DCIX_SPATIAL_ROOT={codec_prefix}", f"-DCMAKE_INSTALL_PREFIX={prefix}"],
            receipt, "spatial-configure")
        run(["/usr/bin/cmake", "--build", str(build), "--parallel", "4"], receipt, "spatial-build")
        run(["/usr/bin/cmake", "--install", str(build)], receipt, "spatial-install")
        commands = build / "compile_commands.json"
        library = next((prefix / "lib").glob("*.so"))
        if not commands.is_file():
            raise RuntimeError("spatial configure did not emit compile_commands.json")
        copied_commands = WORK / "compile_commands.json"
        shutil.copy2(commands, copied_commands)
        receipt["spatial"] = {
            "source_cmakelists_sha256": digest(source / "CMakeLists.txt"),
            "source_cpp_sha256": digest(source / "cix_spatial_bridge.cpp"),
            "compile_commands_sha256": digest(copied_commands),
            "artifact_sha256": digest(library),
            "selected_closure_sha256": closure["providers"]["CIX_RUNTIME_SPATIAL_BRIDGE"]["sha256"],
        }
        receipt["status"] = "pass_current_spatial_build"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
