import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from benchmarks.hutter_bounded_runner import load_manifest, run


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
        "encode_command": [sys.executable, str(script), "encode", "{source}", "{workdir}/archive"],
        "decode_command": [sys.executable, str(script), "decode", "{workdir}/archive", "{workdir}/restored"],
        "artifacts": {"archive": "{workdir}/archive", "restored": "{workdir}/restored"},
    }
    row.update(changes)
    path = tmp_path / "manifest.json"; path.write_text(json.dumps(row)); return path


def write_copy(path):
    path.write_text("import shutil,sys\nshutil.copyfile(sys.argv[2],sys.argv[3])\n")


def test_verified_receipt_then_matching_reuse(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"bounded runner" * 100)
    script = tmp_path / "copy.py"; write_copy(script)
    result = run(manifest(tmp_path, source, script), tmp_path / "results", tmp_path)
    assert result["status"] == "VERIFIED_SCREENING" and result["verification"]["matched"]
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
    script = tmp_path / "sleep.py"; script.write_text(
        "import subprocess,sys,time\nfrom pathlib import Path\nchild=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\nPath('childpid').write_text(str(child.pid))\ntime.sleep(60)\n")
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 1, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()})
    result = run(path, tmp_path / "results", tmp_path)
    assert result["status"] == "FAILED" and result["phases"][0]["stop_reason"] == "wall_budget_exhausted"
    child_pid = int(next((tmp_path / "results").glob("*/work/childpid")).read_text())
    assert not Path(f"/proc/{child_pid}").exists()
    progress = [json.loads(line) for line in next((tmp_path / "results").glob("*/progress.jsonl")).read_text().splitlines()]
    assert progress[-1]["completed"] is False and progress[-1]["processed_bytes"] is None


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
    assert second["status"] == "VERIFIED_SCREENING" and second["experiment_id"] != first["experiment_id"]


def test_temp_budget_stops_run(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "write.py"; script.write_text("from pathlib import Path\nimport time\nPath('large').write_bytes(b'x'*10000); time.sleep(60)\n")
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 3, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 100, "cpu": runner_cpu()})
    result = run(path, tmp_path / "results", tmp_path)
    assert result["phases"][0]["stop_reason"] == "temp_budget_exhausted"


def test_moderate_contiguous_budget_requires_all_explicit_guards(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 1200, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()})
    with pytest.raises(ValueError, match="moderate_contiguous"):
        load_manifest(path)
    row = json.loads(path.read_text()); row["stage"] = "moderate_contiguous"; row["longer_budget_justification"] = "contiguous 4 MiB context screen"; path.write_text(json.dumps(row))
    assert load_manifest(path)[0]["budget"]["wall_seconds"] == 1200
    row["input"]["length"] = 16 * 1024 * 1024 + 1; path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="input <=16MiB"):
        load_manifest(path)


def test_regular_budget_limit_remains_300_seconds(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script, budget={"wall_seconds": 301, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()})
    with pytest.raises(ValueError, match="1..300"):
        load_manifest(path)


def test_cached_artifact_tamper_is_refused(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script)
    first = run(path, tmp_path / "results", tmp_path)
    archive = Path(first["artifacts"]["archive"]); archive.write_bytes(archive.read_bytes() + b"!")
    with pytest.raises(ValueError, match="existing receipt"):
        run(path, tmp_path / "results", tmp_path)


def test_completed_non_gain_skips_decoder_and_is_never_reused(tmp_path):
    source = tmp_path / "input"; source.write_bytes(b"gate control" * 40)
    control_script = tmp_path / "copy.py"; write_copy(control_script)
    results = tmp_path / "results"
    control = run(manifest(tmp_path, source, control_script), results, tmp_path)
    control_receipt = Path(control["receipt"]); control_archive = Path(control["artifacts"]["archive"])
    candidate_script = tmp_path / "larger.py"; candidate_script.write_text(
        "import pathlib,sys\n"
        "if sys.argv[1]=='encode': pathlib.Path(sys.argv[3]).write_bytes(pathlib.Path(sys.argv[2]).read_bytes()+b'!')\n"
        "else: raise RuntimeError('decoder must not run')\n")
    gate = {"control_receipt": str(control_receipt.resolve()), "archive_sha256": digest(control_archive),
            "control_bytes": control_archive.stat().st_size, "matching_configuration_keys": ["codec"]}
    candidate = run(manifest(tmp_path, source, candidate_script, decode_size_gate=gate), results, tmp_path)
    assert candidate["status"] == "SIZE_REJECTED_UNVERIFIED"
    assert candidate["phases"][0]["exit_code"] == 0 and candidate["phases"][1] is None
    assert candidate["verification"]["matched"] is False
    rejected = next(results.glob("*/size-rejected.json")); assert json.loads(rejected.read_text())["archive_bytes"] > gate["control_bytes"]
    with pytest.raises(ValueError, match="size-rejected experiment"):
        run(manifest(tmp_path, source, candidate_script, decode_size_gate=gate), results, tmp_path)


@pytest.mark.parametrize("kind", ("input", "configuration", "hash"))
def test_size_gate_mismatch_refuses_before_candidate_encode(tmp_path, kind):
    source = tmp_path / "input"; source.write_bytes(b"control")
    script = tmp_path / "copy.py"; write_copy(script)
    results = tmp_path / "results"; control = run(manifest(tmp_path, source, script), results, tmp_path)
    archive = Path(control["artifacts"]["archive"])
    gate = {"control_receipt": str(Path(control["receipt"]).resolve()), "archive_sha256": digest(archive),
            "control_bytes": archive.stat().st_size, "matching_configuration_keys": ["codec"]}
    candidate_source = source
    changes = {"decode_size_gate": gate}
    if kind == "input":
        candidate_source = tmp_path / "other"; candidate_source.write_bytes(b"different")
    elif kind == "configuration":
        changes["configuration"] = {"codec": "different"}
    else:
        gate["archive_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="decode_size_gate"):
        run(manifest(tmp_path, candidate_source, script, **changes), results, tmp_path)
    assert len(list(results.glob("*/work/archive"))) == 1


@pytest.mark.parametrize("seconds", [-1, 0, 1201])
def test_moderate_budget_refuses_invalid_boundaries(tmp_path, seconds):
    source = tmp_path / "input"; source.write_bytes(b"abc")
    script = tmp_path / "copy.py"; write_copy(script)
    path = manifest(tmp_path, source, script, budget={"wall_seconds": seconds, "max_rss_bytes": 1_000_000_000, "max_temp_bytes": 1_000_000, "cpu": runner_cpu()})
    row = json.loads(path.read_text()); row["stage"] = "moderate_contiguous"; row["longer_budget_justification"] = "boundary guard"; path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match="1..300"):
        load_manifest(path)
