from cix.periodic import (
    decode_periodic_block,
    encode_periodic_block,
    profile_periods,
)
from cix.record import BASE_WIDTHS, discover_record_widths


def test_discovered_period_is_not_a_magic_prior():
    # 37 is deliberately absent from the universal prior. Repeated shingles recur
    # every 37 bytes (or a multiple whose divisor reveals 37), so discovery must
    # recover it from the data itself.
    assert 37 not in BASE_WIDTHS
    row = bytearray(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!")
    assert len(row) == 37
    data = bytearray()
    for i in range(300):
        r = row.copy()
        r[-1] = i & 0xFF
        data += r
    assert 37 in discover_record_widths(bytes(data))


def test_periodic_residual_round_trip_and_compresses():
    row = bytearray(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!")
    data = bytearray()
    for i in range(300):
        r = row.copy()
        r[-1] = i & 0xFF
        data += r
    payload, description = encode_periodic_block(bytes(data), beam=6)
    restored = decode_periodic_block(payload, source_length=len(data))
    assert restored == bytes(data)
    assert len(payload) < len(data) // 4
    assert description.startswith("period-")


def test_record_priors_have_no_benchmark_specific_scanline_constants():
    assert 216 not in BASE_WIDTHS
    assert 432 not in BASE_WIDTHS
