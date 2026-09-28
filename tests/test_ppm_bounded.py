import random
import pytest
from benchmarks.ppm_bounded import encode, decode


def test_bounded_ppm_crosses_blocks_and_preserves_bytes():
    rng = random.Random(927)
    for data in (b'', b'x', bytes(range(256)) * 3, rng.randbytes(701), b'abc' * 257):
        frame = encode(data, block_size=256)
        assert decode(frame) == data
        for bad in (frame[:-1], frame + b'\x00'):
            with pytest.raises(ValueError):
                decode(bad)


def test_bounded_ppm_rejects_checksum_change():
    from cix.multinomial import vdecode
    frame = bytearray(encode(b'abc' * 200, block_size=128))
    _, pos = vdecode(frame, 5)
    _, pos = vdecode(frame, pos)
    frame[pos] ^= 1
    with pytest.raises(ValueError, match='checksum'):
        decode(bytes(frame))


def test_bounded_ppm_rejects_invalid_block_bound():
    for size in (0, -1, 1048577):
        with pytest.raises(ValueError):
            encode(b'x', block_size=size)
