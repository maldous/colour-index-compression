"""Real pinned JXL bridge/reference cross-decode on generated tiny fixtures."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys

import imagecodecs
import numpy as np


class Image(C.Structure):
    _fields_ = [("pixels", C.c_void_p), ("pixels_size", C.c_size_t),
                ("width", C.c_uint32), ("height", C.c_uint32),
                ("bits", C.c_uint32), ("kind", C.c_uint32), ("effort", C.c_uint32)]


class Buffer(C.Structure):
    _fields_ = [("data", C.c_void_p), ("size", C.c_size_t)]


class Info(C.Structure):
    _fields_ = [("width", C.c_uint32), ("height", C.c_uint32),
                ("bits", C.c_uint32), ("kind", C.c_uint32)]


library_path = Path(sys.argv[1]).resolve(strict=True)
destination = Path(sys.argv[2])
destination.mkdir(parents=True, exist_ok=False)
lib = C.CDLL(str(library_path))
lib.cix_jxl_library_version.restype = C.c_uint32
assert lib.cix_jxl_library_version() == 12000
lib.cix_jxl_encode_gray_2d.argtypes = [C.POINTER(Image), C.c_size_t, C.POINTER(Buffer)]
lib.cix_jxl_free_buffer.argtypes = [C.POINTER(Buffer)]
lib.cix_jxl_probe_gray_2d.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(Info)]
lib.cix_jxl_decode_gray_2d.argtypes = [C.c_void_p, C.c_size_t, C.c_uint32, C.c_uint32,
                                     C.c_uint32, C.c_uint32, C.c_void_p, C.c_size_t]
rows = []
for bits, dtype, kind in ((8, np.uint8, 1), (16, np.dtype("<u2"), 2)):
    source = ((np.arange(17 * 19, dtype=np.uint32) * 7919) & ((1 << bits) - 1)).astype(dtype).reshape(19, 17)
    raw = source.tobytes()
    for effort in (7, 9, 10):
        descriptor = Image(source.ctypes.data, len(raw), 17, 19, bits, kind, effort)
        result = Buffer()
        assert lib.cix_jxl_encode_gray_2d(C.byref(descriptor), 1 << 20, C.byref(result)) == 0
        try:
            encoded = C.string_at(result.data, result.size)
        finally:
            lib.cix_jxl_free_buffer(C.byref(result))
        assert not result.data and result.size == 0
        assert imagecodecs.jpegxl_decode(encoded).tobytes() == raw
        reference = imagecodecs.jpegxl_encode(source, lossless=True, effort=effort, numthreads=1)
        for owner, payload in (("native", encoded), ("reference", reference)):
            data = C.create_string_buffer(payload)
            info = Info()
            assert lib.cix_jxl_probe_gray_2d(data, len(payload), 17 * 19, C.byref(info)) == 0
            assert (info.width, info.height, info.bits, info.kind) == (17, 19, bits, kind)
            assert lib.cix_jxl_probe_gray_2d(data, len(payload), 17 * 19 - 1, C.byref(info)) != 0
            restored = C.create_string_buffer(len(raw))
            assert lib.cix_jxl_decode_gray_2d(data, len(payload), 17, 19, bits, kind, restored, len(raw)) == 0
            assert restored.raw == raw
            assert lib.cix_jxl_decode_gray_2d(data, len(payload), 19, 17, bits, kind, restored, len(raw)) != 0
            (destination / f"gray-{bits}-effort-{effort}-{owner}.jxl").write_bytes(payload)
        rows.append({"bits": bits, "effort": effort, "source_bytes": len(raw),
                     "source_sha256": hashlib.sha256(raw).hexdigest(),
                     "native_bytes": len(encoded), "reference_bytes": len(reference),
                     "same_encoded_bytes": encoded == reference, "cross_decode_exact": True,
                     "wrong_geometry_rejected": True, "wrong_paid_pixels_rejected": True})
        result = Buffer()
        assert lib.cix_jxl_encode_gray_2d(C.byref(descriptor), 1, C.byref(result)) != 0
        assert not result.data and result.size == 0
invalid = C.create_string_buffer(b"not a JPEG XL stream")
info = Info()
assert lib.cix_jxl_probe_gray_2d(invalid, len(invalid.raw), 1, C.byref(info)) != 0
report = {"schema": "cix.jxl.real-boundary.v1", "library": str(library_path),
          "library_sha256": hashlib.sha256(library_path.read_bytes()).hexdigest(),
          "reference_imagecodecs": imagecodecs.__version__, "rows": rows,
          "scope": "generated 2D gray fixtures; no corpus result or full volume parity claim"}
(destination / "result.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report), flush=True)
