from runtime.cix_runtime.legacy import multinomial


def test_type_class_helper_closure_round_trips_rank_and_range_inputs():
    for data in (b"", b"aaaa", b"abcabc", bytes(range(256)) * 10):
        frame = multinomial.encode_type_class(data)
        restored, position = multinomial.decode_type_class(frame)
        assert restored == data
        assert position == len(frame)


def test_shared_arithmetic_and_combinatorial_exports_remain_available():
    assert multinomial.combination_unrank_colex(multinomial.combination_rank_colex([1, 3, 7]), 3, 8) == [1, 3, 7]
    tree = multinomial.Fenwick([2, 0, 3])
    assert tree.select(2) == 2
