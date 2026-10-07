import json

import pytest

from benchmarks.hutter_experiment_registry import Registry


HASH = "a" * 64
RANGE = "b" * 64


def test_input_is_content_addressed_and_location_free(tmp_path):
    registry = Registry(tmp_path / "registry")
    first = registry.register_input(HASH, 0, 64, RANGE)
    second = registry.register_input(HASH, 0, 64, RANGE)
    assert first == second
    assert registry.get_input(first) == {"dataset_sha256": HASH, "offset": 0, "length": 64, "range_sha256": RANGE}
    assert registry.records("inputs") == [registry.get_input(first)]


def test_classification_and_exposure_append_immutably(tmp_path):
    registry = Registry(tmp_path / "registry")
    input_id = registry.register_input(HASH, 10, 64, RANGE)
    classification = registry.record_classification(input_id, {"language": "unknown"}, {"tool": "fixture"})
    exposure = registry.record_exposure(input_id, {"kind": "development", "evidence_refs": ["receipt:test"], "userdirective_refs": ["directive:test"]})
    assert registry.records("classifications")[0]["input_id"] == input_id
    assert registry.records("exposures")[0]["event"]["kind"] == "development"
    assert classification != exposure


def test_corruption_and_invalid_exposure_are_refused(tmp_path):
    registry = Registry(tmp_path / "registry")
    input_id = registry.register_input(HASH, 0, 1, RANGE)
    with pytest.raises(ValueError, match="kind"):
        registry.record_exposure(input_id, {"kind": "unknown", "evidence_refs": ["e"], "userdirective_refs": ["u"]})
    path = tmp_path / "registry" / "inputs" / f"{input_id}.json"
    path.chmod(0o644); path.write_text(json.dumps({"tampered": True}))
    with pytest.raises(ValueError, match="corrupt"):
        registry.get_input(input_id)


@pytest.mark.parametrize("offset,length", [(-1, 1), (0, 0)])
def test_invalid_ranges_are_refused(tmp_path, offset, length):
    with pytest.raises(ValueError):
        Registry(tmp_path / "registry").register_input(HASH, offset, length, RANGE)
