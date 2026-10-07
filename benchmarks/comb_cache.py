"""Optional bounded cache of exact small binomial coefficients."""
from functools import lru_cache
import math
import operator


def enable(capacity=8192, maximum_n=4096):
    original = math.comb
    cached = lru_cache(capacity)(original)

    def comb(n, k):
        n, k = operator.index(n), operator.index(k)
        if 0 <= n <= maximum_n:
            return cached(n, k)
        return original(n, k)

    math.comb = comb
    return cached
