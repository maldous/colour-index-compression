#!/usr/bin/env python3
"""Lease-gated, bounded current-source quality and focused native qualification."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[5]
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/native-final-source-v1"
NATIVE = PROJECT / "rust/cix-native"
ALLOWLIST = NATIVE / "packaging/export/source-allowlist.json"
EXPORTER = NATIVE / "packaging/export/export_source.py"
CLOSURE = PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"
RETAINED_WORKSPACE_LOCK = PROJECT / "benchmark-work/native-rc-check-v1/distribution-engineering-v4/source-output/cix-0.1.0/Cargo.lock"
PORTABLE = PROJECT / "rust/cix-portable"
RETAINED_TARGET = PROJECT / "benchmark-work/native-rc-check-v1/distribution-engineering-v4/target"
CODEC_SDK_LIBDIR = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix/usr/lib/x86_64-linux-gnu"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/native-final-source-v1"
QUALITY_SCOPE = PROJECT / "benchmark-work/native-rc-check-v1/native-final-source-v1.quality-scope.json"
WORK_CAP = 720_000_000
SAMPLE_SECONDS = 0.2


def fail(message: str) -> None:
    raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(path: Path) -> dict[str, object]:
    if not path.is_file():
        fail(f"required regular file is missing: {path}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def tree_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def file_hashes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): sha256(path) for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()}


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def allocated_bytes(path: Path) -> int:
    result = subprocess.run(["/usr/bin/du", "-s", "--block-size=1", str(path)], text=True,
                            capture_output=True, check=False)
    if result.returncode:
        fail(f"cannot measure shared work allocation: {result.stderr.strip()}")
    return int(result.stdout.split(maxsplit=1)[0])


def sdk_linker_inputs() -> dict[str, dict[str, object]]:
    names = ("libcharls.so", "libopenjp2.so", "liblz4.so", "libsnappy.so")
    return {name: identity(CODEC_SDK_LIBDIR / name) for name in names}


def normalized_export_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "cix-native-materialised-source-export-v1":
        fail("unexpected source-export manifest schema")
    members = value.get("members_sha256")
    if not isinstance(members, dict) or not all(isinstance(key, str) and isinstance(item, str) for key, item in members.items()):
        fail("source-export manifest has no usable member hash mapping")
    return {"schema": value["schema"], "profile": value.get("profile"),
            "dependency_closure_status": value.get("dependency_closure_status"),
            "members_sha256": dict(sorted(members.items()))}


def lock_packages(path: Path) -> list[dict[str, object]]:
    value = tomllib.loads(path.read_text(encoding="utf-8"))
    packages = value.get("package")
    if not isinstance(packages, list) or not all(isinstance(package, dict) for package in packages):
        fail(f"Cargo lock package array is invalid: {path}")
    return sorted(packages, key=lambda package: (str(package.get("name")), str(package.get("version")), str(package.get("source", ""))))


def compatible_workspace_lock() -> dict[str, object]:
    native_packages = lock_packages(NATIVE / "Cargo.lock")
    workspace_packages = lock_packages(RETAINED_WORKSPACE_LOCK)
    workspace_without_portable = [package for package in workspace_packages if package.get("name") != "cix-portable"]
    if native_packages != workspace_without_portable:
        fail("retained workspace lock package array differs from current native lock beyond local cix-portable")
    if sum(package.get("name") == "cix-portable" for package in workspace_packages) != 1:
        fail("retained workspace lock does not contain exactly one local cix-portable package")
    local_inputs = {str(path.relative_to(PROJECT)): identity(path) for path in
                    (NATIVE / "Cargo.toml", NATIVE / "Cargo.lock", PORTABLE / "Cargo.toml",
                     NATIVE / "packaging/export/ROOT-Cargo.toml.in", RETAINED_WORKSPACE_LOCK)}
    return {"retained_workspace_lock": identity(RETAINED_WORKSPACE_LOCK), "current_local_workspace_inputs": local_inputs,
            "native_package_count": len(native_packages), "workspace_package_count": len(workspace_packages)}


def required_quality_scope() -> dict[str, object]:
    try:
        value = json.loads(QUALITY_SCOPE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"root quality_scope record is required before dispatch: {error}")
    if not isinstance(value, dict) or value.get("schema") != "cix-native-quality-scope-v1":
        fail("quality_scope record has an unexpected schema")
    if value.get("approved_by_root") is not True:
        fail("quality_scope record must state approved_by_root: true")
    if value.get("cache_archive_verified") is not True or value.get("cache_prune_complete") is not True:
        fail("quality_scope must record verified cache archive and completed prune")
    if value.get("shared_work_ceiling_bytes") != 4_000_000_000:
        fail("quality_scope must retain the shared 4 GB ceiling")
    if not isinstance(value.get("admitted_new_work_bytes"), int) or value["admitted_new_work_bytes"] < WORK_CAP:
        fail("quality_scope must admit at least this job’s 720 MB new-work cap")
    actual_existing = allocated_bytes(WORK.parent)
    recorded_existing = value.get("existing_work_bytes")
    if not isinstance(recorded_existing, int):
        fail("quality_scope must record its existing-work measurement")
    if actual_existing + WORK_CAP > 4_000_000_000:
        fail("fresh shared-work measurement plus new-work cap exceeds 4 GB")
    value["recorded_existing_work_bytes"] = recorded_existing
    value["fresh_existing_work_bytes"] = actual_existing
    return value


def run_phase(label: str, argv: list[str], env: dict[str, str], receipt: dict) -> None:
    stdout, stderr = WORK / f"{label}.stdout.log", WORK / f"{label}.stderr.log"
    started, peak_work = time.time(), tree_bytes(WORK)
    cap_reason: str | None = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(argv, cwd=WORK, env=env, stdout=out, stderr=err,
                                 start_new_session=True)
        while child.poll() is None:
            current_work = tree_bytes(WORK)
            peak_work = max(peak_work, current_work)
            if current_work > WORK_CAP:
                cap_reason = f"all new job work exceeded {WORK_CAP} bytes"
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
            time.sleep(SAMPLE_SECONDS)
        returncode = child.wait()
    current_work = tree_bytes(WORK)
    peak_work = max(peak_work, current_work)
    if current_work > WORK_CAP and cap_reason is None:
        cap_reason = f"all new job work exceeded {WORK_CAP} bytes"
    receipt["phases"][label] = {
        "argv": argv, "returncode": returncode, "elapsed_seconds": round(time.time() - started, 3),
        "stdout": str(stdout), "stderr": str(stderr), "sample_interval_seconds": SAMPLE_SECONDS,
        "sampled_peak_all_new_work_bytes": peak_work, "cap_reason": cap_reason,
    }
    atomic_json(WORK / "receipt.json", receipt)
    if cap_reason:
        fail(f"{label}: {cap_reason}; process group terminated")
    if returncode:
        fail(f"{label} failed; inspect {stderr}")


def hardlink_overlap(original: Path, copy: Path) -> bool:
    original_ids = {(path.stat().st_dev, path.stat().st_ino) for path in original.rglob("*")
                    if path.is_file() and not path.is_symlink()}
    return any((path.stat().st_dev, path.stat().st_ino) in original_ids for path in copy.rglob("*")
               if path.is_file() and not path.is_symlink())


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        fail("CIX_RELEASE_LEASE=1 is required")
    if WORK.exists():
        fail(f"refusing to reuse work directory: {WORK}")
    if not RETAINED_TARGET.is_dir() or not CLOSURE.is_file() or not CODEC_SDK_LIBDIR.is_dir() or not RETAINED_WORKSPACE_LOCK.is_file():
        fail("retained LTO target, workspace lock, selected-provider closure, or installed native library directory is absent")
    scope = required_quality_scope()
    cargo = shutil.which("cargo")
    if cargo is None:
        fail("cargo is not on PATH")
    WORK.mkdir(parents=True)
    original_target_hashes_before = file_hashes(RETAINED_TARGET)
    workspace_lock_proof = compatible_workspace_lock()
    sdk_inputs_before = sdk_linker_inputs()
    receipt: dict[str, object] = {
        "schema": "cix-native-final-source-v1", "status": "running",
        "scope": "allowlisted current native snapshot; fmt, all-target Clippy -D warnings, release-lto binary build, and four focused native/CLI test targets",
        "non_claims": ["not full library or all integration regression", "not provider-runtime closure", "not Windows, package-manager, or final RC acceptance"],
        "quality_scope": identity(QUALITY_SCOPE), "quality_scope_record": scope,
        "original_retained_target_before": {"bytes": tree_bytes(RETAINED_TARGET), "files_sha256": original_target_hashes_before},
        "selected_provider_closure": identity(CLOSURE), "workspace_lock_compatibility": workspace_lock_proof,
        "installed_native_library_directory": str(CODEC_SDK_LIBDIR), "sdk_linker_inputs_before": sdk_inputs_before,
        "limits": {"all_new_work_cap_bytes": WORK_CAP, "cargo_build_jobs": 4, "test_threads": 1},
        "phases": {},
    }
    try:
        copied_target = WORK / "target"
        run_phase("copy-retained-lto-cache", ["/usr/bin/cp", "-a", "--reflink=auto", str(RETAINED_TARGET), str(copied_target)], os.environ.copy(), receipt)
        if hardlink_overlap(RETAINED_TARGET, copied_target):
            fail("copied LTO cache shares a hardlink with immutable retained evidence")
        receipt["copied_lto_target"] = {"path": str(copied_target), "bytes": tree_bytes(copied_target), "files_sha256": file_hashes(copied_target)}
        export_root = WORK / "export"
        run_phase("allowlisted-export", ["/usr/bin/python3", str(EXPORTER), "--source-root", str(NATIVE),
                  "--manifest", str(ALLOWLIST), "--output-directory", str(export_root),
                  "--profile", "engineering-validation"], os.environ.copy(), receipt)
        snapshot_root = export_root / "cix-0.1.0"
        snapshot = snapshot_root / "rust/cix-native"
        manifest, native_lockfile = snapshot_root / "Cargo.toml", snapshot / "Cargo.lock"
        lockfile = snapshot_root / "Cargo.lock"
        shutil.copy2(RETAINED_WORKSPACE_LOCK, lockfile)
        if lock_packages(lockfile) != lock_packages(RETAINED_WORKSPACE_LOCK):
            fail("copied qualified workspace lockfile changed while staging")
        if not manifest.is_file() or not native_lockfile.is_file() or not lockfile.is_file():
            fail("allowlisted export did not produce the native lockfile and true workspace lockfile")
        snapshot_hashes_before = file_hashes(snapshot)
        export_manifest = snapshot_root / "EXPORT-MANIFEST.json"
        export_proof_before = normalized_export_manifest(export_manifest)
        workspace_files = [manifest, lockfile, export_manifest]
        workspace_hashes_before = {str(path.relative_to(snapshot_root)): sha256(path) for path in workspace_files}
        receipt["snapshot"] = {"workspace_manifest": identity(manifest), "workspace_lockfile": identity(lockfile),
                               "native_lockfile": identity(native_lockfile), "workspace_file_hashes_before": workspace_hashes_before,
                               "normalized_export_member_hashes_before": export_proof_before,
                               "native_file_hashes_before": snapshot_hashes_before}
        environment = os.environ.copy()
        environment.update({"CARGO_TARGET_DIR": str(copied_target), "CARGO_BUILD_JOBS": "4",
                            "CARGO_INCREMENTAL": "0", "CARGO_NET_OFFLINE": "true",
                            "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
                            "CARGO_PROFILE_RELEASE_LTO_DEBUG": "0", "TMPDIR": str(WORK / "tmp"),
                            "CIX_NATIVE_LIBRARY_DIR": str(CODEC_SDK_LIBDIR), "LIBRARY_PATH": str(CODEC_SDK_LIBDIR)})
        (WORK / "tmp").mkdir(mode=0o700)
        common = ["--manifest-path", str(manifest), "--locked", "--offline", "-p", "cix-native"]
        run_phase("format", [cargo, "fmt", "--manifest-path", str(manifest), "--check"], environment, receipt)
        run_phase("clippy", [cargo, "clippy", *common, "--all-targets", "--", "-D", "warnings"], environment, receipt)
        run_phase("release-lto-binaries", [cargo, "build", *common, "--bins", "--profile", "release-lto"], environment, receipt)
        run_phase("test-cli-program-aliases", [cargo, "test", *common, "--lib", "cli::tests::program_name_normalization_is_platform_specific", "--", "--test-threads=1"], environment, receipt)
        for target in ("zpaq_backend", "full_engine_constraints", "cli_smoke"):
            run_phase(f"test-{target}", [cargo, "test", *common, "--test", target, "--", "--test-threads=1"], environment, receipt)
        snapshot_hashes_after = file_hashes(snapshot)
        receipt["snapshot"]["native_file_hashes_after"] = snapshot_hashes_after
        if snapshot_hashes_before != snapshot_hashes_after:
            fail("allowlisted snapshot changed during qualification")
        workspace_hashes_after = {str(path.relative_to(snapshot_root)): sha256(path) for path in workspace_files}
        receipt["snapshot"]["workspace_file_hashes_after"] = workspace_hashes_after
        export_proof_after = normalized_export_manifest(export_manifest)
        receipt["snapshot"]["normalized_export_member_hashes_after"] = export_proof_after
        if export_proof_before != export_proof_after:
            fail("source-export member hash proof changed during qualification")
        if workspace_hashes_before != workspace_hashes_after:
            fail("workspace manifest, lockfile, or export manifest changed during qualification")
        sdk_inputs_after = sdk_linker_inputs()
        receipt["sdk_linker_inputs_after"] = sdk_inputs_after
        if sdk_inputs_before != sdk_inputs_after:
            fail("selected installed SDK linker inputs changed during qualification")
        original_target_hashes_after = file_hashes(RETAINED_TARGET)
        receipt["original_retained_target_after"] = {"bytes": tree_bytes(RETAINED_TARGET), "files_sha256": original_target_hashes_after}
        if original_target_hashes_before != original_target_hashes_after:
            fail("immutable retained LTO evidence changed during qualification")
        receipt["release_lto_binaries"] = {name: identity(copied_target / "release-lto" / name)
                                            for name in ("cix", "uncix", "cixcat")}
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        receipt["work_bytes_final"] = tree_bytes(WORK) if WORK.exists() else 0
        receipt["original_retained_target_after"] = {"bytes": tree_bytes(RETAINED_TARGET), "files_sha256": file_hashes(RETAINED_TARGET)} if RETAINED_TARGET.exists() else {}
        if receipt.get("original_retained_target_after", {}).get("files_sha256") != original_target_hashes_before:
            receipt["immutable_retained_target_changed"] = True
        atomic_json(JOB / "receipt.json", receipt)
        atomic_json(JOB / "source.json", receipt.get("snapshot", {}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"native-final-source-v1: {error}", file=sys.stderr)
        raise SystemExit(1)
