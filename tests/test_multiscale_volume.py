import numpy as np
import pytest
from benchmarks import multiscale_volume as codec


@pytest.mark.parametrize('shape', [(3, 9, 7), (1, 3, 2), (2, 1, 1), (1, 1, 1)])
def test_modular_odd_dimension_lifting(shape):
    a = np.random.default_rng(72).integers(0, 65536, shape, dtype=np.uint16)
    for axis in range(3):
        if shape[axis] < 2: continue
        for predictor in (0, 1):
            low, high = codec.split_axis(a, axis, predictor)
            assert np.array_equal(codec.join_axis(low, high, axis, predictor), a)


@pytest.mark.parametrize('axes,levels,predictor', [(0,0,0),(1,3,0),(1,3,1),(7,2,1)])
def test_complete_frames_restore_arbitrary_pixels_and_metadata(axes, levels, predictor):
    a = np.random.default_rng(13).integers(0, 65536, (3,9,7), dtype=np.uint16)
    data = b'header' + a.astype('<u2').tobytes() + b'tail'
    region = dict(offset=6, length=a.nbytes, width=7, slice_height=9)
    frame, _ = codec.encode(data, region, axes, levels, predictor, effort=1)
    assert codec.decode(frame) == data
    with pytest.raises(ValueError): codec.decode(frame + b'X')
