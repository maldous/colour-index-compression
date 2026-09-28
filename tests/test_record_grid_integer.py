import random
import struct
import pytest
from benchmarks import record_grid_integer as codec


@pytest.mark.parametrize('policy',[1,2,3])
def test_integer_constraints_and_escapes(policy):
    rng=random.Random(72)
    cases=[[],[0]*400,[-(1<<31)+1,(1<<31)-1]*40,list(range(-200,200)),[rng.randrange(-100000,100000) for _ in range(4097)]]
    for values in cases:
        for block in (17,256):
            frame,_=codec.encode_integers(values,policy,block)
            assert codec.decode_integers(frame,len(values))==values


@pytest.mark.parametrize('policy',[1,2,3])
def test_complete_float_frame(policy):
    rng=random.Random(12);data=bytes(28)+rng.randbytes(28*70)+b'tail'
    frame,_=codec.encode(data,policy,32)
    assert codec.decode(frame)==data
