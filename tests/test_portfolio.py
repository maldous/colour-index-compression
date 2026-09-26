import os

from cix.bitplanes import decode_bitplanes, encode_bitplanes
from cix.bwt import decode_bwt_block, encode_bwt_block
from cix.lz import decode_lz_block, encode_lz_block
from cix.numeric import decode_numeric_block, encode_numeric_block
from cix.multinomial import ContextModel, StreamConfig, compress, decompress
from cix.transforms import decode_transform_block, encode_transform_block


def test_lz_substreams_round_trip_and_exploit_repetition():
    data = b"the quick brown fox jumps over the lazy dog. " * 80
    payload, _ = encode_lz_block(
        data,
        context_models=(ContextModel(1, 8), ContextModel(2, 10)),
    )
    assert decode_lz_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 20



def test_lz_optimal_candidate_round_trip():
    unit = b"0123456789abcdef--generic-pattern--"
    data = (unit * 90) + (unit[:17] * 20) + (unit * 40)
    payload, _ = encode_lz_block(
        data,
        context_models=(ContextModel(1, 8),),
        chain=48,
    )
    assert decode_lz_block(payload, source_length=len(data)) == data

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
    data = b"".join(value.to_bytes(4, "little") for value in range(500))
    payload, _ = encode_numeric_block(data)
    assert decode_numeric_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 20


def test_numeric_transform_round_trip():
    data = b"".join(value.to_bytes(4, "little") for value in range(400))
    payload, _ = encode_transform_block(data)
    assert decode_transform_block(payload, source_length=len(data)) == data
    assert len(payload) < len(data) // 10


def test_bitplane_round_trip():
    data = bytes(0 if i % 100 else 1 for i in range(1500))
    payload, _ = encode_bitplanes(data)
    assert decode_bitplanes(payload, source_length=len(data)) == data


def test_full_portfolio_round_trip_nonstationary_stream():
    data = (
        os.urandom(256)
        + (b"ABRACADABRA!" * 40)
        + b"".join(value.to_bytes(4, "little") for value in range(100))
        + (b'{"kind":"student","active":true}\n' * 30)
    )
    config = StreamConfig(
        min_block=256,
        max_block=1024,
        probe_stride=128,
        history_bytes=1 << 16,
        lz_window_bytes=1 << 16,
        lz_chain=8,
        context_beam=2,
        transform_beam=2,
        adaptive_beam=1,
        enable_chains=False,
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
