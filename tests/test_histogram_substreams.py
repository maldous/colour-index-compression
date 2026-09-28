import random

import pytest

from cix.histogram import decode_type_class, type_class_candidate
from cix.multinomial import (
    StreamConfig, StreamDecoder, compress, decompress, encode_type_class_known_n,
)
from cix.substreams import BYTE_STREAM_HISTOGRAM, decode_bytes, encode_bytes


@pytest.mark.parametrize("alphabet", [16, 37, 64, 128, 256])
def test_complete_histogram_candidate_and_nested_substream(alphabet):
    rng = random.Random(728 + alphabet)
    values = list(range(alphabet)) * (8192 // alphabet)
    rng.shuffle(values)
    data = bytes(values)
    incumbent = encode_type_class_known_n(data)
    candidate = type_class_candidate(data, incumbent)
    if candidate is not None:
        assert len(candidate) < len(incumbent)
        assert decode_type_class(candidate, len(data)) == data
        with pytest.raises(ValueError):
            decode_type_class(candidate + b"\x00", len(data))
        with pytest.raises(ValueError):
            decode_type_class(candidate[:3], len(data))
    encoded = encode_bytes(data)
    assert len(encoded) <= len(incumbent) + 1
    assert decode_bytes(encoded, len(data)) == data
    if alphabet >= 64:
        assert encoded[0] == BYTE_STREAM_HISTOGRAM


def test_tiny_substreams_cannot_recurse_into_count_vector_search(monkeypatch):
    import cix.histogram as histogram

    def forbidden(_):
        raise AssertionError("small type classes must not search histograms")

    monkeypatch.setattr(histogram, "encode_best", forbidden)
    for n in (0, 1, 127, 255, 256, 511):
        data = bytes(i % 256 for i in range(n))
        assert type_class_candidate(data, encode_type_class_known_n(data)) is None


def test_randomized_histogram_candidates_are_reversible():
    rng = random.Random(929)
    for _ in range(25):
        alphabet = rng.sample(range(256), rng.randint(2, 256))
        data = bytes(rng.choice(alphabet) for _ in range(rng.randint(512, 2048)))
        incumbent = encode_type_class_known_n(data)
        candidate = type_class_candidate(data, incumbent)
        if candidate is not None:
            assert len(candidate) < len(incumbent)
            assert decode_type_class(candidate, len(data)) == data


def test_stream_version_and_legacy_decoder_single_byte_packets():
    data = b"local-stream-compatibility" * 30
    config = StreamConfig(min_block=1024, max_block=1024, probe_stride=1024)
    blob = compress(data, config)
    assert blob.startswith(b"CIXM6")
    assert decompress(blob) == data
    # This small block cannot use histogram mode; its payload is legacy compatible.
    legacy = b"CIXM5" + blob[5:]
    decoder = StreamDecoder()
    restored = b"".join(decoder.feed(bytes((b,))) for b in legacy)
    decoder.finish()
    assert restored == data


def test_count_vector_top_level_frame_and_packet_boundaries():
    from cix.cli import config_for_level
    from cix.multinomial import StreamEncoder

    values = list(range(128)) * 64
    random.Random(284).shuffle(values)
    data = bytes(values)
    config = config_for_level(3)
    config.min_block = config.max_block = config.probe_stride = len(data)
    config.chunk_mode = 'fixed'
    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    assert 'count-vector-multinomial' in encoder.block_descriptions
    for size in (1, 31, 8192):
        decoder = StreamDecoder()
        restored = b''.join(decoder.feed(blob[i:i + size]) for i in range(0, len(blob), size))
        decoder.finish()
        assert restored == data
