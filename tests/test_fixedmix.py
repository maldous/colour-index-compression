import random

from cix.fixedmix import decode_fixed_mix, encode_fixed_mix
from cix.multinomial import StreamConfig, compress, decompress


def test_fixed_mix_round_trip():
    rng = random.Random(20260927)
    sources = (
        b"periodic-sequence|" * 40,
        bytes(0 if rng.random() < 0.9 else rng.randrange(1, 16) for _ in range(1500)),
        bytes(rng.randrange(256) for _ in range(1500)),
    )
    for data in sources:
        blob = encode_fixed_mix(data)
        assert decode_fixed_mix(blob, source_length=len(data)) == data


def test_fixed_mix_can_compete_in_extreme_stream():
    data = (b"ABRACADABRA!" * 200) + (b"0123456789abcdef" * 100)
    config = StreamConfig(
        min_block=1024,
        max_block=4096,
        probe_stride=512,
        enable_fixed_mix=True,
        fixed_mix_max_block=4096,
        enable_chains=False,
        enable_persistent_adaptive=False,
        context_beam=1,
        transform_beam=1,
        adaptive_beam=1,
        lz_chain=8,
    )
    blob = compress(data, config)
    assert decompress(blob) == data
