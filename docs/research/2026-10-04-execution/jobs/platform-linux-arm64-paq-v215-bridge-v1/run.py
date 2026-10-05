#!/usr/bin/env python3
"""Root-scheduled ARM64 PAQ v215 bridge ABI qualification; no worker integration."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

AREA = Path(__file__).resolve().parent
PROJECT = AREA.parents[4]
WORK_PARENT = PROJECT / "benchmark-work/native-rc-check-v1"
WORK = WORK_PARENT / "platform-linux-arm64-paq-v215-bridge-v1"
TOOLCHAIN_RECEIPT = Path(os.environ.get("CIX_ARM64_TOOLCHAIN_RECEIPT", str(WORK_PARENT / "platform-linux-arm64-user-toolchain-v3/receipt.json")))
VENDOR = WORK_PARENT / "paq-v215-build-v1-vendor"
VENDOR_RECEIPT = PROJECT / "docs/research/2026-10-04-native-rc/jobs/paq-v215-build-v1/source.json"
X64_JOB = PROJECT / "docs/research/2026-10-04-native-rc/jobs/paq-v215-qualification-v2"
X64_SUMMARY = X64_JOB / "raw/qualification.json"
X64_BUILD = WORK_PARENT / "paq-v215-qualification-v2-output"
X64_LIBRARY = X64_BUILD / "libcix_paq_v215_bridge.so"
X64_PROBE = X64_BUILD / "paq_abi_probe"
LOCAL_CAP = 128_000_000
SHARED_CAP = 4_000_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def allocated(path: Path) -> int:
    return int(subprocess.run(["du", "-sx", "-B1", str(path)], text=True, check=True,
                              stdout=subprocess.PIPE).stdout.split()[0])


def check_local_cap() -> int:
    used = allocated(WORK)
    if used > LOCAL_CAP:
        raise RuntimeError(f"local qualification cap exceeded: {used} > {LOCAL_CAP}")
    return used


def run(receipt: dict[str, object], name: str, argv: list[Path | str], *, timeout: int = 180,
        env: dict[str, str] | None = None) -> str:
    """Keep exact stdout/stderr and command status even when a command fails."""
    logs = WORK / "logs"; logs.mkdir(exist_ok=True)
    command = [str(value) for value in argv]
    stdout_path = logs / f"{name}.stdout.log"; stderr_path = logs / f"{name}.stderr.log"
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, timeout=timeout, check=False, env=env)
        stdout_path.write_bytes(completed.stdout); stderr_path.write_bytes(completed.stderr)
        code: int | None = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout_path.write_bytes(error.stdout or b""); stderr_path.write_bytes(error.stderr or b"")
        code = None
        receipt.setdefault("commands", []).append({"name": name, "argv": command, "returncode": code,
            "timed_out": True, "stdout": str(stdout_path), "stderr": str(stderr_path)})
        raise RuntimeError(f"{name} timed out after {timeout}s") from error
    receipt.setdefault("commands", []).append({"name": name, "argv": command, "returncode": code,
        "timed_out": False, "stdout": str(stdout_path), "stderr": str(stderr_path)})
    if code != 0:
        raise RuntimeError(f"{name} failed with exit {code}")
    return completed.stdout.decode("utf-8", "replace")


def snapshot_files(root: Path, hashes: dict[str, str]) -> None:
    if not root.is_dir():
        raise RuntimeError(f"retained source missing: {root}")
    for relative, expected in hashes.items():
        source = root / relative
        if not source.is_file() or sha256(source) != expected:
            raise RuntimeError(f"retained source identity mismatch: {source}")


def vendor_hashes(expected: dict[str, str]) -> dict[str, str]:
    return {relative: sha256(VENDOR / relative) for relative in expected}


def x64_identities() -> dict[str, str]:
    return {"summary": sha256(X64_SUMMARY), "library": sha256(X64_LIBRARY), "probe": sha256(X64_PROBE)}


def toolchain_identities(compiler: Path, qemu: Path, host_library_path: Path) -> dict[str, object]:
    libraries = {entry.name: sha256(entry) for entry in sorted(host_library_path.iterdir())
                 if entry.is_file() and not entry.is_symlink()}
    if not libraries:
        raise RuntimeError("passed toolchain receipt host library path has no regular libraries")
    return {"receipt": sha256(TOOLCHAIN_RECEIPT), "compiler": sha256(compiler), "qemu": sha256(qemu),
            "host_library_path": str(host_library_path), "host_libraries": libraries}


def host_build_env(host_library_path: Path) -> dict[str, str]:
    return {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
            "LD_LIBRARY_PATH": str(host_library_path)}


def current_bridge_hashes() -> dict[str, str]:
    root = PROJECT / "rust/cix-native/codecs/paq/v215"
    names = ("CMakeLists.txt", "exports.map", "paq_v215_bridge.cpp", "paq_v215_bridge.h")
    return {name: sha256(root / name) for name in names}


def job_hashes() -> dict[str, str]:
    return {name: sha256(AREA / name) for name in ("run.py", "probe.cpp", "spec.json")}


def qemu_env(prefix: Path) -> dict[str, str]:
    return {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "OMP_NUM_THREADS": "1",
            "LD_LIBRARY_PATH": ""}


def invoke_qemu(receipt: dict[str, object], name: str, qemu: Path, runtime_root: Path, probe: Path, expected: Path, args: list[Path | str]) -> str:
    return run(receipt, name, [qemu, "-cpu", "cortex-a72", "-L", runtime_root, probe, expected, *args], env=qemu_env(runtime_root))


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse work: {WORK}")
    existing = allocated(WORK_PARENT) if WORK_PARENT.exists() else 0
    if existing + LOCAL_CAP > SHARED_CAP:
        raise RuntimeError(f"shared work admission fails: {existing} + {LOCAL_CAP} > {SHARED_CAP}")
    vendor_receipt = json.loads(VENDOR_RECEIPT.read_text())
    vendor_expected = vendor_receipt["vendor"]["files"]
    snapshot_files(VENDOR, vendor_expected)
    vendor_before = vendor_hashes(vendor_expected)
    x64_summary = json.loads(X64_SUMMARY.read_text())
    if x64_summary.get("status") != "component qualification passed; not full CIX worker integration":
        raise RuntimeError("retained x64 v215 qualification is not the expected component pass")
    if not X64_LIBRARY.is_file() or not X64_PROBE.is_file():
        raise RuntimeError("retained qualified x64 bridge artifacts are absent")
    if sha256(X64_LIBRARY) != x64_summary["bridge_sha256"] or sha256(X64_PROBE) != x64_summary["probe_sha256"]:
        raise RuntimeError("retained x64 bridge artifact identity mismatch")
    x64_before = x64_identities()
    if not TOOLCHAIN_RECEIPT.is_file() or not TOOLCHAIN_RECEIPT.is_relative_to(WORK_PARENT):
        raise RuntimeError("configured toolchain receipt must remain under the shared work root")
    toolchain_receipt = json.loads(TOOLCHAIN_RECEIPT.read_text())
    if toolchain_receipt.get("status") != "pass":
        raise RuntimeError("user-toolchain receipt is not a passing result")
    TOOLCHAIN = Path(toolchain_receipt.get("toolchain_prefix", ""))
    host_library_path = Path(toolchain_receipt.get("host_library_path", ""))
    if not TOOLCHAIN.is_dir() or not TOOLCHAIN.is_relative_to(WORK_PARENT) or not host_library_path.is_dir() or not host_library_path.is_relative_to(WORK_PARENT):
        raise RuntimeError("passed receipt has an invalid retained prefix or host library path")
    compiler = TOOLCHAIN / "usr/bin/aarch64-linux-gnu-g++"
    qemu = TOOLCHAIN / "usr/bin/qemu-aarch64-static"
    sysroot = TOOLCHAIN
    runtime_root = TOOLCHAIN / "usr/aarch64-linux-gnu"
    target_bin = runtime_root / "bin"
    if not compiler.is_file() or not qemu.is_file() or not runtime_root.is_dir() or not target_bin.is_dir():
        raise RuntimeError("passed user-toolchain job prefix is unavailable")
    if toolchain_receipt.get("relocated_compiler_sha256") != sha256(compiler) or toolchain_receipt.get("relocated_qemu_sha256") != sha256(qemu):
        raise RuntimeError("user-toolchain executable identity mismatch")
    toolchain_before = toolchain_identities(compiler, qemu, host_library_path)
    WORK.mkdir(parents=True)
    receipt: dict[str, object] = {
        "schema": "cix-platform-linux-arm64-paq-v215-bridge-v1", "status": "fail",
        "job_inputs_before": job_hashes(), "bridge_inputs_before": current_bridge_hashes(),
        "vendor_inputs_before": vendor_before, "x64_inputs_before": x64_before, "toolchain_inputs_before": toolchain_before,
        "vendor_receipt_sha256": sha256(VENDOR_RECEIPT), "x64_summary_sha256": sha256(X64_SUMMARY),
        "x64_bridge_sha256": sha256(X64_LIBRARY), "x64_probe_sha256": sha256(X64_PROBE),
        "toolchain_receipt_path": str(TOOLCHAIN_RECEIPT), "toolchain_prefix": str(TOOLCHAIN),
        "toolchain_host_library_path": str(host_library_path), "toolchain_receipt_sha256": sha256(TOOLCHAIN_RECEIPT),
        "toolchain_compiler_sha256": sha256(compiler), "toolchain_qemu_sha256": sha256(qemu),
        "shared_bytes_before": existing, "local_cap_bytes": LOCAL_CAP,
    }
    try:
        source = PROJECT / "rust/cix-native/codecs/paq/v215"
        bridge = WORK / "bridge-source"
        shutil.copytree(source, bridge)
        if {name: sha256(bridge / name) for name in current_bridge_hashes()} != receipt["bridge_inputs_before"]:
            raise RuntimeError("copied bridge source identity mismatch")
        check_local_cap()
        build = WORK / "arm-build"
        cmake = ["cmake", "-S", bridge, "-B", build, "-DCMAKE_BUILD_TYPE=Release",
                 "-DCMAKE_SYSTEM_NAME=Linux", "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
                 f"-DCMAKE_C_COMPILER={TOOLCHAIN / 'usr/bin/aarch64-linux-gnu-gcc'}",
                 f"-DCMAKE_CXX_COMPILER={compiler}", f"-DCMAKE_C_FLAGS_INIT=-B{target_bin}",
                 f"-DCMAKE_CXX_FLAGS_INIT=-B{target_bin}", f"-DCMAKE_SYSROOT={sysroot}",
                 f"-DCMAKE_FIND_ROOT_PATH={sysroot}", "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER",
                 "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY", "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY",
                 f"-DCIX_PAQ_SOURCE_ROOT={VENDOR}"]
        run(receipt, "cmake-configure", cmake, env=host_build_env(host_library_path))
        check_local_cap()
        run(receipt, "cmake-build", ["cmake", "--build", build, "--parallel", "2"], timeout=600, env=host_build_env(host_library_path))
        check_local_cap()
        library = build / "libcix_paq_v215_bridge.so"
        if not library.is_file():
            raise RuntimeError("ARM64 bridge library missing")
        probe = WORK / "paq_abi_probe_arm64"
        shutil.copy2(library, WORK / library.name)
        run(receipt, "probe-compile", [compiler, f"--sysroot={sysroot}", "-B", target_bin, "-std=c++17", "-O2", AREA / "probe.cpp",
                                         f"-I{bridge}", f"-L{build}", "-Wl,-rpath,$ORIGIN",
                                         "-lcix_paq_v215_bridge", "-o", probe], env=host_build_env(host_library_path))
        receipt["arm_library_file"] = run(receipt, "arm-library-file", ["file", library])
        receipt["arm_probe_file"] = run(receipt, "arm-probe-file", ["file", probe])
        if "aarch64" not in receipt["arm_library_file"].lower() or "aarch64" not in receipt["arm_probe_file"].lower():
            raise RuntimeError("cross build output is not AArch64")
        program_headers = run(receipt, "arm-probe-program-headers", ["readelf", "-l", probe])
        dynamic = run(receipt, "arm-probe-dynamic", ["readelf", "-d", probe])
        interpreter = re.search(r"Requesting program interpreter: ([^]]+)", program_headers)
        if interpreter is None:
            raise RuntimeError("ARM probe lacks a recorded ELF interpreter")
        interpreter_path = interpreter.group(1)
        if not interpreter_path.startswith("/") or not (runtime_root / interpreter_path.lstrip("/")).is_file():
            raise RuntimeError(f"qemu runtime root lacks ELF interpreter {interpreter_path}")
        receipt["qemu_runtime_root"] = str(runtime_root)
        receipt["elf_interpreter"] = interpreter_path
        receipt["elf_needed_records"] = [line.strip() for line in dynamic.splitlines() if "NEEDED" in line]
        fixtures = WORK / "fixtures"; fixtures.mkdir()
        source_data = (b"CIX ARM64 PAQ v215 ABI fixture\n" * 64) + bytes(range(256)) * 8
        source_input = fixtures / "source.bin"; source_input.write_bytes(source_data)
        arm_archive = fixtures / "arm.paq8px215"; arm_decoded = fixtures / "arm-decoded.bin"
        x64_archive = fixtures / "x64.paq8px215"; x64_decoded = fixtures / "x64-decoded.bin"
        receipt["arm_encode"] = invoke_qemu(receipt, "arm-encode", qemu, runtime_root, probe, arm_archive, ["-1", source_input, arm_archive])
        receipt["arm_decode_fresh_process"] = invoke_qemu(receipt, "arm-decode", qemu, runtime_root, probe, arm_decoded, ["-d", arm_archive, arm_decoded])
        if arm_decoded.read_bytes() != source_data:
            raise RuntimeError("ARM bridge self-decode differs from input")
        run(receipt, "x64-encode", [X64_PROBE, "once", x64_archive, "-1", source_input, x64_archive], env=qemu_env(runtime_root))
        run(receipt, "x64-decode-arm", [X64_PROBE, "once", x64_decoded, "-d", arm_archive, x64_decoded], env=qemu_env(runtime_root))
        if x64_decoded.read_bytes() != source_data:
            raise RuntimeError("qualified x64 bridge cannot decode ARM archive")
        arm_from_x64 = fixtures / "arm-from-x64.bin"
        invoke_qemu(receipt, "arm-decode-x64", qemu, runtime_root, probe, arm_from_x64, ["-d", x64_archive, arm_from_x64])
        if arm_from_x64.read_bytes() != source_data:
            raise RuntimeError("ARM bridge cannot decode qualified x64 archive")
        receipt["input_sha256"] = hashlib.sha256(source_data).hexdigest()
        receipt["arm_archive_sha256"] = sha256(arm_archive); receipt["x64_archive_sha256"] = sha256(x64_archive)
        receipt["arm_library_sha256"] = sha256(library); receipt["arm_probe_sha256"] = sha256(probe)
        receipt["job_inputs_after"] = job_hashes(); receipt["bridge_inputs_after"] = current_bridge_hashes()
        receipt["vendor_inputs_after"] = vendor_hashes(vendor_expected)
        receipt["x64_inputs_after"] = x64_identities()
        receipt["toolchain_inputs_after"] = toolchain_identities(compiler, qemu, host_library_path)
        if receipt["job_inputs_before"] != receipt["job_inputs_after"] or receipt["bridge_inputs_before"] != receipt["bridge_inputs_after"]:
            raise RuntimeError("runner or bridge inputs changed during qualification")
        if receipt["vendor_inputs_before"] != receipt["vendor_inputs_after"] or receipt["x64_inputs_before"] != receipt["x64_inputs_after"] or receipt["toolchain_inputs_before"] != receipt["toolchain_inputs_after"]:
            raise RuntimeError("retained vendor, x64 bridge, or toolchain input changed during qualification")
        receipt["allocated_work_bytes"] = check_local_cap()
        receipt["status"] = "pass"
    except Exception as error:
        receipt["error"] = str(error)
        raise
    finally:
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
