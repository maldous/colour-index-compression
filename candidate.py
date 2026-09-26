#!/usr/bin/env python3
"""Maximal candidate test harness for colour/index compression research.

This file is intentionally a research harness rather than a production codec.
It is designed to compare transform families, combinatorial block sizes,
raw fallback and optional recursion under exact accounting.
"""

CONFIG = {
    "block_sizes": [15, 31, 63, 127, 255],
    "chunk_sizes": [2048, 4096, 8192, 16384, 65536],
    "chunk_modes": ["fixed", "adaptive", "content-defined"],
    "predictors": [
        "identity",
        "bit-xor-lag",
        "byte-xor-lag",
        "byte-delta-lag",
        "delta16",
        "delta32",
        "delta64",
        "delta-of-delta",
        "byte-shuffle",
        "bitplane",
        "periodic",
        "bwt",
        "mtf",
        "zero-run",
        "lz-match",
        "context",
    ],
    "recursion": {
        "mode": "auto",
        "max_passes": 3,
        "minimum_gain_bits": 1,
    },
    "raw_fallback": True,
    "footer_once_per_file": True,
}

def research_principle():
    return (
        "Choose recursion only when the complete recursively encoded candidate "
        "is smaller than every non-recursive candidate after all metadata."
    )

if __name__ == "__main__":
    print(CONFIG)
    print(research_principle())
