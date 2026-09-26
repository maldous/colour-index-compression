#!/usr/bin/env python3
"""Generated-data portfolio benchmark.

No network, no external compressor backend, and no automatic CI trigger. This is intended
for rapid local tuning before a standard-corpus gate is run manually.
"""

import bz2
import lzma
import os
import random
import zlib

from cix.multinomial import ContextModel, StreamConfig, StreamEncoder, decompress


def pct(size, original):
    return 100.0 * size / original if original else 100.0


def build_sources():
    rng = random.Random(1)
    biased = bytes(
        0 if rng.random() < 0.90 else rng.randrange(1, 8)
        for _ in range(20000)
    )
    repeating = b"the quick brown fox jumps over the lazy dog. " * 500
    jsonish = b"".join(
        (
            f'{{"id":{i},"name":"student-{i % 137}",'
            f'"active":{str(i % 7 != 0).lower()},"score":{(i * 17) % 101}}}\n'
        ).encode()
        for i in range(500)
    )
    counter = b"".join(i.to_bytes(4, "little") for i in range(5000))
    mixed = (
        os.urandom(5000)
        + b"A" * 5000
        + repeating[:7000]
        + counter[:8000]
        + jsonish[:10000]
    )
    return {
        "random": os.urandom(20000),
        "biased": biased,
        "repeating": repeating,
        "jsonish": jsonish,
        "counter32": counter,
        "mixed": mixed,
    }


def main():
    config = StreamConfig(
        min_block=1024,
        max_block=8192,
        probe_stride=512,
        history_bytes=1 << 20,
        context_models=(
            ContextModel(1, 6),
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(4, 10),
        ),
    )

    for name, data in build_sources().items():
        encoder = StreamEncoder(config)
        blob = encoder.feed(data) + encoder.finish()
        assert decompress(blob) == data

        print(
            name,
            f"CIX={pct(len(blob), len(data)):.2f}%",
            f"zlib={pct(len(zlib.compress(data, 9)), len(data)):.2f}%",
            f"bzip2={pct(len(bz2.compress(data, 9)), len(data)):.2f}%",
            f"xz={pct(len(lzma.compress(data, preset=9)), len(data)):.2f}%",
            "models=" + ",".join(encoder.block_descriptions),
        )


if __name__ == "__main__":
    main()
