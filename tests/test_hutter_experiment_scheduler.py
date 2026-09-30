import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.hutter_bounded_runner import build_identity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cpu():
    return min(os.sched_getaffinity(0))


def manifest(tmp_path, source, name):
    row = {
        "hypothesis": "fake scheduler control", "matched_control": "fake",
        "input": {"path": str(source), "offset": 0, "length": source.stat().st_size, "sha256": digest(source)},
        "configuration": {"name": name}, "mechanism": "test",
        "budget": {"wall_seconds": 1, "max_rss_bytes": 1024, "max_temp_bytes": 1024, "cpu": cpu()},
        "promotion_criteria": "none", "build_paths": ["fake.py"],
        "encode_command": ["unused"], "decode_command": ["unused"],
        "artifacts": {"archive": "unused", "restored": "unused"},
    }
    path = tmp_path / f"{name}.json"; path.write_text(json.dumps(row)); return path


def fake_runner(tmp_path, status="VERIFIED_SCREENING", code=0):
    path = tmp_path / "runner.py"
    path.write_text(
        "import argparse,hashlib,json,shutil\nfrom pathlib import Path\n"
        "p=argparse.ArgumentParser();p.add_argument('--manifest');p.add_argument('--results');p.add_argument('--root');a=p.parse_args()\n"
        "m=json.loads(Path(a.manifest).read_text()); canon=json.dumps(m,sort_keys=True,separators=(',',':')).encode(); source=Path(m['input']['path']); out=Path(a.results)/'proof'; out.mkdir(parents=True,exist_ok=True); archive=out/'archive'; restored=out/'restored'\n"
        "def h(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()\n"
        f"status={status!r}\n"
        "if status=='VERIFIED_SCREENING':\n"
        " shutil.copyfile(source,archive);shutil.copyfile(source,restored); receipt=out/'receipt.json'; row={'status':status,'identity':{'manifest_sha256':hashlib.sha256(canon).hexdigest(),'input':m['input']},'verification':{'matched':True,'source_sha256':h(source),'restored_sha256':h(restored)},'artifacts':{'archive':str(archive),'restored':str(restored)},'archive_bytes':archive.stat().st_size,'archive_sha256':h(archive)};receipt.write_text(json.dumps(row)); print(json.dumps({'status':status,'receipt':str(receipt)}))\n"
        "else: print(json.dumps({'status':status}))\n"
        f"raise SystemExit({code})\n")
    return (sys.executable, str(path))


def cell(path, output, name, **extra):
    row = json.loads(path.read_text())
    expected = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"cell_id": name, "owner": "agent-test", "manifest_path": str(path), "output_dir": str(output),
            "expected_manifest_sha256": expected, **extra}


def scheduler(tmp_path, command):
    (tmp_path / "benchmarks").mkdir(exist_ok=True)
    (tmp_path / "fake.py").write_text("# frozen fake build\n")
    return WaveScheduler(tmp_path, max_memory_bytes=10_000, max_temp_bytes=10_000,
                         min_free_disk_bytes=1, runner_command=command, progress_seconds=0.01)


def test_verified_cell_is_reused_without_relaunch_and_claim_is_immutable(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path))
    plan = manifest(tmp_path, source, "one"); request = cell(plan, tmp_path / "out", "one")
    assert runner.run_wave([request])[0]["runner_status"] == "VERIFIED_SCREENING"
    claim = tmp_path / ".hutter-experiment-scheduler/claims/one.claim.json"; before = claim.read_bytes()
    assert runner.run_wave([request])[0]["status"] == "REUSED_VERIFIED"
    assert claim.read_bytes() == before


def test_terminal_negative_is_preserved_and_same_manifest_needs_justification(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path, "FAILED", 1))
    plan = manifest(tmp_path, source, "shared")
    first = cell(plan, tmp_path / "one", "one")
    assert runner.run_wave([first])[0]["runner_status"] == "FAILED"
    assert runner.run_wave([first])[0]["status"] == "TERMINAL_NEGATIVE"
    with pytest.raises(ValueError, match="fresh_justification"):
        runner.run_wave([cell(plan, tmp_path / "two", "two")])
    assert runner.run_wave([cell(plan, tmp_path / "two", "two", fresh_justification="independent new matrix cell")])[0]["cell_id"] == "two"


def test_hash_and_physical_core_conflicts_reject_before_claims(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path))
    first, second = manifest(tmp_path, source, "a"), manifest(tmp_path, source, "b")
    bad = cell(first, tmp_path / "out", "bad", expected_manifest_sha256="0" * 64)
    with pytest.raises(ValueError, match="expected_manifest"):
        runner.run_wave([bad])
    with pytest.raises(ValueError, match="overlapping physical"):
        runner.run_wave([cell(first, tmp_path / "a", "a"), cell(second, tmp_path / "b", "b")])
    assert not (tmp_path / ".hutter-experiment-scheduler/claims/a.claim.json").exists()


def test_reuse_rehashes_receipt_and_refuses_tampered_artifact(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path))
    plan = manifest(tmp_path, source, "tamper"); request = cell(plan, tmp_path / "out", "tamper")
    first = runner.run_wave([request])[0]
    receipt = json.loads((tmp_path / ".hutter-experiment-scheduler/claims/tamper.terminal.json").read_text())["runner_result"]["receipt"]
    archive = Path(json.loads(Path(receipt).read_text())["artifacts"]["archive"]); archive.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="cannot be rehashed"):
        runner.run_wave([request])
    assert first["runner_status"] == "VERIFIED_SCREENING"


def test_same_cell_id_rejects_changed_immutable_identity(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path))
    plan = manifest(tmp_path, source, "identity"); request = cell(plan, tmp_path / "out", "identity")
    runner.run_wave([request])
    changed = cell(plan, tmp_path / "different-output", "identity")
    with pytest.raises(ValueError, match="different immutable claim identity"):
        runner.run_wave([changed])
    with pytest.raises(ValueError, match="different immutable claim identity"):
        runner.run_wave([cell(plan, tmp_path / "out", "identity", owner="different-owner")])
    replacement = manifest(tmp_path, source, "different-manifest")
    with pytest.raises(ValueError, match="different immutable claim identity"):
        runner.run_wave([cell(replacement, tmp_path / "out", "identity")])


def test_global_wave_lock_blocks_concurrent_scheduler(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path)); runner.state.mkdir(parents=True, exist_ok=True)
    with runner._wave_lock_path().open("a+") as held:
        import fcntl
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="global aggregate"):
            runner.run_wave([cell(manifest(tmp_path, source, "locked"), tmp_path / "out", "locked")])


def test_expected_build_identity_refuses_source_drift_before_launch_or_reuse(tmp_path):
    source = tmp_path / "source"; source.write_bytes(b"source")
    runner = scheduler(tmp_path, fake_runner(tmp_path))
    plan = manifest(tmp_path, source, "build")
    frozen = build_identity(json.loads(plan.read_text()), tmp_path)
    request = cell(plan, tmp_path / "out", "build", expected_build_sha256=frozen)
    assert runner.run_wave([request])[0]["runner_status"] == "VERIFIED_SCREENING"
    (tmp_path / "fake.py").write_text("# changed after claim\n")
    with pytest.raises(ValueError, match="expected_build_sha256"):
        runner.run_wave([request])
