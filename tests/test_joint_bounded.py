import random
import pytest
from benchmarks.native_ppm import enable
from benchmarks.joint_bounded import encode,decode
from benchmarks.ppm_bounded import encode as incumbent


@pytest.mark.parametrize('data',[b'',b'abc'*200,random.Random(18).randbytes(1025),bytes(range(37))*60])
def test_round_trip_and_physical_nonregression(data):
    enable()
    frame=encode(data,block_size=512)
    assert decode(frame)==data
    assert len(frame)<=len(incumbent(data,block_size=512))
    for bad in (frame[:-1],frame+b'x'):
        with pytest.raises((ValueError,IndexError)):
            decode(bad)


def test_mixer_branch_is_selected_and_decoded():
    from cix.multinomial import vdecode
    rng=random.Random(438)
    data=bytes(rng.randrange(4) for _ in range(8192))
    enable()
    frame=encode(data)
    _,pos=vdecode(frame,5)
    _,pos=vdecode(frame,pos)
    _,pos=vdecode(frame,pos+4)
    assert frame[pos]==2
    assert decode(frame)==data
    assert len(frame)<len(incumbent(data))
