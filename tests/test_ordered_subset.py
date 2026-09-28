from itertools import combinations
from math import comb
import random
import pytest
from benchmarks import ordered_subset as codec


def test_every_small_subset_is_a_bijection_and_both_controls_restore():
    for universe in range(9):
        for n in range(universe + 1):
            ranks = []
            for values in combinations(range(universe), n):
                for method in (0, 1):
                    blob = codec.encode(values, universe, method)
                    restored, pos = codec.decode(blob, 0, universe, n, method)
                    assert restored == list(values) and pos == len(blob)
                    if method == 0:
                        ranks.append(int.from_bytes(blob, 'big'))
            assert sorted(ranks) == list(range(comb(universe, n)))


def test_sparse_large_universe_avoids_linear_scan():
    values = sorted(random.Random(324).sample(range(1 << 30), 64))
    for method in (0, 1):
        blob = codec.encode(values, 1 << 30, method)
        assert codec.decode(blob, 0, 1 << 30, 64, method) == (values, len(blob))


def test_invalid_subsets_and_out_of_class_rank():
    with pytest.raises(ValueError): codec.encode([1, 1], 5)
    with pytest.raises(ValueError): codec.encode([3, 1], 5)
    with pytest.raises(ValueError): codec.decode(b'\xff', 0, 4, 2)
