import os

from cix.bitplanes import decode_bitplanes, encode_bitplanes
from cix.bwt import decode_bwt_block, encode_bwt_block
from cix.lz import decode_lz_block, encode_lz_block
from cix.numeric import decode_numeric_block, encode_numeric_block
from cix.multinomial import ContextModel, StreamConfig, compress, decompress
from cix.transforms import decode_transform_block, encode_transform_block


def test_lz_substreams_round_trip_and_exploit_repetition():
    data = b"the quick brown fox jumps over the lazy dog. " * 300
    payload, _ = encode_lz_block(
        data,
        context_models=(ContextModel(1, 8), ContextModel(2, 10)),
    )
    assert decode_lz_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 20


def test_lz_uses_previous_stream_history():
    prefix = b"shared-dictionary-sequence:" * 100
    data = prefix[-1000:] * 4
    payload, _ = encode_lz_block(
        data,
        prefix_history=prefix,
        context_models=(ContextModel(1, 8),),
    )
    assert decode_lz_block(
        payload,
        source_length=len(data),
        prefix_history=prefix,
    ) == data


def test_bwt_substreams_round_trip():
    data = (
        b'{"id":1,"name":"alice","active":true}\n'
        b'{"id":2,"name":"bob","active":true}\n'
    ) * 200
    payload, _ = encode_bwt_block(data)
    assert decode_bwt_block(payload, source_length=len(data)) == data


def test_numeric_native_round_trip():
    data = b"".join(value.to_bytes(4, "little") for value in range(2000))
    payload, _ = encode_numeric_block(data)
    assert decode_numeric_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 20


def test_numeric_transform_round_trip():
    data = b"".join(value.to_bytes(4, "little") for value in range(1000))
    payload, _ = encode_transform_block(data)
    assert decode_transform_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 10


def test_bitplane_round_trip():
    data = bytes(0 if i % 100 else 1 for i in range(5000))
    payload, _ = encode_bitplanes(data)
    assert decode_bitplanes(payload, source_length=len(data)) == data


def test_full_portfolio_round_trip_nonstationary_stream():
    data = (
        os.urandom(4096)
        + (b"ABRACADABRA!" * 1000)
        + b"".join(value.to_bytes(4, "little") for value in range(1500))
        + (b'{"kind":"student","active":true}\n' * 500)
    )
    config = StreamConfig(
        min_block=1024,
        max_block=8192,
        probe_stride=512,
        history_bytes=1 << 20,
        context_models=(
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(4, 10),
        ),
    )
    blob = compress(data, config)
    assert decompress(blob) == data


def test_extreme_preset_is_within_format_limits():
    config = StreamConfig.extreme()
    assert config.history_bytes <= 16 << 20
    assert config.lz_window_bytes <= config.history_bytes
    assert config.enable_lz
    assert config.enable_bwt
    assert config.enable_transforms
    assert config.enable_bitplanes
    assert config.enable_numeric
    assert config.enable_chains
