import struct

import numpy as np
import pytest

from benchmarks import domain_volume as volume


def nifti(values: np.ndarray, *, suffix: bytes = b"") -> bytes:
    assert values.dtype == np.dtype("<i2") and values.ndim == 4
    t, z, y, x = values.shape
    header = bytearray(416)
    struct.pack_into("<i", header, 0, 348)
    struct.pack_into("<8h", header, 40, 4, x, y, z, t, 1, 1, 1)
    struct.pack_into("<h", header, 70, 4)
    struct.pack_into("<h", header, 72, 16)
    struct.pack_into("<f", header, 108, 416.0)
    header[344:348] = b"n+1\0"
    return bytes(header) + values.tobytes() + suffix


def test_structural_frames_recover_every_original_byte():
    values = np.arange(2 * 3 * 4 * 5, dtype="<i2").reshape(2, 3, 4, 5) - 50
    source = nifti(values, suffix=b"exact trailing metadata\0")
    for variant in ("original", "plane-stack", "delta-z"):
        assert volume.decode(volume.encode(source, variant)) == source


def test_delta_z_handles_signed_wraparound():
    values = np.array([[[[-32768, 32767]], [[32767, -32768]], [[-1, 1]]]], dtype="<i2")
    source = nifti(values)
    assert volume.decode(volume.encode(source, "delta-z")) == source


def test_rejects_non_auditable_nifti_layouts_and_corrupt_frames():
    with pytest.raises(ValueError):
        volume.encode(b"not a nifti", "plane-stack")
    source = nifti(np.zeros((1, 2, 2, 2), dtype="<i2"))
    frame = volume.encode(source, "plane-stack")
    with pytest.raises(ValueError):
        volume.decode(frame[:-1])


def test_planar_jxl_round_trips_a_small_signed_volume():
    values = (np.arange(2 * 3 * 8 * 9, dtype="<i2").reshape(2, 3, 8, 9) - 100)
    source = nifti(values)
    assert volume.decode(volume.encode(source, "jxl-planar3-e10")) == source
