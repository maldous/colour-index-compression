"""Optional exact arithmetic acceleration for local measurements.

GMP's binomial coefficient is converted back to an ordinary Python int. This
does not change histogram/rank values, candidate sets, framing or byte policy.
"""
import math
import operator
from functools import lru_cache

_caches = {}


def enable(memoize=False):
    import gmpy2

    def comb(n, k):
        n, k = operator.index(n), operator.index(k)
        if n < 0 or k < 0:
            raise ValueError('binomial arguments must be non-negative')
        if k > n:
            return 0
        return int(gmpy2.comb(n, k))

    math.comb = comb
    if memoize:
        # Only immutable results of pure functions are reused. These caches are
        # bounded and key solely on the actual generic codec inputs.
        from cix import multinomial
        multinomial.encode_type_class_known_n = lru_cache(128)(multinomial.encode_type_class_known_n)
        _caches['type_class'] = multinomial.encode_type_class_known_n
        from cix import substreams
        substreams.encode_type_class_known_n = multinomial.encode_type_class_known_n
        substreams.encode_bytes = lru_cache(256)(substreams.encode_bytes)
        _caches['byte_substreams'] = substreams.encode_bytes
        from cix import ppm
        ppm.encode_ppm = lru_cache(16)(ppm.encode_ppm)
        ppm.estimate_ppm_bits = lru_cache(32)(ppm.estimate_ppm_bits)
        _caches['ppm'] = ppm.encode_ppm
        _caches['ppm_estimate'] = ppm.estimate_ppm_bits
    return dict(gmpy2=gmpy2.version(), acceleration='exact math.comb -> int(gmpy2.comb)',
                memoize=memoize)


def cache_stats():
    return {name: fn.cache_info()._asdict() for name, fn in _caches.items()}
