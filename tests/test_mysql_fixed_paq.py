from pathlib import Path
import pytest
from benchmarks import mysql_fixed_paq as codec


def test_independent_frame_round_trip_and_checksum():
    source = Path('benchmark-work/silesia/osdb')
    if not source.exists(): pytest.skip('local database unavailable')
    # Includes a partial last record, which must be preserved literally.
    data = source.read_bytes()[:8193]
    for mode in (1, 3):
        frame, stats = codec.encode(data, mode, '-2')
        assert stats['physical_bytes'] == len(frame)
        assert codec.decode(frame) == data
        _, pos = codec.vdecode(frame, 5)
        damaged = bytearray(frame); damaged[pos] ^= 1
        with pytest.raises(ValueError, match='checksum'): codec.decode(bytes(damaged))
