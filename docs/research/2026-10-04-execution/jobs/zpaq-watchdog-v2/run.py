#!/usr/bin/env python3
"""Lease-gated focused contract for the private libzpaq watchdog wrapper."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/zpaq-watchdog-v2"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/zpaq-watchdog-v2"
SOURCE = WORK / "source"
CURRENT = PROJECT / "rust/cix-native"
OWNED = ("src/zpaq_ffi.cpp", "tests/native/zpaq_watchdog_contract.cpp")
VENDOR = ("vendor/libzpaq715/libzpaq.cpp", "vendor/libzpaq715/libzpaq.h")
WORK_LIMIT = 4_000_000_000


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_inputs(paths: tuple[str, ...]) -> None:
    for relative in paths:
        original, frozen = CURRENT / relative, SOURCE / relative
        if not original.is_file():
            raise RuntimeError(f"missing source: {relative}")
        frozen.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, frozen)


def verify(hashes: dict[str, str], root: Path) -> None:
    for relative, expected in hashes.items():
        if not (root / relative).is_file() or digest(root / relative) != expected:
            raise RuntimeError(f"source identity changed: {relative}")


def work_size() -> int:
    return sum(path.stat().st_size for path in WORK.rglob("*") if path.is_file() and not path.is_symlink())


def run(argv: list[str], receipt: dict, label: str, expected_returncode: int = 0) -> dict:
    result = subprocess.run(argv, cwd=WORK, text=True, capture_output=True, check=False, timeout=120)
    used = work_size()
    receipt["commands"].append({"label": label, "argv": argv, "cwd": str(WORK),
                                "returncode": result.returncode, "stdout": result.stdout,
                                "stderr": result.stderr, "work_bytes_after": used})
    if used > WORK_LIMIT:
        raise RuntimeError("work cap exceeded")
    if result.returncode != expected_returncode:
        raise RuntimeError(f"{label} failed")
    return receipt["commands"][-1]


def write_job_record(name: str, value: object) -> None:
    (JOB / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists():
        raise RuntimeError("refusing to reuse work root")
    initial_owned = {relative: digest(CURRENT / relative) for relative in OWNED}
    vendor_hashes = {relative: digest(CURRENT / relative) for relative in VENDOR}
    write_job_record("source-hashes.json", {"owned": initial_owned, "vendor": vendor_hashes})
    WORK.mkdir(parents=True)
    copy_inputs(OWNED + VENDOR)
    verify(initial_owned, SOURCE)
    verify(vendor_hashes, SOURCE)
    for relative in OWNED:
        target = JOB / "frozen-inputs" / (relative + ".txt")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / relative, target)
    receipt = {"schema": "cix-zpaq-watchdog-v2", "status": "running",
               "owned_source_sha256": initial_owned, "vendor_sha256": vendor_hashes,
               "commands": []}
    try:
        flags = ["-std=c++17", "-O3", "-DNOJIT", "-Dunix", "-fno-strict-aliasing"]
        vendor_object = WORK / "libzpaq.o"
        run(["/usr/bin/c++", *flags, "-I", str(SOURCE / "vendor/libzpaq715"), "-c",
             str(SOURCE / "vendor/libzpaq715/libzpaq.cpp"), "-o", str(vendor_object)], receipt,
            "compile-pinned-vendor")
        baseline_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip()
        baseline_bytes = subprocess.check_output(["git", "show", baseline_revision + ":rust/cix-native/src/zpaq_ffi.cpp"], cwd=PROJECT)
        current_bytes = (SOURCE / "src/zpaq_ffi.cpp").read_bytes()
        expected = baseline_bytes.replace(b"if (g_instruction_budget-- == 0) return false;", b"if (g_instruction_budget == 0) return false;\n  --g_instruction_budget;")
        if current_bytes != expected or baseline_bytes == expected:
            raise RuntimeError("baseline differs beyond the reviewed watchdog fix")
        baseline = WORK / "baseline"
        (baseline / "src").mkdir(parents=True)
        (baseline / "tests/native").mkdir(parents=True)
        (baseline / "src/zpaq_ffi.cpp").write_bytes(baseline_bytes)
        shutil.copy2(SOURCE / "tests/native/zpaq_watchdog_contract.cpp", baseline / "tests/native/zpaq_watchdog_contract.cpp")
        baseline_executable = WORK / "baseline_contract"
        run(["/usr/bin/c++", *flags, "-DNDEBUG", "-Wall", "-Wextra", "-Werror", "-isystem", str(SOURCE / "vendor/libzpaq715"),
             str(baseline / "tests/native/zpaq_watchdog_contract.cpp"), str(vendor_object), "-o", str(baseline_executable)], receipt, "compile-baseline-control")
        control = run([str(baseline_executable)], receipt, "expected-baseline-exhaustion-failure", expected_returncode=1)
        if "exhausted watchdog wrapped" not in control["stderr"]:
            raise RuntimeError("baseline failed outside the specific watchdog assertion")
        receipt["baseline_control"] = {"revision": baseline_revision, "wrapper_sha256": hashlib.sha256(baseline_bytes).hexdigest(), "status": "expected exhaustion assertion failed"}
        executable = WORK / "zpaq_watchdog_contract"
        run(["/usr/bin/c++", *flags, "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
             "-isystem", str(SOURCE / "vendor/libzpaq715"),
             str(SOURCE / "tests/native/zpaq_watchdog_contract.cpp"), str(vendor_object),
             "-o", str(executable)], receipt, "compile-owned-contract")
        run([str(executable)], receipt, "execute-contract")
        verify(initial_owned, CURRENT)
        verify(vendor_hashes, CURRENT)
        verify(initial_owned, SOURCE)
        verify(vendor_hashes, SOURCE)
        receipt["executable_sha256"] = digest(executable)
        receipt["source_unchanged"] = True
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        write_job_record("receipt.json", receipt)
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
