import random
import struct
import pytest
from benchmarks import record_float_grid as codec


@pytest.mark.parametrize('mode',range(4))
def test_all_float_bits_and_partial_record_preserved(mode):
    rng=random.Random(19);data=rng.randbytes(28)
    special=(0,1,0x8000000000000000,0x7ff0000000000000,0xfff0000000000000,0x7ff8000000000001)
    for i in range(120):
        data+=struct.pack('<QQ',special[i%len(special)],rng.getrandbits(64))+rng.randbytes(12)
    data+=b'partial'
    frame,_=codec.transform(data,mode)
    assert codec.inverse(frame)==data


@pytest.mark.parametrize('backend',range(3))
def test_complete_frames_with_small_grid_residuals(backend):
    data=bytes(28)
    for i in range(80):
        data+=struct.pack('<dd2shff',i*float.fromhex(codec.FIELDS[0][2]),-i*float.fromhex(codec.FIELDS[1][2]),b'A0',i,-0.0,float(i)*1e-8)
    for mode in (1,2,3):
        frame,_=codec.encode(data,mode,backend)
        assert codec.decode(frame)==data
        damaged=bytearray(frame);damaged[8]^=1
        with pytest.raises(Exception):codec.decode(bytes(damaged))
