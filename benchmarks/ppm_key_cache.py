"""Experimental bounded PPM key cache; never enabled by the main benchmark.

PPM count dictionaries only add keys. Rescaling changes values but never removes
keys, so object identity plus length identifies an unchanged sorted key set.
Strong references prevent Python id reuse while an entry is cached.
"""


def enable(capacity=4096, minimum_symbols=16):
    from cix import ppm

    cache = {}

    def eligible(counts, excluded):
        if not counts:
            return []
        if len(counts) < minimum_symbols:
            return [symbol for symbol in sorted(counts) if symbol not in excluded]
        entry = cache.get(id(counts))
        if entry is None or entry[1] != len(counts):
            if len(cache) >= capacity:
                cache.clear()
            entry = (counts, len(counts), sorted(counts))
            cache[id(counts)] = entry
        return [symbol for symbol in entry[2] if symbol not in excluded]

    ppm._eligible = eligible
    return cache


def tournament():
    import hashlib
    import json
    import random
    import time
    from cix import ppm

    rng = random.Random(81928)
    cases = [
        ('uniform', bytes(rng.randrange(256) for _ in range(8192))),
        ('small-alphabet', bytes(rng.randrange(32) for _ in range(8192))),
        ('periodic', bytes(range(256)) * 32),
    ]
    original = ppm._eligible
    rows = []
    try:
        for name, data in cases:
            for order in (1, 3, 5):
                for prefix in (b'', data[:4096]):
                    times, blobs = {}, {}
                    for mode in ('baseline', 'cached', 'cached', 'baseline'):
                        if mode == 'cached':
                            enable()
                        else:
                            ppm._eligible = original
                        start = time.perf_counter()
                        blob = ppm.encode_ppm(data, max_order=order, prefix_history=prefix)
                        times.setdefault(mode, []).append(time.perf_counter() - start)
                        blobs[mode] = blob
                    assert blobs['baseline'] == blobs['cached']
                    ppm._eligible = original
                    assert ppm.decode_ppm(blob, source_length=len(data), prefix_history=prefix) == data
                    rows.append(dict(case=name, order=order, prefix=len(prefix), times=times,
                                     size=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                                     round_trip=True, identical=True))
    finally:
        ppm._eligible = original
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    tournament()
