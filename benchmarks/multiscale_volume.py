"""CIXI2: exact multiscale interpolation residuals with independent JXL bands.

The decoder receives dimensions, axis choices, scale depth and every residual.
No image identity, sample values or external model are built into the format.
"""
import lzma
import zlib
import numpy as np
import imagecodecs
from cix.multinomial import vencode, vdecode

MAGIC = b'CIXI\x02'


def split_axis(array, axis, predictor):
    a = np.moveaxis(array, axis, 0).astype(np.int64)
    low = a[::2].copy()
    count = len(a) // 2
    pred = low[:count]
    if predictor:
        right = low[np.minimum(np.arange(count) + 1, len(low) - 1)]
        pred = (pred + right) // 2
    difference = ((a[1::2] - pred + 32768) & 65535) - 32768
    high = ((difference << 1) ^ (difference >> 15)).astype(np.uint16)
    return (np.moveaxis(low.astype(np.uint16), 0, axis).copy(),
            np.moveaxis(high, 0, axis).copy())


def join_axis(low, high, axis, predictor):
    a = np.moveaxis(low, axis, 0).astype(np.int64)
    h = np.moveaxis(high, axis, 0).astype(np.int64)
    pred = a[:len(h)]
    if predictor:
        right = a[np.minimum(np.arange(len(h)) + 1, len(a) - 1)]
        pred = (pred + right) // 2
    difference = (h >> 1) ^ -(h & 1)
    out = np.empty((len(a) + len(h), *a.shape[1:]), dtype=np.uint16)
    out[::2] = a
    out[1::2] = (pred + difference) & 65535
    return np.moveaxis(out, 0, axis).copy()


def encode(data, region, axes=1, levels=3, predictor=1, effort=9):
    if not 0 <= axes < 8 or not 0 <= levels <= 8 or predictor not in (0, 1):
        raise ValueError('unsupported multiscale parameters')
    offset = region['offset']; h = region['slice_height']; w = region['width']
    length = region['length']; z, remainder = divmod(length, 2 * h * w)
    if remainder or min(h, w, z) <= 0 or offset < 0 or offset + length > len(data):
        raise ValueError('invalid volume region')
    array = np.frombuffer(data[offset:offset + length], dtype='<u2').reshape(z, h, w)
    plan = [axis for _ in range(levels) for axis in range(3) if axes & (1 << axis)]
    bands = []

    def leaf(a):
        bits = max(1, int(a.max()).bit_length())
        a = a.astype(np.uint8 if bits <= 8 else np.uint16)
        planar = a.shape[0] > 1
        if not planar:
            a = a[0]
        payload = imagecodecs.jpegxl_encode(a, lossless=True, effort=effort,
            bitspersample=bits, numthreads=1, planar=planar, photometric='GRAY')
        bands.append(payload)
        return vencode(len(payload)) + payload

    def visit(a, step):
        while step < len(plan) and a.shape[plan[step]] < 2:
            step += 1
        if step == len(plan):
            return leaf(a)
        low, high = split_axis(a, plan[step], predictor)
        return visit(low, step + 1) + leaf(high)

    payload = visit(array, 0)
    metadata = lzma.compress(data[:offset] + data[offset + length:], preset=9)
    fields = (len(data), offset, z, h, w, len(metadata))
    frame = (MAGIC + bytes([axes, levels, predictor]) + b''.join(vencode(n) for n in fields)
             + zlib.crc32(data).to_bytes(4, 'big') + metadata + payload)
    return frame, dict(axes=axes, levels=levels, predictor=predictor, effort=effort,
                      band_bytes=list(map(len, bands)), physical_bytes=len(frame))


def decode(frame):
    if frame[:5] != MAGIC or len(frame) < 8:
        raise ValueError('invalid multiscale frame')
    axes, levels, predictor = frame[5:8]
    if axes > 7 or levels > 8 or predictor > 1:
        raise ValueError('unsupported multiscale parameters')
    pos = 8; fields = []
    for _ in range(6):
        n, pos = vdecode(frame, pos); fields.append(n)
    original, offset, z, h, w, metadata_size = fields
    length = 2 * z * h * w
    if not length or offset + length > original or pos + 4 + metadata_size > len(frame):
        raise ValueError('invalid multiscale dimensions')
    crc = int.from_bytes(frame[pos:pos + 4], 'big'); pos += 4
    metadata = lzma.decompress(frame[pos:pos + metadata_size]); pos += metadata_size
    if len(metadata) != original - length:
        raise ValueError('invalid multiscale metadata')
    plan = [axis for _ in range(levels) for axis in range(3) if axes & (1 << axis)]

    def leaf(shape):
        nonlocal pos
        size, pos = vdecode(frame, pos)
        if pos + size > len(frame):
            raise ValueError('truncated multiscale band')
        a = imagecodecs.jpegxl_decode(frame[pos:pos + size], numthreads=1); pos += size
        if a.dtype not in (np.dtype('uint8'), np.dtype('uint16')) or a.size != np.prod(shape):
            raise ValueError('invalid multiscale band')
        return a.reshape(shape).astype(np.uint16)

    def visit(shape, step):
        while step < len(plan) and shape[plan[step]] < 2:
            step += 1
        if step == len(plan):
            return leaf(shape)
        axis = plan[step]; lo = list(shape); hi = list(shape)
        lo[axis] = (shape[axis] + 1) // 2; hi[axis] = shape[axis] // 2
        return join_axis(visit(tuple(lo), step + 1), leaf(tuple(hi)), axis, predictor)

    pixels = visit((z, h, w), 0)
    if pos != len(frame):
        raise ValueError('trailing multiscale bytes')
    data = metadata[:offset] + pixels.astype('<u2').tobytes() + metadata[offset:]
    if len(data) != original or zlib.crc32(data) != crc:
        raise ValueError('multiscale restoration checksum mismatch')
    return data
