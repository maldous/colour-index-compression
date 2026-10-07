from cix.multinomial import encode_type_class_known_n
from cix.substreams import (
    decode_bytes,
    decode_distances_best,
    decode_uints,
    encode_bytes,
    encode_distances_best,
    encode_uints,
)
from cix.multinomial import vdecode


def test_local_byte_substream_round_trip_nonstationary():
    data = (
        b"A" * 400
        + bytes(range(64)) * 10
        + b"B" * 400
        + (b"ABCD" * 300)
    )
    encoded = encode_bytes(data)
    assert decode_bytes(encoded, len(data)) == data

    # The selector includes the static type class, so local modelling can never
    # make this substream worse than that candidate by more than its mode byte.
    static = b"\x00" + encode_type_class_known_n(data)
    assert len(encoded) <= len(static)


def test_integer_logclass_local_round_trip():
    values = (
        [0] * 100
        + list(range(64))
        + [1, 2, 3, 4] * 100
        + [1000 + i for i in range(100)]
    )
    encoded = encode_uints(values)
    assert decode_uints(encoded, len(values)) == values


def test_distance_cache_and_local_classes_round_trip():
    distances = (
        [4, 4, 4, 8, 4, 8, 16, 4] * 100
        + [1024, 2048, 1024, 4096] * 50
    )
    encoded = encode_distances_best(distances)
    assert decode_distances_best(encoded, len(distances)) == distances


def test_integer_local_logclasses_store_low_bit_padding_only_once():
    values = [0] * 65 + [128, 129, 130] * 65 + [0] * 65 + [32768, 32769] * 65
    encoded = encode_uints(values)
    assert encoded[0] == 3  # local logclass mode
    class_size, pos = vdecode(encoded, 1)
    low_bits = sum((v + 1).bit_length() - 1 for v in values)
    assert low_bits % 8 != 0
    assert len(encoded) == pos + class_size + (low_bits + 7) // 8
    assert decode_uints(encoded, len(values)) == values
