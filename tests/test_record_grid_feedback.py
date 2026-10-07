import random
import struct
import pytest
from benchmarks import record_grid_feedback as codec


@pytest.mark.parametrize('mode',[1,2,3])
def test_arbitrary_bits_and_causal_repeats(mode):
    rng=random.Random(41);data=bytes(28)
    for i in range(220):
        data+=struct.pack('<QQ4sII',rng.getrandbits(64),rng.choice([0,1,0x8000000000000000,0x7ff8000000000001]),b'A0\0\0',rng.choice([0,0x80000000,0x7f800000,0x35800000]),rng.getrandbits(32))
    data+=b'tail'
    for model in (0,1):
        raw,_=codec.transform(data,mode,model);assert codec.inverse(raw)==data
        frame,_=codec.encode(data,mode,model);assert codec.decode(frame)==data


def test_repeated_coordinate_constraints_reduce_errors():
    q=[1,2,1,2,1,2];residues=[3,-4,3,-4,3,-4]
    errors=codec.feedback(q,residues,4)
    assert errors==[3,-4,0,0,0,0]
    assert codec.feedback(q,errors,4,True)==residues
    assert codec.feedback([0,0],[0x7fffffff,-0x80000000],4)==[0x7fffffff,1]
