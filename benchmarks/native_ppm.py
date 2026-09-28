"""Explicit opt-in experimental native PPM accelerator; Python decoder unchanged."""
import ctypes
from pathlib import Path


def load(path=None):
    lib = ctypes.CDLL(str(Path(path or 'results/leaderboard/native_ppm.so').resolve()))
    lib.cix_ppm_encode.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p,
        ctypes.c_size_t, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_size_t)]
    lib.cix_ppm_encode.restype = ctypes.c_int
    lib.cix_ppm_free.argtypes = [ctypes.c_void_p]
    lib.cix_ppm_free.restype = None

    def variant(data, *, max_order, prefix_history=b'', escape_method=0,
                update_exclusion=False, secondary_escape=False, max_bytes=None):
        if not 0 <= max_order <= 8 or escape_method not in range(4):
            raise ValueError('invalid PPM parameters')
        result, size = ctypes.c_void_p(), ctypes.c_size_t()
        status = lib.cix_ppm_encode(data, len(data), prefix_history, len(prefix_history),
            max_order, escape_method, bool(update_exclusion), bool(secondary_escape),
            max_bytes or 0, ctypes.byref(result), ctypes.byref(size))
        if status == 1:
            return None
        if status != 0:
            raise RuntimeError('native PPM encoder failed')
        try:
            return ctypes.string_at(result, size.value)
        finally:
            lib.cix_ppm_free(result)

    def encode(data, *, max_order=4, prefix_history=b'', escape_method=None,
               update_exclusion=None, secondary_escape=None):
        if not 0 <= max_order <= 8:
            raise ValueError('PPM order outside supported range')
        if escape_method is not None and escape_method not in range(4):
            raise ValueError('invalid PPM escape method')
        updates = (False, True) if update_exclusion is None else (update_exclusion,)
        methods = range(4) if escape_method is None else (escape_method,)
        best = None
        options = []
        if secondary_escape is not True:
            options.extend((u, m, False) for u in updates for m in methods)
        if secondary_escape is not False:
            options.extend((u, 0, True) for u in updates)
        for u, m, secondary in options:
            candidate = variant(data, max_order=max_order, prefix_history=prefix_history,
                escape_method=m, update_exclusion=u, secondary_escape=secondary,
                max_bytes=len(best) if best is not None else None)
            if candidate is not None and (best is None or len(candidate) < len(best)):
                best = candidate
        if best is None:
            raise ValueError('no PPM variants requested')
        return best
    return variant, encode


def enable(path=None):
    from cix import ppm
    _, encode = load(path)
    ppm.encode_ppm = encode
