#!/usr/bin/env python3
"""Root-scheduled native Rust regression qualification.

This is deliberately a test runner, not a benchmark.  It accepts only a
root-frozen source snapshot and creates a fresh child work directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time

REQUIRED_PAQ = (
    "libcix_paq_v215_bridge.so",
    "libcix_paq_v216_bridge.so",
    "libcix_paq_joint_discount_bridge.so",
    "libcix_paq_store_state_bridge.so",
)
INTEGRATION_TARGETS = (
    # Public C ABI and dictionary contracts.
    "c_api_contract", "c_format_contract", "c_stream_contract", "dictionary_contract",
    "native_context",
    # Ordinary and full-engine command-line paths, including the RC23 worker.
    "cli_smoke", "cli_full_engine", "cli_multiple_files", "full_engine_jobs_cli",
    # Resource admission and bounded input/output paths.
    "resource_admission", "codec_limits", "decoder_memory", "bounded_reader",
    # Incremental, pipe and CIXW1 streaming transports.
    "incremental_contract", "streaming_pipe", "window_stream", "window_transport", "window_cli",
)
PAQ_PRIVATE_ROOT_CAP = 64_000_000
PAQ_SAMPLE_SECONDS = 0.2


def fail(message):
    raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path):
    path = path.resolve()
    if not path.is_file():
        fail(f"required regular file is absent: {path}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def source_file_hashes(root):
    """Return a complete, stable source snapshot identity without following links."""
    result = {}
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or not path.is_file() or path.is_symlink():
            continue
        result[str(path.relative_to(root))] = sha256(path)
    return result


def directory_bytes(root):
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            # PAQ workers remove their own private children while this monitor
            # walks the directory.
            continue
    return total


def private_directory(path):
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        fail(f"private PAQ root is not mode 0700: {path}")


def run_phase(label, argv, env, work, receipt, private_paq_root):
    stdout = work / f"{label}.stdout.log"
    stderr = work / f"{label}.stderr.log"
    started = time.time()
    peak_private_paq_bytes = directory_bytes(private_paq_root)
    cap_exceeded = False
    with stdout.open("xb") as out, stderr.open("xb") as err:
        completed = subprocess.Popen(
            argv, env=env, stdout=out, stderr=err, start_new_session=True,
        )
        while completed.poll() is None:
            peak_private_paq_bytes = max(peak_private_paq_bytes, directory_bytes(private_paq_root))
            if peak_private_paq_bytes > PAQ_PRIVATE_ROOT_CAP:
                cap_exceeded = True
                try:
                    os.killpg(completed.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    completed.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(completed.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                break
            time.sleep(PAQ_SAMPLE_SECONDS)
        returncode = completed.wait()
    peak_private_paq_bytes = max(peak_private_paq_bytes, directory_bytes(private_paq_root))
    cap_exceeded |= peak_private_paq_bytes > PAQ_PRIVATE_ROOT_CAP
    result = {
        "argv": argv,
        "returncode": returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout": str(stdout),
        "stderr": str(stderr),
        "private_paq_root_cap_bytes": PAQ_PRIVATE_ROOT_CAP,
        "private_paq_root_sample_interval_seconds": PAQ_SAMPLE_SECONDS,
        "private_paq_root_sampled_peak_bytes": peak_private_paq_bytes,
        "private_paq_root_cap_exceeded": cap_exceeded,
    }
    receipt["phases"][label] = result
    (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if cap_exceeded:
        fail(f"{label} exceeded the PAQ private-root cap; Cargo process group terminated")
    if returncode:
        fail(f"{label} failed; inspect {stderr}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--freeze-record", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--native-library-dir", type=Path, required=True)
    parser.add_argument("--paq-libdir", type=Path, required=True)
    parser.add_argument("--paq-work-root", type=Path, required=True)
    parser.add_argument("--jxl-bridge", type=Path, required=True)
    parser.add_argument("--spatial-bridge", type=Path, required=True)
    args = parser.parse_args()

    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        fail("CIX_RELEASE_LEASE=1 is required for root-scheduled regression dispatch")
    source = args.source.resolve()
    manifest = source / "Cargo.toml"
    lockfile = source / "Cargo.lock"
    if not manifest.is_file() or not lockfile.is_file():
        fail("--source must be the root-confirmed frozen cix-native snapshot with Cargo.toml and Cargo.lock")
    freeze_record = args.freeze_record.resolve()
    try:
        freeze = json.loads(freeze_record.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read root freeze record: {error}")
    if not isinstance(freeze, dict) or freeze.get("approved_by_root") is not True:
        fail("freeze record must state approved_by_root: true")
    if freeze.get("manifest_sha256") != sha256(manifest) or freeze.get("lockfile_sha256") != sha256(lockfile):
        fail("freeze record does not identify this source manifest and lockfile")
    actual_source_files = source_file_hashes(source)
    if freeze.get("source_files_sha256") != actual_source_files:
        fail("freeze record does not identify every regular source file")
    if args.work.exists():
        fail(f"--work must be absent so this job owns its artifacts: {args.work}")
    args.work.mkdir(parents=True)
    private_paq_root = args.paq_work_root.resolve()
    if private_paq_root.exists():
        fail(f"--paq-work-root must be absent so this job owns the PAQ private root: {private_paq_root}")
    private_directory(private_paq_root)
    temporary = args.work / "tmp"
    private_directory(temporary)

    native_library_dir = args.native_library_dir.resolve()
    paq_libdir = args.paq_libdir.resolve()
    if not native_library_dir.is_dir() or not paq_libdir.is_dir():
        fail("the native library directory and PAQ library directory must exist")
    provider_identities = {
        "jxl": identity(args.jxl_bridge),
        "spatial": identity(args.spatial_bridge),
        "paq": {name: identity(paq_libdir / name) for name in REQUIRED_PAQ},
    }

    cargo = shutil.which("cargo")
    if not cargo:
        fail("cargo is not on PATH")
    target = args.target.resolve()
    environment = os.environ.copy()
    environment.update({
        "CARGO_TARGET_DIR": str(target),
        "CARGO_BUILD_JOBS": "4",
        "CARGO_INCREMENTAL": "0",
        "CARGO_PROFILE_DEV_DEBUG": "0",
        "CARGO_PROFILE_TEST_DEBUG": "0",
        "TMPDIR": str(temporary),
        "CIX_NATIVE_LIBRARY_DIR": str(native_library_dir),
        "LIBRARY_PATH": str(native_library_dir),
        "CIX_TEST_PAQ_LIBDIR": str(paq_libdir),
        "CIX_TEST_PAQ_WORKROOT": str(private_paq_root),
        "CIX_TEST_JXL_BRIDGE": str(args.jxl_bridge.resolve()),
        "CIX_TEST_SPATIAL_BRIDGE": str(args.spatial_bridge.resolve()),
    })
    receipt = {
        "job": "native-regression-v2",
        "source": {
            "manifest": identity(manifest), "lockfile": identity(lockfile),
            "root_freeze_record": identity(freeze_record), "root_freeze": freeze,
            "source_files_sha256": actual_source_files,
        },
        "providers": provider_identities,
        "constraints": {
            "cargo_build_jobs": 4,
            "test_threads": 1,
            "debug_info": False,
            "declared_memory_bytes": 12000000000,
            "scheduler_temporary_bytes": 3936000000,
            "private_paq_root_reservation_bytes": PAQ_PRIVATE_ROOT_CAP,
            "aggregate_temporary_bytes": 4000000000,
            "provider_checks_are_required": True,
        },
        "phases": {},
    }
    (args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def cargo_command(action):
        return [cargo, action, "--locked", "--offline", "--manifest-path", str(manifest)]

    run_phase("build-bins", cargo_command("build") + ["--bins"], environment, args.work, receipt, private_paq_root)
    cix = target / "debug" / "cix"
    receipt["cix_executable"] = identity(cix)
    environment["CIX_TEST_EXECUTABLE"] = str(cix.resolve())
    (args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    run_phase("library", cargo_command("test") + ["--lib", "--", "--test-threads=1"], environment, args.work, receipt, private_paq_root)
    integration = cargo_command("test")
    for target_name in INTEGRATION_TARGETS:
        integration.extend(["--test", target_name])
    integration.extend(["--", "--test-threads=1"])
    run_phase("focused-integration", integration, environment, args.work, receipt, private_paq_root)

    used = sum(path.stat().st_size for path in args.work.rglob("*") if path.is_file())
    receipt["owned_work_file_bytes"] = used
    receipt["status"] = "passed"
    (args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"native-regression-v2: {error}", file=sys.stderr)
        raise SystemExit(1)
