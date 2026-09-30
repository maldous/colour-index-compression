import pytest

from benchmarks import domain_numeric_noaa as numeric


def _source() -> bytes:
    return numeric.HEADER + b"".join([
        b"2024-01-01 00:00,1.327,0.045,0,0,0,0,p\n",
        b"2024-01-01 00:06,1.297,0.042,0,0,0,0,p\n",
        b"2024-01-01 00:12,1.242,0.046,1,0,0,0,p\n",
        b"2024-01-01 00:18,1.2,0.04,1,0,0,0,p\n",
    ])


@pytest.mark.parametrize("variant", tuple(numeric.VARIANTS))
def test_variants_are_self_contained_and_exact(variant):
    source = _source()
    frame = numeric.encode(source, variant)
    assert frame.startswith(numeric.MAGIC)
    assert numeric.decode(frame) == source


def test_column_and_row_packing_are_distinct():
    source = _source()
    assert numeric.encode(source, "numeric-delta-columns-v1") != numeric.encode(source, "numeric-delta-rows-v1")
    assert numeric.encode(source, "numeric-delta-columns-v1") != numeric.encode(source, "numeric-delta-columns-packed-meta-v1")


def test_inspection_reports_numeric_and_timing_eligibility():
    report = numeric.inspect(_source())
    assert report["records"] == 4
    assert report["timestamp_delta_min"] == report["timestamp_delta_max"] == 6
    assert report["water_precision_values"] == [1, 3]
    assert report["raw_precision_and_flag_bytes"] == 24
    assert report["fixed_width_metadata_recovery_bytes"] > 0


def test_rejects_unsupported_schema_and_corrupt_frame():
    with pytest.raises(ValueError):
        numeric.encode(b"not csv", "numeric-delta-columns-v1")
    frame = numeric.encode(_source(), "numeric-delta-columns-v1")
    with pytest.raises(ValueError):
        numeric.decode(b"BAD!" + frame[4:])


@pytest.mark.parametrize("before, after", [
    (b"1.327", b"+1.327"),
    (b"1.327", b"01.327"),
    (b"0.045", b"-0.000"),
    (b"\n", b"\r\n"),
])
def test_rejects_lexical_spellings_that_cannot_round_trip(before, after):
    source = _source().replace(before, after, 1)
    with pytest.raises(ValueError):
        numeric.encode(source, "numeric-delta-columns-v1")


def test_packed_metadata_frame_is_self_contained():
    source = _source()
    packed = numeric.encode(source, "numeric-delta-columns-packed-meta-v1")
    assert numeric.decode(packed) == source
