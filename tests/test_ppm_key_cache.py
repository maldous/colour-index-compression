import random

from benchmarks.ppm_key_cache import enable
from cix import ppm


def test_key_cache_matches_growth_rescale_exclusion_and_eviction(monkeypatch):
    original = ppm._eligible
    monkeypatch.setattr(ppm, '_eligible', original)
    cache = enable(capacity=4, minimum_symbols=2)
    rng = random.Random(382)
    contexts = [{} for _ in range(10)]
    for _ in range(1000):
        counts = rng.choice(contexts)
        key = rng.randrange(256)
        counts[key] = counts.get(key, 0) + 1
        if rng.randrange(10) == 0:
            for symbol in counts:
                counts[symbol] = max(1, counts[symbol] // 2)
        excluded = set(rng.sample(range(256), rng.randrange(257)))
        assert ppm._eligible(counts, excluded) == original(counts, excluded)
        assert len(cache) <= 4
