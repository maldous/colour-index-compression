import os
import random

from cix.multinomial import (
    ContextModel,
    StreamConfig,
    StreamEncoder,
    compress,
    decode_context_type_classes,
    decode_type_class,
    decompress,
    encode_context_type_classes,
    encode_type_class,
)


def test_type_class_round_trip():
    rng = random.Random(1234)
    for length in (0, 1, 2, 5, 10, 100, 1000):
        for alphabet in (1, 2, 5, 26, 256):
            data = bytes(rng.randrange(alphabet) for _ in range(length))
            encoded = encode_type_class(data)
            restored, pos = decode_type_class(encoded)
            assert restored == data
            assert pos == len(encoded)


def test_context_type_class_round_trip():
    rng = random.Random(99)
    data = bytes(rng.randrange(16) for _ in range(4000))
    prefix = b"prefix!!"
    for order, bits in ((1, 6), (1, 8), (2, 8), (2, 10), (4, 10)):
        encoded = encode_context_type_classes(
            data, order=order, bucket_bits=bits, prefix_history=prefix
        )
        restored, pos = decode_context_type_classes(
            encoded, 0, len(data), prefix_history=prefix
        )
        assert restored == data
        assert pos == len(encoded)


def test_stream_round_trip_is_feed_size_independent():
    data = (
        os.urandom(5000)
        + b"A" * 5000
        + (b"abc123," * 1000)
        + os.urandom(5000)
    )
    config = StreamConfig(
        min_block=512,
        max_block=4096,
        probe_stride=256,
        context_models=(
            ContextModel(1, 6),
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(3, 10),
            ContextModel(4, 10),
        ),
    )
    outputs = []
    for feed_size in (1, 17, 1024, len(data)):
        encoder = StreamEncoder(config)
        for start in range(0, len(data), feed_size):
            encoder.feed(data[start : start + feed_size])
        blob = encoder.finish()
        assert decompress(blob) == data
        outputs.append(blob)

    # Segmentation decisions are based on accumulated content, not caller packet sizes.
    assert len({blob for blob in outputs}) == 1


def test_random_data_falls_back_near_raw():
    data = os.urandom(12000)
    blob = compress(
        data,
        StreamConfig(
            min_block=1024,
            max_block=4096,
            probe_stride=512,
            context_models=(ContextModel(1, 6), ContextModel(2, 8)),
        ),
    )
    assert decompress(blob) == data
    assert len(blob) <= len(data) + 64


def test_crc_detects_corruption():
    data = b"multinomial cix " * 1000
    blob = bytearray(compress(data))
    blob[-1] ^= 1
    try:
        decompress(bytes(blob))
    except ValueError as exc:
        assert "checksum" in str(exc)
    else:
        raise AssertionError("corruption was not detected")
