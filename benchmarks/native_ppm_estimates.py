"""Opt-in estimator acceleration; qualify bit-exact floats before use."""
import ctypes
import math
from pathlib import Path


def load(path='results/leaderboard/native_ppm_estimates.so'):
    lib = ctypes.CDLL(str(Path(path).resolve()))
    fn = lib.cix_ppm_estimate
    fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t,
                  ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
    fn.restype = ctypes.c_int
    # Preserve the calling interpreter's exact log2 values, including PyPy.
    logs = (ctypes.c_double * 16641)(0.0, *(math.log2(i) for i in range(1, 16641)))

    def variant(data, *, max_order, prefix_history=b'', sample_limit=4096,
                escape_method=1, update_exclusion=False, portfolio=False):
        if not 0 <= max_order <= 8 or escape_method not in range(4):
            raise ValueError('invalid PPM parameters')
        sample_size = len(data[:sample_limit])
        result = ctypes.c_double()
        code = fn(data, len(data), prefix_history, len(prefix_history), max_order,
                  escape_method, bool(update_exclusion), bool(portfolio),
                  sample_size, logs, ctypes.byref(result))
        if code:
            raise RuntimeError('native estimator failed')
        return result.value

    def portfolio(data, *, max_order, prefix_history=b'', sample_limit=4096):
        if not 0 <= max_order <= 8:
            raise ValueError('PPM order outside supported range')
        if sample_limit <= 0:
            raise ValueError('sample_limit must be positive')
        return min(variant(data, max_order=max_order, prefix_history=prefix_history,
                           sample_limit=sample_limit, update_exclusion=u, portfolio=True)
                   for u in (False, True))
    return variant, portfolio


def enable(path='results/leaderboard/native_ppm_estimates.so'):
    from cix import ppm
    variant, portfolio = load(path)
    ppm.estimate_ppm_bits = variant
    ppm.estimate_ppm_portfolio_bits = portfolio
