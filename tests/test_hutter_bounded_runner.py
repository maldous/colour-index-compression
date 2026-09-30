import hashlib
import json
import sys
from pathlib import Path

import pytest

from benchmarks.hutter_bounded_runner import run


def runner_cpu():
    """The runner smoke suite has a single declared CPU-6, 1-GiB envelope."""
    return 6 if 6 in __import__("os").sched_getaffinity(0) else min(__import__("os").sched_getaffinity(0))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(tmp_path, source, script, **changes):
    row = {
        "hypothesis": "copy framing is a control smoke",
        "matched_control": "raw copy",
        "input": {"path": str(source), "offset": 0, "length": source.stat().st_size, "sha256": digest(source)},
        "configuration": {"codec": "test"}, "mechanism": "none",
        "budget": {"wall_seconds": 3, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()},
        "promotion_criteria": "exact restoration", "build_paths": [script.name],
        "command": [sys.executable, str(script), "{source}", "{workdir}/archive", "{workdir}/restored"],
        "artifacts": {"archive": "{workdir}/archive", "restored": "{workdir}/restored"},
    }
    row.update(changes)
    path = tmp_path / "manifest.json"; path.write_text(json.dumps(row)); return path


def write_copy(path):
    path.write_text("import shutil,sys\nshutil.copyfile(sys.argv[1],sys.argv[2]); shutil.copyfile(sys.argv[1],sys.argv[3])\n")


def test_verified_receipt_then_matching_reuse(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"bounded runner" * 100)
    script = tmp_path / "copy.py"; write_copy(script)
    result = run(manifest(tmp_path, source, script), tmp_path / "results", tmp_path)
    assert result["status"] == "VERIFIED" and result["verification"]["matched"]
    cached = run(manifest(tmp_path, source, script), tmp_path / "results", tmp_path)
    assert cached["status"] == "REUSED_VERIFIED"


def test_input_hash_failure_prevents_launch(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script)
    row = json.loads(path.read_text()); row["input"]["sha256"] = "0" * 64; path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="input range hash mismatch"):
        run(path, tmp_path / "results", tmp_path)


def test_timeout_kills_child_process_group_and_writes_failure(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "sleep.py"; script.write_text("import time\ntime.sleep(60)\n")
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 1, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()})
    result = run(path, tmp_path / "results", tmp_path)
    assert result["status"] == "FAILED" and result["stop_reason"] == "wall_budget_exhausted"


def test_unverified_receipt_is_not_reused_and_build_change_is_a_new_identity(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script)
    first = run(path, tmp_path / "results", tmp_path)
    receipt = Path(first["receipt"]); row = json.loads(receipt.read_text()); row["verification"]["matched"] = False; receipt.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="existing receipt"):
        run(path, tmp_path / "results", tmp_path)
    script.write_text(script.read_text() + "# changed build\n")
    second = run(path, tmp_path / "results", tmp_path)
    assert second["status"] == "VERIFIED" and second["experiment_id"] != first["experiment_id"]


def test_temp_budget_stops_run(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "write.py"; script.write_text("from pathlib import Path\nimport time\nPath('large').write_bytes(b'x'*10000); time.sleep(60)\n")
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 3, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 100, "cpu": runner_cpu()})
    result = run(path, tmp_path / "results", tmp_path)
    assert result["stop_reason"] == "temp_budget_exhausted"
