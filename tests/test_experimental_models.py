import os
import random

from cix.ctw import decode_ctw, encode_ctw
from cix.mixerv2 import decode as decode_mixerv2
from cix.mixerv2 import encode as encode_mixerv2
from cix.wavelet import decode_wavelet, encode_wavelet


def sources():
    rng = random.Random(20260927)
    return (
        b"",
        b"A",
        b"ABRACADABRA!" * 50,
        bytes(0 if rng.random() < 0.9 else rng.randrange(1, 16) for _ in range(1000)),
        bytes(rng.randrange(256) for _ in range(1000)),
        b"".join(i.to_bytes(4, "little") for i in range(250)),
    )


def test_wavelet_cix_round_trip():
    for data in sources():
        blob = encode_wavelet(data)
        assert decode_wavelet(blob, source_length=len(data)) == data


def test_ctw_round_trip():
    for data in sources():
        blob = encode_ctw(data, depth=12)
        assert decode_ctw(blob, source_length=len(data)) == data


def test_fixed_share_mixer_v2_round_trip():
    for data in sources():
        blob = encode_mixerv2(data)
        assert decode_mixerv2(blob, source_length=len(data)) == data


def test_experimental_models_support_prefix_history():
    prefix = os.urandom(64)
    data = (prefix[-16:] + b"XYZ") * 20

    blob = encode_ctw(data, depth=12, prefix_history=prefix)
    assert decode_ctw(
        blob, source_length=len(data), prefix_history=prefix
    ) == data

    blob = encode_mixerv2(data, prefix_history=prefix)
    assert decode_mixerv2(
        blob, source_length=len(data), prefix_history=prefix
    ) == data
