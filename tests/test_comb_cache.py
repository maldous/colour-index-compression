import math
import pytest
from benchmarks.comb_cache import enable


def test_exact_comb_cache_preserves_values_and_argument_validation(monkeypatch):
    original = math.comb
    monkeypatch.setattr(math, 'comb', original)
    cache = enable(capacity=8, maximum_n=128)
    for n in range(150):
        for k in range(n + 2):
            assert math.comb(n, k) == original(n, k)
    math.comb(4, 2)
    for n, k in ((4.0, 2), (4, 2.0), ('4', 2)):
        with pytest.raises(TypeError):
            math.comb(n, k)
    for n, k in ((-1, 0), (4, -1)):
        with pytest.raises(ValueError):
            math.comb(n, k)
    assert cache.cache_info().currsize <= 8
