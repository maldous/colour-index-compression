import random
import pytest
from benchmarks.mixer_bounded import BLOCK_SIZE, encode, decode


def test_mixed_multiblock_round_trip():
    data=random.Random(4207).randbytes(BLOCK_SIZE)+bytes(range(37))*32
    assert decode(encode(data))==data


@pytest.mark.parametrize('data',[b'',b'a',b'abracadabra'*50])
def test_rejects_truncation_trailing_and_corruption(data):
    frame=encode(data)
    assert decode(frame)==data
    damaged=(frame[:-1],frame+b'x',frame[:6]+bytes([frame[6]^1])+frame[7:])
    for bad in damaged:
        with pytest.raises((ValueError,IndexError)):
            decode(bad)
