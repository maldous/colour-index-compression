import random

import pytest

from cix.ppm import (
    ESCAPE_METHODS, _encode_ppm_method, _encode_ppm_see,
    decode_ppm, encode_ppm,
)


@pytest.mark.parametrize("order", [0, 1, 3, 5])
@pytest.mark.parametrize("kind", ["random", "sparse", "periodic"])
def test_bounded_search_is_byte_identical_to_exhaustive(order, kind):
    rng = random.Random(490 + order)
    if kind == "random":
        data = bytes(rng.randrange(256) for _ in range(768))
    elif kind == "sparse":
        data = bytes(0 if rng.random() < .9 else rng.randrange(16) for _ in range(768))
    else:
        data = bytes(range(19)) * 41
    history = data[:350] * 2
    candidates = [
        _encode_ppm_method(data, max_order=order, prefix_history=history,
                           escape_method=method, update_exclusion=variant)
        for variant in (False, True) for method in ESCAPE_METHODS
    ] + [
        _encode_ppm_see(data, max_order=order, prefix_history=history,
                        update_exclusion=variant)
        for variant in (False, True)
    ]
    expected = min(candidates, key=len)
    actual = encode_ppm(data, max_order=order, prefix_history=history)
    assert actual == expected
    assert decode_ppm(actual, source_length=len(data), prefix_history=history) == data


def test_bound_can_stop_a_losing_candidate_without_returning_a_stream():
    data = bytes(range(256)) * 4
    assert _encode_ppm_method(data, max_order=0, prefix_history=b"",
                              escape_method=0, update_exclusion=False,
                              max_bytes=10) is None
    assert _encode_ppm_see(data, max_order=0, prefix_history=b"",
                           update_exclusion=False, max_bytes=10) is None
