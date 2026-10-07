"""Freeze an allowlisted current source and admit the bounded PAQ loader check."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/paq-supervisor-groups-v1"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError("refusing an existing source freeze")
    native = module("prior_native_freeze", JOB.parent / "native-final-source-v2/run.py")
    loader = module("paq_loader_qualification", JOB.parent / "paq-supervisor-groups-v1/run.py")
    preserve = json.loads((JOB.parent / "preserve-native-final-v3-target-v1/receipt.json").read_text())
    if preserve.get("status") != "pass":
        raise RuntimeError("target preservation did not pass")
    existing = native.allocated_bytes(WORK.parent)
    if existing + loader.CAP > 4_000_000_000:
        raise RuntimeError("retained work plus 600 MB job exceeds 4 GB")
    lock = native.compatible_workspace_lock()
    inputs = {str(p): native.sha256(p) for p in (native.EXPORTER, native.ALLOWLIST,
              JOB / "run.py", JOB.parent / "paq-supervisor-groups-v1/run.py",
              JOB.parent / "paq-supervisor-groups-v1/spec.json")}
    WORK.mkdir()
    staging = WORK / "export"
    subprocess.run(["python3", str(native.EXPORTER), "--source-root", str(native.NATIVE),
        "--manifest", str(native.ALLOWLIST), "--output-directory", str(staging),
        "--profile", "engineering-validation"], check=True)
    (staging / "cix-0.1.0").rename(WORK / "source")
    staging.rmdir()
    shutil.copy2(native.RETAINED_WORKSPACE_LOCK, WORK / "source/Cargo.lock")
    frozen = loader.snapshot()
    providers = loader.providers()
    scope = {"schema": "cix-native-quality-scope-v1", "approved_by_root": True,
        "cache_archive_verified": True, "cache_prune_complete": True,
        "shared_work_ceiling_bytes": 4_000_000_000, "admitted_new_work_bytes": loader.CAP,
        "existing_work_bytes": existing, "workspace_files_sha256": frozen["workspace_files_sha256"],
        "native_files_sha256": frozen["native_files_sha256"],
        "preservation_receipt_sha256": hashlib.sha256((JOB.parent / "preserve-native-final-v3-target-v1/receipt.json").read_bytes()).hexdigest(),
        "scope": "Focused common PAQ loader tests only; no RC or platform acceptance"}
    loader.SCOPE.write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n")
    result = {"status": "pass", "source": frozen, "quality_scope": scope,
              "workspace_lock": lock, "providers": providers, "inputs": inputs}
    (JOB / "receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
