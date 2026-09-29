import numpy as np
import pytest
from benchmarks import paq_image_planes as p


@pytest.mark.parametrize('shift',[0,4,6,8])
@pytest.mark.parametrize('shape',[(1,1),(7,5),(33,19)])
def test_sample_and_metadata_preserved(shift,shape):
    w,h=shape;rng=np.random.default_rng(w*100+h)
    samples=rng.integers(0,4096,w*h,dtype=np.uint16).astype('<u2').tobytes()
    data=b'prefix'+samples+b'suffix'
    assert p.inverse(p.transform(data,dict(offset=6,width=w,height=h),shift))==data


def test_split_does_not_truncate_high_bits():
    with pytest.raises(ValueError,match='exceeds'):
        p.transform(b'\xff\xff',dict(offset=0,width=1,height=1),4)


def test_low_plane_must_fit_transmitted_alphabet():
    raw=bytearray(p.transform(b'\0\0',dict(offset=0,width=1,height=1),4))
    raw[-1]=16
    with pytest.raises(ValueError,match='alphabet'):p.inverse(bytes(raw))
