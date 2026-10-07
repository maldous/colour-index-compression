#!/usr/bin/env python3
"""Rebuild selected Linux bridge CMake sources and retain compile metadata."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
WORK = PROJECT / "benchmark-work/native-rc-check-v1/bridge-portability-v1"
PROVENANCE = PROJECT / "rust/cix-native/packaging/notices/provider-provenance-v3.json"
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


def configure_build(name: str, source: Path, arguments: list[str], receipt: dict) -> Path:
    build = WORK / "build" / name
    prefix = WORK / "prefix" / name
    command = ["/usr/bin/cmake", "-S", str(source), "-B", str(build),
               "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
               f"-DCMAKE_INSTALL_PREFIX={prefix}", *arguments]
    run(command, receipt, f"{name}-configure")
    run(["/usr/bin/cmake", "--build", str(build), "--parallel", "4"], receipt, f"{name}-build")
    run(["/usr/bin/cmake", "--install", str(build)], receipt, f"{name}-install")
    commands = build / "compile_commands.json"
    if not commands.is_file():
        raise RuntimeError(f"{name} did not emit compile_commands.json")
    copied = WORK / "compile_commands" / f"{name}.json"
    copied.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(commands, copied)
    receipt["compile_commands"][name] = {"path": str(copied), "sha256": digest(copied)}
    return prefix


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse work root: {WORK}")
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    if provenance.get("schema") != "cix-selected-runtime-provider-provenance-v3":
        raise RuntimeError("unexpected provider provenance schema")
    if set(provenance["providers"]) != set(closure["providers"]):
        raise RuntimeError("provenance and selected closure provider sets differ")
    WORK.mkdir(parents=True)
    receipt = {"schema": "cix-linux-bridge-portability-v1", "status": "running",
               "scope": "current first-party CMake compile/link regression only; not cross-platform qualification",
               "commands": [], "compile_commands": {}, "artifacts": {},
               "source_hashes": {}, "provenance_receipts": {}}
    for name, evidence in provenance.get("evidence_receipts", {}).items():
        evidence_path = PROJECT / evidence["path"]
        actual = digest(evidence_path)
        if actual != evidence["sha256"]:
            raise RuntimeError(f"provenance evidence hash mismatch: {name}")
        receipt["provenance_receipts"][name] = actual
    for key, provider in provenance["providers"].items():
        source = provider.get("source")
        if not isinstance(source, dict) or "receipt" not in source:
            continue
        source_receipt = PROJECT / source["receipt"]
        actual = digest(source_receipt)
        if actual != source["receipt_sha256"]:
            raise RuntimeError(f"PAQ source receipt hash mismatch: {key}")
        receipt["provenance_receipts"][key] = actual
    sources = {
        "paq-v215": PROJECT / "rust/cix-native/codecs/paq/v215",
        "paq-v216": PROJECT / "rust/cix-native/codecs/paq/v216",
        "paq-joint-discount": PROJECT / "rust/cix-native/codecs/paq/joint_discount",
        "paq-store-state": PROJECT / "rust/cix-native/codecs/paq/store_state",
        "jxl": PROJECT / "rust/cix-native/codecs/jxl",
        "spatial": PROJECT / "rust/cix-native/codecs/spatial",
    }
    for name, source in sources.items():
        for path in source.glob("*.cpp"):
            receipt["source_hashes"][str(path.relative_to(PROJECT))] = digest(path)
        receipt["source_hashes"][str((source / "CMakeLists.txt").relative_to(PROJECT))] = digest(source / "CMakeLists.txt")
    try:
        paq_keys = {"paq-v215": "CIX_RUNTIME_PAQ_V215_BRIDGE", "paq-v216": "CIX_RUNTIME_PAQ_V216_BRIDGE",
                    "paq-joint-discount": "CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE", "paq-store-state": "CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE"}
        for name, key in paq_keys.items():
            root = PROJECT / provenance["providers"][key]["source"]["local_root"]
            configure_build(name, sources[name], [f"-DCIX_PAQ_SOURCE_ROOT={root}"], receipt)
        jxl_prefix = PROJECT / "benchmark-work/native-rc-check-v1/jxl-prefix-v3"
        spatial_prefix = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix"
        configure_build("jxl", sources["jxl"], [f"-DCIX_JXL_ROOT={jxl_prefix}"], receipt)
        configure_build("spatial", sources["spatial"], [f"-DCIX_SPATIAL_ROOT={spatial_prefix}"], receipt)
        for name, key in (("paq-v215", "CIX_RUNTIME_PAQ_V215_BRIDGE"), ("paq-v216", "CIX_RUNTIME_PAQ_V216_BRIDGE"),
                          ("paq-joint-discount", "CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE"), ("paq-store-state", "CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE"),
                          ("jxl", "CIX_RUNTIME_JXL_BRIDGE"), ("spatial", "CIX_RUNTIME_SPATIAL_BRIDGE")):
            library = next((WORK / "prefix" / name / "lib").glob("*.so"))
            receipt["artifacts"][key] = {"path": str(library), "sha256": digest(library),
                                           "selected_closure_sha256": closure["providers"][key]["sha256"]}
        receipt["status"] = "pass_current_source_build"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
