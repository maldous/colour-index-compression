import hashlib
import json
from pathlib import Path

import pytest

from benchmarks import hutter_wikipedia_matrix as matrix
from benchmarks import hutter_opportunity_inputs as inputs


def test_immutable_claim_cannot_be_redefined(tmp_path):
    path = tmp_path / "claim.json"
    matrix.immutable(path, {"owner": "A", "input": "exact"})
    matrix.immutable(path, {"input": "exact", "owner": "A"})
    with pytest.raises(ValueError, match="immutable record changed"):
        matrix.immutable(path, {"owner": "B", "input": "exact"})


def test_reserved_cores_and_unowned_trials_cannot_prepare(tmp_path):
    with pytest.raises(ValueError, match="CPU4/6"):
        matrix.prepare("irrelevant", "original", "/root/worker", 0, tmp_path)
    with pytest.raises(ValueError, match="owner"):
        matrix.prepare("irrelevant", "original", "", 4, tmp_path)


def test_strong_body_opportunity_is_changed_lines_not_exact_copies():
    for strength in ("strong", "weak", "absent"):
        spec = next(s for s in inputs.default_specs() if s["opportunity"] == "repeated_body_families" and s["strength"] == strength)
        observed = inputs.provenance(spec)["mechanistic_diagnostics"]
        if strength == "absent":
            assert observed["body_codec_eligible_members"] == 0
        else:
            assert observed["body_codec_eligible_members"] >= 3
            assert observed["body_codec_distinct_raw_lines"] == observed["body_codec_eligible_members"]


def test_sweep_inputs_have_matched_one_factor_provenance(tmp_path, monkeypatch):
    # One class is enough to test registry/contrast integration without copying
    # the full suite into every test run.
    monkeypatch.setattr(inputs, "CLASSES", ("repeated_body_families",))
    rows = matrix.register_sweeps(tmp_path)
    assert len(rows) == 21
    base = rows[0]
    assert all(row["base_input_id"] == base["input_id"] for row in rows)
    assert all(len(row["changed_parameters"]) == 1 for row in rows[1:])
    assert all(Path(row["path"]).is_file() for row in rows)
    for row in rows:
        registry = tmp_path / matrix.REL / "registry"
        record = json.loads((registry / "inputs" / (row["input_id"] + ".json")).read_text())
        assert hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() == record["range_sha256"]
