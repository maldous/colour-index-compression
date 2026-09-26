from pathlib import Path

from cix.multinomial import StreamConfig
from cix.transforms import SPECS
from cix.record import BASE_WIDTHS


FORBIDDEN_CONFIG_FIELDS = {
    "enable_tokens",
    "enable_raster",
    "text_block_target",
    "text_adaptive",
    "text_persistent_adaptive",
}

FORBIDDEN_TRANSFORM_TERMS = {
    "x86",
    "e8e9",
    "sparc",
    "fax",
    "raster",
    "jpeg",
    "png",
    "json",
    "xml",
}


def test_canonical_config_has_no_content_specific_switches():
    fields = set(StreamConfig.__dataclass_fields__)
    assert not (fields & FORBIDDEN_CONFIG_FIELDS)


def test_transform_portfolio_is_format_agnostic():
    names = {spec.name.lower() for spec in SPECS}
    for name in names:
        assert not any(term in name for term in FORBIDDEN_TRANSFORM_TERMS)

    # Long benchmark-specific periods must be discovered generically rather than
    # embedded as magic constants in the canonical transform list.
    assert "byte-xor-216" not in names
    assert "byte-xor-432" not in names


def test_no_removed_semantic_modules_remain():
    root = Path(__file__).resolve().parents[1] / "cix"
    assert not (root / "tokens.py").exists()
    assert not (root / "raster.py").exists()


def test_record_width_priors_are_generic():
    # Benchmark/media-specific scanline constants must be discovered from bytes,
    # never embedded in the canonical candidate list.
    assert 216 not in BASE_WIDTHS
    assert 432 not in BASE_WIDTHS
