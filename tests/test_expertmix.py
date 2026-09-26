import random

from cix.expertmix import decode_expert_mix, encode_expert_mix


def _markov_bytes(length: int, seed: int = 7) -> bytes:
    rng = random.Random(seed)
    out = bytearray()
    state = rng.randrange(8)
    for _ in range(length):
        if rng.random() < 0.93:
            state = (state + (1 if rng.random() < 0.5 else 0)) & 7
        else:
            state = rng.randrange(8)
        out.append((state * 31 + (out[-1] if out else 0)) & 255)
    return bytes(out)


def test_context_expert_round_trip():
    data = _markov_bytes(6000)
    prefix = _markov_bytes(200, seed=11)
    blob = encode_expert_mix(
        data,
        orders=(0, 1, 2, 4),
        prefix_history=prefix,
    )
    restored = decode_expert_mix(
        blob,
        source_length=len(data),
        prefix_history=prefix,
    )
    assert restored == data


def test_context_expert_is_bounded_on_randomish_data():
    rng = random.Random(99)
    data = bytes(rng.randrange(256) for _ in range(2000))
    blob = encode_expert_mix(data, orders=(0, 1, 2))
    assert decode_expert_mix(blob, source_length=len(data)) == data
    # It is a candidate, not a mandatory representation; pathological expansion
    # must remain modest enough for MDL selection to reject cheaply.
    assert len(blob) < len(data) + 256
