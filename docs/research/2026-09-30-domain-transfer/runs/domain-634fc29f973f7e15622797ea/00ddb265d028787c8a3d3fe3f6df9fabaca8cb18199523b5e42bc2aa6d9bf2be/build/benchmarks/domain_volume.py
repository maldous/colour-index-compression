"""Reversible NIfTI-1 volume representations for domain-transfer experiments.

This adapter deliberately supports only a narrow, auditable input: little-endian
NIfTI-1, uncompressed, signed 16-bit voxels.  It retains every non-voxel byte
verbatim.  ``plane-stack`` is the fixed planar JXL layout that won the historic
``mr`` trial (portfolio region 0, transform mode 3, effort 10); ``delta-z`` is
one local neighbouring-slice predictor ablation.

For ``original`` the exact source bytes are returned so a matched PAQ control
does not acquire artificial CIX framing.  The two structural variants return
self-contained reversible frames intended to be passed to the same PAQ command.
The ``jxl-planar3-e10`` variant is already a complete compressed frame and must
not be passed through PAQ again.
"""
from __future__ import annotations

import struct
import zlib

import imagecodecs
import numpy as np

from cix.multinomial import vdecode, vencode

MAGIC = b"CIXDV2"
STRUCT_PLANE_STACK = 1
STRUCT_DELTA_Z = 2
JXL_PLANAR3_E10 = 129


def _read_varints(frame: bytes, count: int, position: int) -> tuple[list[int], int]:
    values: list[int] = []
    for _ in range(count):
        value, position = vdecode(frame, position)
        values.append(value)
    return values, position


def inspect_nifti1(data: bytes) -> dict[str, int]:
    """Return the constrained volume layout or reject a non-auditable input."""
    if len(data) < 352 or struct.unpack_from("<i", data, 0)[0] != 348:
        raise ValueError("expected a little-endian NIfTI-1 header")
    dimensions = struct.unpack_from("<8h", data, 40)
    ndim = dimensions[0]
    if ndim not in (3, 4):
        raise ValueError("only 3-D or 4-D NIfTI volumes are supported")
    x, y, z = dimensions[1:4]
    t = dimensions[4] if ndim == 4 else 1
    if min(x, y, z, t) <= 0:
        raise ValueError("invalid NIfTI dimensions")
    if struct.unpack_from("<h", data, 70)[0] != 4 or struct.unpack_from("<h", data, 72)[0] != 16:
        raise ValueError("only NIfTI signed-int16 data are supported")
    offset_float = struct.unpack_from("<f", data, 108)[0]
    offset = int(offset_float)
    if offset_float != offset or offset < 352:
        raise ValueError("invalid NIfTI voxel offset")
    voxel_bytes = x * y * z * t * 2
    if offset + voxel_bytes > len(data):
        raise ValueError("truncated NIfTI voxel data")
    return {"offset": offset, "voxel_bytes": voxel_bytes, "x": x, "y": y, "z": z, "t": t}


def _volume(data: bytes, info: dict[str, int]) -> np.ndarray:
    start, length = info["offset"], info["voxel_bytes"]
    return np.frombuffer(data[start:start + length], dtype="<i2").reshape(
        info["t"], info["z"], info["y"], info["x"]
    )


def _delta_z(volume: np.ndarray) -> bytes:
    values = volume.astype(np.int32)
    residual = np.empty_like(values)
    residual[:, :1] = values[:, :1]
    residual[:, 1:] = values[:, 1:] - values[:, :-1]
    # Modulo-2^16 representation keeps arbitrary signed int16 inputs reversible.
    return (residual & 0xFFFF).astype("<u2").tobytes()


def _undelta_z(payload: bytes, info: dict[str, int]) -> bytes:
    residual = np.frombuffer(payload, dtype="<u2").astype(np.int64).reshape(
        info["t"], info["z"], info["y"], info["x"]
    )
    signed = np.where(residual >= 32768, residual - 65536, residual)
    volume = np.cumsum(signed, axis=1) & 0xFFFF
    return volume.astype("<u2").tobytes()


def _header(kind: int, data: bytes, info: dict[str, int], payload_size: int) -> bytes:
    prefix = data[:info["offset"]]
    suffix = data[info["offset"] + info["voxel_bytes"]:]
    fields = (len(data), info["offset"], info["voxel_bytes"], info["x"], info["y"], info["z"], info["t"], len(prefix), len(suffix), payload_size)
    return MAGIC + bytes((kind,)) + b"".join(vencode(value) for value in fields) + zlib.crc32(data).to_bytes(4, "big") + prefix + suffix


def _parse_header(frame: bytes) -> tuple[int, dict[str, int], bytes, bytes, bytes]:
    if len(frame) < len(MAGIC) + 2 or frame[:len(MAGIC)] != MAGIC:
        raise ValueError("not a domain-volume frame")
    kind = frame[len(MAGIC)]
    fields, position = _read_varints(frame, 10, len(MAGIC) + 1)
    original, offset, voxel_bytes, x, y, z, t, prefix_size, suffix_size, payload_size = fields
    if min(voxel_bytes, x, y, z, t) <= 0 or voxel_bytes != x * y * z * t * 2:
        raise ValueError("invalid framed dimensions")
    if original != prefix_size + voxel_bytes + suffix_size or offset != prefix_size:
        raise ValueError("invalid framed byte boundaries")
    if position + 4 + prefix_size + suffix_size + payload_size != len(frame):
        raise ValueError("truncated or trailing domain-volume frame")
    crc = frame[position:position + 4]
    position += 4
    prefix = frame[position:position + prefix_size]
    position += prefix_size
    suffix = frame[position:position + suffix_size]
    position += suffix_size
    payload = frame[position:]
    return kind, {"offset": offset, "voxel_bytes": voxel_bytes, "x": x, "y": y, "z": z, "t": t, "original": original}, crc, prefix + suffix, payload


def _assemble(info: dict[str, int], crc: bytes, outside: bytes, raw: bytes) -> bytes:
    if len(raw) != info["voxel_bytes"] or len(outside) != info["original"] - info["voxel_bytes"]:
        raise ValueError("invalid decoded volume lengths")
    result = outside[:info["offset"]] + raw + outside[info["offset"]:]
    if len(result) != info["original"] or zlib.crc32(result).to_bytes(4, "big") != crc:
        raise ValueError("domain-volume checksum mismatch")
    return result


def encode(data: bytes, variant: str) -> bytes:
    """Return a self-contained representation; see module docstring for variants."""
    if variant == "original":
        return data
    info = inspect_nifti1(data)
    volume = _volume(data, info)
    raw = data[info["offset"]:info["offset"] + info["voxel_bytes"]]
    if variant == "plane-stack":
        payload, kind = raw, STRUCT_PLANE_STACK
    elif variant == "delta-z":
        payload, kind = _delta_z(volume), STRUCT_DELTA_Z
    elif variant == "jxl-planar3-e10":
        # The historic winner used the unmodified planes as a planar JXL image.
        # JXL accepts unsigned samples.  Viewing rather than numerically casting
        # retains the exact signed-int16 bit pattern required by NIfTI.
        planes = volume.reshape(info["t"] * info["z"], info["y"], info["x"]).view("<u2")
        bits = 16
        payload = imagecodecs.jpegxl_encode(planes, lossless=True, effort=10, bitspersample=bits,
                                             numthreads=1, planar=True, photometric="GRAY")
        kind = JXL_PLANAR3_E10
    else:
        raise ValueError("unknown domain-volume variant")
    return _header(kind, data, info, len(payload)) + payload


def decode(frame: bytes) -> bytes:
    """Reverse any representation emitted by :func:`encode`, including original."""
    if not frame.startswith(MAGIC):
        return frame
    kind, info, crc, outside, payload = _parse_header(frame)
    if kind == STRUCT_PLANE_STACK:
        raw = payload
    elif kind == STRUCT_DELTA_Z:
        raw = _undelta_z(payload, info)
    elif kind == JXL_PLANAR3_E10:
        planes = imagecodecs.jpegxl_decode(payload, numthreads=1)
        if planes.size != info["voxel_bytes"] // 2:
            raise ValueError("unexpected JXL plane count")
        raw = planes.astype("<u2").tobytes()
    else:
        raise ValueError("unknown domain-volume frame kind")
    return _assemble(info, crc, outside, raw)
