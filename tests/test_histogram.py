import random

from cix.histogram import decode, encode_best, encode_candidates


def _counts(data: bytes) -> list[int]:
    result = [0] * 256
    for value in data:
        result[value] += 1
    return result


def test_experimental_count_vectors_round_trip():
    rng = random.Random(20260928)
    sources = (
        bytes(rng.randrange(256) for _ in range(8192)),
        bytes(0 if rng.random() < 0.92 else rng.randrange(1, 16) for _ in range(8192)),
        bytes(i & 255 for i in range(8192)),
        (bytes(range(37)) * 300)[:8192],
        b"ABRACADABRA!" * 500,
    )
    for data in sources:
        counts = _counts(data)
        for blob in encode_candidates(counts).values():
            assert decode(blob, total=len(data)) == counts
        blob, _ = encode_best(counts)
        assert decode(blob, total=len(data)) == counts
