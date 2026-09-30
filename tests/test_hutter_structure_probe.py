import pytest

from benchmarks.hutter_structure_probe import inverse, transform


def test_b_inverse_preserves_literal_fallback_for_malformed_markup():
    source = b"<page><title>broken</page>"
    transformed, metadata = transform(source, "B")
    assert metadata["mode"] == 0
    assert inverse(transformed, 3, metadata) == source


def test_b_inverse_preserves_literal_fallback_without_markup_events():
    source = b"ordinary prose without tags"
    transformed, metadata = transform(source, "B")
    assert metadata["mode"] == 0
    assert inverse(transformed, 3, metadata) == source


def test_b_inverse_restores_wellformed_stack_prediction_mode_one():
    source = b"<page><title>x</title><id>1</id></page>"
    transformed, metadata = transform(source, "B")
    assert metadata["mode"] == 1
    assert inverse(transformed, 3, metadata) == source


@pytest.mark.parametrize("metadata", [{}, {"mode": 2}, {"mode": "1"}, None])
def test_b_inverse_rejects_invalid_metadata_mode(metadata):
    with pytest.raises(ValueError, match="metadata mode"):
        inverse(b"anything", 3, metadata)
