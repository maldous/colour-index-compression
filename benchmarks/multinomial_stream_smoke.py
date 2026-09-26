#!/usr/bin/env python3
"""Small local smoke benchmark for the multinomial streaming core.

This deliberately uses generated data only. Standard corpora remain separate manual
benchmarks so pushes do not start expensive runs.
"""
import bz2
import lzma
import os
import random
import zlib

from cix.multinomial import ContextModel, StreamConfig, StreamEncoder


def pct(a, b):
    return 100.0 * a / b if b else 100.0


def main():
    rng = random.Random(1)
    sources = {
        "random": os.urandom(20000),
        "biased": bytes(0 if rng.random() < 0.9 else rng.randrange(1, 8) for _ in range(20000)),
        "repeating": b"the quick brown fox jumps over the lazy dog. " * 500,
        "varying": os.urandom(5000) + b"A" * 5000 + (b"abc123," * 1000) + os.urandom(5000),
    }
    config = StreamConfig(
        min_block=512,
        max_block=4096,
        probe_stride=256,
        context_models=(
            ContextModel(1, 6),
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(3, 10),
            ContextModel(4, 10),
        ),
    )

    for name, data in sources.items():
        encoder = StreamEncoder(config)
        cix = encoder.feed(data) + encoder.finish()
        print(
            name,
            f"CIX={pct(len(cix),len(data)):.2f}%",
            f"zlib={pct(len(zlib.compress(data,9)),len(data)):.2f}%",
            f"bz2={pct(len(bz2.compress(data,9)),len(data)):.2f}%",
            f"xz={pct(len(lzma.compress(data,preset=9)),len(data)):.2f}%",
            "modes=" + ",".join(encoder.block_descriptions),
        )


if __name__ == "__main__":
    main()
