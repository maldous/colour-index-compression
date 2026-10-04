#!/usr/bin/env python3
"""Lease-gated continuation of the immutable native-final-source-v2 snapshot."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[5]
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/native-final-source-v3"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/native-final-source-v3"
V2_JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/native-final-source-v2"
V2_WORK = PROJECT / "benchmark-work/native-rc-check-v1/native-final-source-v2"
RETAINED_TARGET = PROJECT / "benchmark-work/native-rc-check-v1/distribution-engineering-v4/target"
CLOSURE = PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"
CODEC_SDK_LIBDIR = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix/usr/lib/x86_64-linux-gnu"
QUALITY_SCOPE = PROJECT / "benchmark-work/native-rc-check-v1/native-final-source-v3.quality-scope.json"
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
    return {name: identity(CODEC_SDK_LIBDIR / name)
            for name in ("libcharls.so", "libopenjp2.so", "liblz4.so", "libsnappy.so")}


def normalized_export_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    members = value.get("members_sha256")
    if value.get("schema") != "cix-native-materialised-source-export-v1" or not isinstance(members, dict):
        fail("v2 export manifest is not the expected allowlisted source proof")
    return {"schema": value["schema"], "profile": value.get("profile"),
            "dependency_closure_status": value.get("dependency_closure_status"),
            "members_sha256": dict(sorted(members.items()))}


def require_quality_scope() -> dict[str, object]:
    try:
        value = json.loads(QUALITY_SCOPE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"root v3 quality_scope record is required: {error}")
    if not isinstance(value, dict) or value.get("schema") != "cix-native-quality-scope-v1" or value.get("approved_by_root") is not True:
        fail("v3 quality_scope is not root approved")
    if value.get("cache_archive_verified") is not True or value.get("cache_prune_complete") is not True:
        fail("v3 quality_scope must record cache preservation and prune")
    if value.get("shared_work_ceiling_bytes") != 4_000_000_000 or value.get("admitted_new_work_bytes", 0) < WORK_CAP:
        fail("v3 quality_scope does not admit this 720 MB work cap")
    fresh = allocated_bytes(WORK.parent)
    if fresh + WORK_CAP > 4_000_000_000:
        fail("fresh shared work plus v3 cap exceeds 4 GB")
    value["fresh_existing_work_bytes"] = fresh
    return value


def hardlink_overlap(original: Path, copy: Path) -> bool:
    originals = {(path.stat().st_dev, path.stat().st_ino) for path in original.rglob("*")
                 if path.is_file() and not path.is_symlink()}
    return any((path.stat().st_dev, path.stat().st_ino) in originals for path in copy.rglob("*")
               if path.is_file() and not path.is_symlink())


def run_phase(label: str, argv: list[str], env: dict[str, str], receipt: dict) -> None:
    stdout, stderr = WORK / f"{label}.stdout.log", WORK / f"{label}.stderr.log"
    started, peak, cap_reason = time.time(), tree_bytes(WORK), None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        child = subprocess.Popen(argv, cwd=WORK, env=env, stdout=out, stderr=err, start_new_session=True)
        while child.poll() is None:
            current = tree_bytes(WORK)
            peak = max(peak, current)
            if current > WORK_CAP:
                cap_reason = f"all new v3 work exceeded {WORK_CAP} bytes"
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
    peak = max(peak, tree_bytes(WORK))
    if peak > WORK_CAP and cap_reason is None:
        cap_reason = f"all new v3 work exceeded {WORK_CAP} bytes"
    receipt["phases"][label] = {"argv": argv, "returncode": returncode,
        "elapsed_seconds": round(time.time() - started, 3), "stdout": str(stdout), "stderr": str(stderr),
        "sample_interval_seconds": SAMPLE_SECONDS, "sampled_peak_all_new_work_bytes": peak, "cap_reason": cap_reason}
    atomic_json(WORK / "receipt.json", receipt)
    if cap_reason:
        fail(f"{label}: {cap_reason}; process group terminated")
    if returncode:
        fail(f"{label} failed; inspect {stderr}")


def v2_snapshot_proof() -> tuple[Path, Path, dict[str, object]]:
    receipt_path = V2_JOB / "receipt.json"
    try:
        predecessor = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read v2 receipt: {error}")
    if predecessor.get("schema") != "cix-native-final-source-v2":
        fail("v2 receipt schema is not accepted")
    format_phase = predecessor.get("phases", {}).get("format")
    if not isinstance(format_phase, dict) or format_phase.get("returncode") != 0:
        fail("v2 did not record a successful all-workspace format phase")
    snapshot = V2_WORK / "export/cix-0.1.0/rust/cix-native"
    root = snapshot.parents[1]
    manifest, lockfile, export_manifest = root / "Cargo.toml", root / "Cargo.lock", root / "EXPORT-MANIFEST.json"
    recorded = predecessor.get("snapshot")
    if not isinstance(recorded, dict) or not all(path.is_file() for path in (manifest, lockfile, export_manifest)):
        fail("v2 immutable snapshot or source proof is absent")
    if file_hashes(snapshot) != recorded.get("native_file_hashes_before"):
        fail("v2 native snapshot no longer matches its frozen source hashes")
    workspace = {str(path.relative_to(root)): sha256(path) for path in (manifest, lockfile, export_manifest)}
    if workspace != recorded.get("workspace_file_hashes_before"):
        fail("v2 workspace manifest, qualified lockfile, or export manifest changed")
    proof = normalized_export_manifest(export_manifest)
    if proof != recorded.get("normalized_export_member_hashes_before"):
        fail("v2 normalized export member hashes changed")
    return root, snapshot, {"receipt": identity(receipt_path), "format_phase": format_phase,
                            "workspace_hashes": workspace, "native_file_hashes": file_hashes(snapshot),
                            "normalized_export_member_hashes": proof}


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        fail("CIX_RELEASE_LEASE=1 is required")
    if WORK.exists():
        fail(f"refusing to reuse v3 work directory: {WORK}")
    if not RETAINED_TARGET.is_dir() or not CLOSURE.is_file() or not CODEC_SDK_LIBDIR.is_dir():
        fail("required retained target, provider closure, or SDK library directory is absent")
    scope = require_quality_scope()
    cargo = shutil.which("cargo")
    if cargo is None:
        fail("cargo is not on PATH")
    workspace_root, snapshot, v2_proof = v2_snapshot_proof()
    original_hashes_before, sdk_before = file_hashes(RETAINED_TARGET), sdk_linker_inputs()
    WORK.mkdir(parents=True)
    receipt: dict[str, object] = {"schema": "cix-native-final-source-v3", "status": "running",
        "scope": "continuation from immutable v2 snapshot after its successful all-workspace format phase; Clippy, release-lto binaries, and focused tests only",
        "non_claims": ["no source export, lockfile rewrite, or format rerun", "not full regression, provider closure, Windows, package-manager, or final RC acceptance"],
        "quality_scope": identity(QUALITY_SCOPE), "quality_scope_record": scope, "prior_v2": v2_proof,
        "selected_provider_closure": identity(CLOSURE), "sdk_linker_inputs_before": sdk_before,
        "original_retained_target_before": {"bytes": tree_bytes(RETAINED_TARGET), "files_sha256": original_hashes_before},
        "limits": {"all_new_work_cap_bytes": WORK_CAP, "cargo_build_jobs": 4, "test_threads": 1}, "phases": {}}
    try:
        copied_target = WORK / "target"
        run_phase("copy-retained-lto-cache", ["/usr/bin/cp", "-a", "--reflink=auto", str(RETAINED_TARGET), str(copied_target)], os.environ.copy(), receipt)
        if hardlink_overlap(RETAINED_TARGET, copied_target):
            fail("v3 target copy shares hardlinks with retained evidence")
        receipt["copied_lto_target"] = {"path": str(copied_target), "bytes": tree_bytes(copied_target), "files_sha256": file_hashes(copied_target)}
        environment = os.environ.copy()
        environment.update({"CARGO_TARGET_DIR": str(copied_target), "CARGO_BUILD_JOBS": "4", "CARGO_INCREMENTAL": "0",
            "CARGO_NET_OFFLINE": "true", "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
            "TMPDIR": str(WORK / "tmp"), "CIX_NATIVE_LIBRARY_DIR": str(CODEC_SDK_LIBDIR), "LIBRARY_PATH": str(CODEC_SDK_LIBDIR)})
        (WORK / "tmp").mkdir(mode=0o700)
        common = ["--manifest-path", str(workspace_root / "Cargo.toml"), "--locked", "--offline", "-p", "cix-native"]
        run_phase("clippy", [cargo, "clippy", *common, "--all-targets", "--", "-D", "warnings"], environment, receipt)
        run_phase("release-lto-binaries", [cargo, "build", *common, "--bins", "--profile", "release-lto"], environment, receipt)
        run_phase("test-cli-program-aliases", [cargo, "test", *common, "--lib", "cli::tests::program_name_normalization_is_platform_specific", "--", "--test-threads=1"], environment, receipt)
        for target in ("zpaq_backend", "full_engine_constraints", "cli_smoke"):
            run_phase(f"test-{target}", [cargo, "test", *common, "--test", target, "--", "--test-threads=1"], environment, receipt)
        _, _, v2_after = v2_snapshot_proof()
        if v2_proof["workspace_hashes"] != v2_after["workspace_hashes"] or v2_proof["native_file_hashes"] != v2_after["native_file_hashes"]:
            fail("immutable v2 snapshot changed during v3")
        if sdk_before != sdk_linker_inputs():
            fail("selected SDK linker inputs changed during v3")
        if original_hashes_before != file_hashes(RETAINED_TARGET):
            fail("retained original LTO evidence changed during v3")
        receipt["release_lto_binaries"] = {name: identity(copied_target / "release-lto" / name) for name in ("cix", "uncix", "cixcat")}
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"; receipt["error"] = str(error); raise
    finally:
        receipt["work_bytes_final"] = tree_bytes(WORK) if WORK.exists() else 0
        receipt["original_retained_target_after"] = {"bytes": tree_bytes(RETAINED_TARGET), "files_sha256": file_hashes(RETAINED_TARGET)} if RETAINED_TARGET.exists() else {}
        receipt["sdk_linker_inputs_after"] = sdk_linker_inputs() if CODEC_SDK_LIBDIR.is_dir() else {}
        atomic_json(JOB / "receipt.json", receipt)
        atomic_json(JOB / "source.json", receipt.get("prior_v2", {}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"native-final-source-v3: {error}", file=sys.stderr)
        raise SystemExit(1)
