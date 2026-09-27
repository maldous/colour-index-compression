import random

from cix.ppm import decode_ppm, encode_ppm


def test_ppm_order_range_probe():
    n = 4096
    rng = random.Random(20260928)
    sources = []
    sources.append(bytes((i * 29 + (i % 11) * 7) & 255 for i in range(n)))
    markov = bytearray()
    x = 0
    for _ in range(n):
        if rng.random() < 0.035:
            x = rng.randrange(96)
        markov.append(x)
    sources.append(bytes(markov))
    repeated = bytearray((b"generic-context-pattern|" * 300)[:n])
    for i in range(n):
        if rng.random() < 0.02:
            repeated[i] ^= 1 << rng.randrange(8)
    sources.append(bytes(repeated))
    sources.append(b"".join(
        f"{i:06d}|{i % 137:03d}|{i % 17:02d}|{(i * 31) % 10007:05d}|{i % 2}\n".encode()
        for i in range(400)
    )[:n])

    incumbent_total = 0
    expanded_total = 0
    winners = []
    all_sizes = []
    for data in sources:
        sizes = {}
        for order in range(9):
            payload = encode_ppm(data, max_order=order)
            assert decode_ppm(payload, source_length=len(data)) == data
            sizes[order] = len(payload)
        incumbent_order = min((2, 3, 4), key=lambda o: (sizes[o], o))
        expanded_order = min(range(9), key=lambda o: (sizes[o], o))
        incumbent_total += sizes[incumbent_order]
        expanded_total += sizes[expanded_order]
        winners.append((incumbent_order, expanded_order))
        all_sizes.append(sizes)

    assert False, (
        f"PPM_ORDER_RANGE_PROBE incumbent={incumbent_total} expanded={expanded_total} "
        f"saved={incumbent_total-expanded_total} winners={winners} sizes={all_sizes}"
    )
