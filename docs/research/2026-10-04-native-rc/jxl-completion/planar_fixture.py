#!/usr/bin/env python3
"""Scheduler-only oracle for historical imagecodecs planar JPEG XL layout.

Requires the frozen imagecodecs 2026.8.16 environment.  It creates no corpus
asset: two tiny generated volumes expose plane ordering and 8/16-bit transport.
The native bridge check, when added, must accept `--native` and demonstrate
both-direction semantic equality; this oracle deliberately does not choose a
host fallback codec.
"""
import argparse
import ctypes
import hashlib
import json
import os


class Buffer(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("size", ctypes.c_size_t)]


class PlanarImage(ctypes.Structure):
    _fields_ = [
        ("pixels", ctypes.POINTER(ctypes.c_uint8)), ("pixels_size", ctypes.c_size_t),
        ("depth", ctypes.c_uint32), ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32), ("bits_per_sample", ctypes.c_uint32),
        ("sample_type", ctypes.c_uint32), ("effort", ctypes.c_uint32),
    ]


class PlanarInfo(ctypes.Structure):
    _fields_ = [
        ("depth", ctypes.c_uint32), ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32), ("bits_per_sample", ctypes.c_uint32),
        ("sample_type", ctypes.c_uint32),
    ]


def native_bridge(path):
    if not os.path.isabs(path):
        raise ValueError("--bridge must be an absolute packaged bridge path")
    bridge = ctypes.CDLL(path)
    bridge.cix_jxl_encode_planar.argtypes = [ctypes.POINTER(PlanarImage), ctypes.c_size_t, ctypes.POINTER(Buffer)]
    bridge.cix_jxl_encode_planar.restype = ctypes.c_int
    bridge.cix_jxl_probe_planar.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_uint32, ctypes.c_size_t, ctypes.POINTER(PlanarInfo)]
    bridge.cix_jxl_probe_planar.restype = ctypes.c_int
    bridge.cix_jxl_decode_planar.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    bridge.cix_jxl_decode_planar.restype = ctypes.c_int
    bridge.cix_jxl_free_buffer.argtypes = [ctypes.POINTER(Buffer)]
    bridge.cix_jxl_library_version.restype = ctypes.c_uint32
    if bridge.cix_jxl_library_version() != 12000:
        raise AssertionError("bridge is not linked to libjxl 0.12.0")
    return bridge


def native_decode(bridge, payload, source):
    encoded = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload)
    info = PlanarInfo()
    expected_pixels = source.size
    if bridge.cix_jxl_probe_planar(encoded, len(payload), source.shape[0], expected_pixels, ctypes.byref(info)) != 0:
        raise AssertionError("native planar probe rejected frozen imagecodecs payload")
    if (info.depth, info.height, info.width) != source.shape:
        raise AssertionError("native planar probe shape mismatch")
    output = (ctypes.c_uint8 * source.nbytes)()
    if bridge.cix_jxl_decode_planar(encoded, len(payload), info.depth, info.width, info.height, info.bits_per_sample, info.sample_type, output, source.nbytes) != 0:
        raise AssertionError("native planar decode failed")
    if bytes(output) != source.tobytes(order="C"):
        raise AssertionError("native planar decode plane ordering mismatch")


def native_encode(bridge, source, effort, imagecodecs, numpy):
    raw = source.tobytes(order="C")
    input_buffer = (ctypes.c_uint8 * len(raw)).from_buffer_copy(raw)
    image = PlanarImage(input_buffer, len(raw), source.shape[0], source.shape[2], source.shape[1],
                        int(source.max()).bit_length(), 1 if source.dtype == numpy.uint8 else 2, effort)
    output = Buffer()
    status = bridge.cix_jxl_encode_planar(ctypes.byref(image), len(raw) + (64 << 20), ctypes.byref(output))
    if status != 0:
        raise AssertionError(f"native planar encode failed with status {status}")
    try:
        payload = ctypes.string_at(output.data, output.size)
    finally:
        bridge.cix_jxl_free_buffer(ctypes.byref(output))
    decoded = imagecodecs.jpegxl_decode(payload, numthreads=1, out=bytearray(source.nbytes))
    if decoded.shape != source.shape or decoded.dtype != source.dtype or not numpy.array_equal(decoded, source):
        raise AssertionError("imagecodecs decode of native planar payload mismatch")


def volume(dtype, depth, offset):
    import numpy
    # A distinct base per Z plane catches color/extra-channel reordering.
    values = numpy.arange(depth * 3 * 4, dtype=numpy.uint16) + offset
    return values.astype(dtype).reshape(depth, 3, 4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--bridge", help="absolute path to the staged CIX bridge; required with --native")
    args = parser.parse_args()
    import imagecodecs
    import numpy

    if args.native and not args.bridge:
        parser.error("--native requires --bridge")
    bridge = native_bridge(args.bridge) if args.native else None

    cases = []
    for dtype, offset in ((numpy.uint8, 0), (numpy.uint16, 257)):
        for depth in (2, 3, 5):
          for effort in (7, 9, 10):
            source = volume(dtype, depth, offset)
            payload = imagecodecs.jpegxl_encode(
                source, lossless=True, effort=effort,
                bitspersample=int(source.max()).bit_length(), numthreads=1,
                planar=True, photometric="GRAY",
            )
            decoded = imagecodecs.jpegxl_decode(payload, numthreads=1,
                                                 out=bytearray(source.nbytes))
            if decoded.shape != source.shape or decoded.dtype != source.dtype or not numpy.array_equal(decoded, source):
                raise AssertionError("historical planar JPEG XL round-trip mismatch")
            if bridge is not None:
                native_decode(bridge, payload, source)
                native_encode(bridge, source, effort, imagecodecs, numpy)
            cases.append({
            "dtype": str(dtype), "shape": list(source.shape), "effort": effort,
            "plane_order": "z=0 color; z=1.. channels 0..z-2 optional",
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "payload_bytes": len(payload),
        })
    with open(args.result, "w", encoding="utf-8") as stream:
        json.dump({"imagecodecs": imagecodecs.__version__, "native": bool(bridge), "cases": cases}, stream, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
