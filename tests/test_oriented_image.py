import numpy as np
import pytest
pytest.importorskip('imagecodecs')
from benchmarks import oriented_image_codec as codec


@pytest.mark.parametrize('mode',range(8))
def test_rectangular_orientation(mode):
    pixels=np.random.default_rng(72).integers(0,65536,(16,20),dtype=np.uint16)
    data=b'prefix\0'+pixels.astype('<u2').tobytes()+b'\xffsuffix'
    region=dict(offset=7,length=pixels.nbytes,width=20,height=16,slice_height=16)
    blob=codec.encode(data,region,mode,effort=3)
    assert codec.decode(blob)==data
