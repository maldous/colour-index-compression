"""Independent framing and reversible-layout checks for competitive image modes."""
import numpy as np
import pytest

pytest.importorskip('imagecodecs')
from benchmarks import spatial_image_codec as spatial
from benchmarks import volume_image_codec as volume


def sample(depth=16, shape=(3, 16, 20)):
    pixels = np.random.default_rng(720).integers(0, 1 << depth, shape, dtype=np.uint16)
    prefix, suffix = b'\x00head\xff', b'tail\x00\xff'
    data = prefix + pixels.astype('<u2').tobytes() + suffix
    z, h, w = shape
    region = dict(offset=len(prefix), length=pixels.nbytes, width=w,
                  height=z*h, slice_height=h)
    return data, region


@pytest.mark.parametrize('depth', [1, 8, 10, 16])
@pytest.mark.parametrize('mode', range(6))
def test_volume_full_range_layouts(depth, mode):
    data, region = sample(depth)
    blob = volume.encode(data, region, mode, effort=3)
    assert volume.decode(blob) == data


@pytest.mark.parametrize('depth', [1, 8, 10, 16])
@pytest.mark.parametrize('backend', ['jxl', 'jls', 'j2k'])
def test_image_full_range(depth, backend):
    data, region = sample(depth)
    assert spatial.decode(spatial.encode_region(data, region, backend, effort=3)) == data


@pytest.mark.parametrize('codec', [spatial, volume])
def test_framing_rejects_corruption(codec):
    data, region = sample(10)
    blob = (codec.encode_region(data, region, 'jxl', 3) if codec is spatial
            else codec.encode(data, region, 3, 3))
    for invalid in (blob[:4], blob[:8], blob[:-1], blob + b'\x00', b'wrong' + blob[5:]):
        with pytest.raises(ValueError):
            codec.decode(invalid)
    changed = bytearray(blob)
    # The first four metadata bytes after the varints are the source CRC.
    from cix.multinomial import vdecode
    pos = 6
    for _ in range(5 if codec is spatial else 8):
        _, pos = vdecode(blob, pos)
    changed[pos] ^= 1
    with pytest.raises(ValueError, match='checksum'):
        codec.decode(bytes(changed))


def test_unsigned_wraparound():
    data = np.array([0, 65535, 32768, 32767, 1, 65534, 100, 50], dtype=np.uint16).reshape(2, 2, 2)
    for mode in range(6):
        assert np.array_equal(volume.inverse(volume.transform(data, mode), data.shape, mode), data)


def test_raster_axes_come_from_bytes():
    header = bytearray(240)
    header[4:10] = b'\x00\x14\x00\x10\x00\x10'
    regions = spatial.regions(bytes(header) + bytes(20 * 16 * 2))
    assert {(r['width'], r['height']) for r in regions} == {(20, 16), (16, 20)}
    assert spatial.regions(bytes(header) + bytes(20 * 16 * 2 - 1)) == []


@pytest.mark.parametrize('codec', [spatial, volume])
def test_invalid_regions(codec):
    data, region = sample()
    encoder = codec.encode_region if codec is spatial else codec.encode
    for change in ({'offset': -1}, {'length': 0}, {'width': 0}, {'length': len(data) + 2}):
        with pytest.raises(ValueError):
            encoder(data, {**region, **change})
