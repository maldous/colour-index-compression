#!/usr/bin/env python3
"""Lease-gated focused PAQ shared-loader qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[5]
WORK = PROJECT / "benchmark-work/native-rc-check-v1/paq-loader-slice1-v1"
SOURCE, NATIVE = WORK / "source", WORK / "source/rust/cix-native"
TARGET, TMP, PAQ_ROOT = WORK / "target", WORK / "tmp", WORK / "paq-private"
SCOPE = PROJECT / "benchmark-work/native-rc-check-v1/paq-loader-slice1-v1.quality-scope.json"
SDK = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix/usr/lib/x86_64-linux-gnu"
PAQ = PROJECT / "benchmark-work/native-rc-check-v1/paq-cix-worker-v2-output/lib"
JXL = PROJECT / "benchmark-work/native-rc-check-v1/jxl-prefix-v3/lib/libcix_jxl_bridge.so"
PAQ_BRIDGES = ("libcix_paq_v215_bridge.so", "libcix_paq_v216_bridge.so",
               "libcix_paq_joint_discount_bridge.so", "libcix_paq_store_state_bridge.so")
CAP, SAMPLE = 600_000_000, 0.2


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(path: Path, *, allow_symlink: bool = False) -> dict[str, object]:
    if not path.is_file() or (path.is_symlink() and not allow_symlink):
        fail(f"required regular file is absent: {path}")
    return {"path": str(path), "resolved_path": str(path.resolve()),
            "symlink_target": os.readlink(path) if path.is_symlink() else None,
            "bytes": path.stat().st_size, "sha256": sha256(path)}


def hashes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()}


def bytes_in(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def allocated(path: Path) -> int:
    result = subprocess.run(["/usr/bin/du", "-s", "--block-size=1", str(path)], text=True,
                            capture_output=True, check=False)
    if result.returncode:
        fail(f"cannot measure allocation: {result.stderr.strip()}")
    return int(result.stdout.split(maxsplit=1)[0])


def write_receipt(receipt: dict) -> None:
    path = WORK / "receipt.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def snapshot() -> dict[str, object]:
    export = SOURCE / "EXPORT-MANIFEST.json"
    if not all(path.is_file() for path in (SOURCE / "Cargo.toml", SOURCE / "Cargo.lock", export,
                                           NATIVE / "Cargo.toml")):
        fail("root must stage a complete portable workspace under owned work/source")
    try:
        manifest = json.loads(export.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read export manifest: {error}")
    if manifest.get("schema") != "cix-native-materialised-source-export-v1" or not isinstance(manifest.get("members_sha256"), dict):
        fail("source export manifest is not an allowlisted materialised-source proof")
    return {"workspace_files_sha256": hashes(SOURCE), "native_files_sha256": hashes(NATIVE),
            "export_manifest": identity(export), "export_members_sha256": dict(sorted(manifest["members_sha256"].items()))}


def providers(cix: Path | None = None) -> dict[str, object]:
    if not SDK.is_dir() or not PAQ.is_dir():
        fail("retained SDK or PAQ provider directory is absent")
    result: dict[str, object] = {
        "sdk_linker_inputs": {name: identity(SDK / name, allow_symlink=True) for name in
                              ("libcharls.so", "libopenjp2.so", "liblz4.so", "libsnappy.so")},
        "paq": {name: identity(PAQ / name) for name in PAQ_BRIDGES}, "jxl": identity(JXL)}
    if cix is not None:
        result["cix"] = identity(cix)
    return result


def private(path: Path) -> None:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        fail(f"private path is not 0700: {path}")


def scope() -> dict[str, object]:
    try:
        value = json.loads(SCOPE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"fresh root quality-scope is required: {error}")
    if (value.get("schema") != "cix-native-quality-scope-v1" or value.get("approved_by_root") is not True or
            value.get("cache_archive_verified") is not True or value.get("cache_prune_complete") is not True or
            value.get("shared_work_ceiling_bytes") != 4_000_000_000 or value.get("admitted_new_work_bytes", 0) < CAP):
        fail("quality-scope does not approve the 600 MB capped job")
    base = allocated(WORK.parent) - allocated(WORK)
    if base + CAP > 4_000_000_000:
        fail("shared work plus capped job exceeds 4 GB")
    value["fresh_existing_work_without_job_bytes"] = base
    return value


def phase(label: str, argv: list[str], environment: dict[str, str], receipt: dict,
          frozen: dict[str, object], tests: bool = False) -> None:
    stdout, stderr = WORK / f"{label}.stdout.log", WORK / f"{label}.stderr.log"
    started, peak, reason = time.time(), bytes_in(WORK), None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(argv, cwd=SOURCE, env=environment, stdout=out, stderr=err,
                                 start_new_session=True)
        while child.poll() is None:
            peak = max(peak, bytes_in(WORK))
            if peak > CAP:
                reason = f"all new work exceeded {CAP} bytes"
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                break
            time.sleep(SAMPLE)
        code = child.wait()
    peak = max(peak, bytes_in(WORK))
    cix = TARGET / "debug/cix"
    result: dict[str, object] = {
        "argv": argv, "returncode": code, "stdout": str(stdout), "stderr": str(stderr),
        "elapsed_seconds": round(time.time() - started, 3), "sample_interval_seconds": SAMPLE,
        "sampled_peak_all_new_work_bytes": peak, "cap_reason": reason,
        "source_unchanged": snapshot() == frozen,
        "providers_after": providers(cix if cix.is_file() else None)}
    if tests:
        output = stdout.read_text(errors="replace") + stderr.read_text(errors="replace")
        counts = [int(value) for value in re.findall(r"(\d+) passed;", output)]
        result["reported_passed_counts"], result["nonzero_passed_count"] = counts, any(counts)
    receipt["phases"][label] = result
    write_receipt(receipt)
    if reason or peak > CAP:
        fail(f"{label}: all-new-work cap exceeded; process group terminated")
    if code:
        fail(f"{label} failed; inspect {stderr}")
    if not result["source_unchanged"]:
        fail(f"{label} changed the frozen workspace snapshot")
    expected_providers = dict(receipt["providers_before"])
    actual_providers = dict(result["providers_after"])
    if "cix" not in expected_providers:
        actual_providers.pop("cix", None)
    if expected_providers != actual_providers:
        fail(f"{label} changed a retained provider")
    if tests and not result["nonzero_passed_count"]:
        fail(f"{label} did not report a nonzero passed-test count")


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        fail("CIX_RELEASE_LEASE=1 is required")
    if not WORK.is_dir() or set(path.name for path in WORK.iterdir()) != {"source"}:
        fail("root must create fresh work containing only its immutable source snapshot")
    if TARGET.exists() or TMP.exists() or PAQ_ROOT.exists():
        fail("owned target, temporary, and private PAQ paths must be absent")
    approved, frozen = scope(), snapshot()
    if bytes_in(WORK) > CAP:
        fail("prepared source snapshot already exceeds the all-new-work cap")
    if (approved.get("workspace_files_sha256") != frozen["workspace_files_sha256"] or
            approved.get("native_files_sha256") != frozen["native_files_sha256"]):
        fail("quality-scope does not bind this complete workspace/native snapshot")
    cargo = shutil.which("cargo")
    if cargo is None:
        fail("cargo is not on PATH")
    private(TMP); private(PAQ_ROOT)
    receipt: dict[str, object] = {"schema": "cix-paq-loader-slice1-v1", "status": "running",
        "quality_scope": identity(SCOPE), "quality_scope_record": approved, "source_before": frozen,
        "providers_before": providers(), "limits": {"all_new_work_cap_bytes": CAP, "cargo_build_jobs": 4,
        "test_threads": 1, "private_paq_root": str(PAQ_ROOT)}, "phases": {}}
    environment = os.environ.copy()
    environment.update({"CARGO_TARGET_DIR": str(TARGET), "CARGO_BUILD_JOBS": "4", "CARGO_INCREMENTAL": "0",
        "CARGO_NET_OFFLINE": "true", "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
        "TMPDIR": str(TMP), "CIX_NATIVE_LIBRARY_DIR": str(SDK), "LIBRARY_PATH": str(SDK),
        "CIX_TEST_PAQ_LIBDIR": str(PAQ), "CIX_TEST_PAQ_WORKROOT": str(PAQ_ROOT), "CIX_TEST_JXL_BRIDGE": str(JXL)})
    common = ["--manifest-path", str(SOURCE / "Cargo.toml"), "--locked", "--offline", "-p", "cix-native"]
    try:
        phase("format", [cargo, "fmt", "--manifest-path", str(SOURCE / "Cargo.toml"), "--all", "--check"], environment, receipt, frozen)
        phase("clippy", [cargo, "clippy", *common, "--all-targets", "--", "-D", "warnings"], environment, receipt, frozen)
        phase("paq-worker", [cargo, "test", *common, "--lib", "paq_worker::tests", "--", "--test-threads=1", "--nocapture"], environment, receipt, frozen, True)
        phase("build-cix", [cargo, "build", *common, "--bin", "cix"], environment, receipt, frozen)
        cix = TARGET / "debug/cix"
        receipt["providers_before"] = providers(cix)
        environment["CIX_TEST_EXECUTABLE"] = str(cix)
        phase("installed-provider-dispatch", [cargo, "test", *common, "--lib", "full_engine::dispatch::tests::installed_paq_and_jxl_complete_archive_dispatch", "--", "--test-threads=1", "--nocapture"], environment, receipt, frozen, True)
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"], receipt["error"] = "fail", str(error)
        raise
    finally:
        receipt["source_after"] = snapshot() if SOURCE.is_dir() else {}
        cix = TARGET / "debug/cix"
        receipt["providers_after"] = providers(cix if cix.is_file() else None)
        receipt["work_bytes_final"] = bytes_in(WORK) if WORK.exists() else 0
        write_receipt(receipt)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"paq-loader-slice1-v1: {error}", file=sys.stderr)
        raise SystemExit(1)
