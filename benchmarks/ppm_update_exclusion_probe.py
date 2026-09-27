#!/usr/bin/env python3
from __future__ import annotations

import bz2
import gzip
import lzma
import random
import urllib.request
from pathlib import Path

import brotli
import zstandard as zstd

from cix.ppm import decode_ppm, encode_ppm

FILES = {
    "alice29-64k": (
        "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
        65536,
    ),
    "cp.html": (
        "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
        None,
    ),
    "fields.c": (
        "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
        None,
    ),
    "grammar.lsp": (
        "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
        None,
    ),
    "xargs.1": (
        "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
        None,
    ),
}


def refs(data: bytes) -> dict[str, int]:
    return {
        "gzip": len(gzip.compress(data, 9)),
        "bzip2": len(bz2.compress(data, 9)),
        "xz": len(lzma.compress(data, preset=9)),
        "brotli": len(brotli.compress(data, quality=11)),
        "zstd": len(zstd.ZstdCompressor(level=19).compress(data)),
    }


def measure(name: str, data: bytes) -> tuple[int, int]:
    standard = encode_ppm(data, max_order=4, update_exclusion=False)
    updated = encode_ppm(data, max_order=4, update_exclusion=True)
    assert decode_ppm(standard, source_length=len(data)) == data
    assert decode_ppm(updated, source_length=len(data)) == data
    delta = len(updated) - len(standard)
    pct = (100.0 * delta / len(standard)) if standard else 0.0
    print(
        name,
        len(data),
        "ppm-standard",
        len(standard),
        "ppm-update-exclusion",
        len(updated),
        "delta",
        delta,
        f"{pct:+.3f}%",
        "refs",
        refs(data),
        flush=True,
    )
    return len(standard), len(updated)


def main() -> None:
    root = Path("benchmark-work/ppm-update-exclusion")
    root.mkdir(parents=True, exist_ok=True)
    total_standard = 0
    total_updated = 0
    wins = 0

    for name, (url, limit) in FILES.items():
        filename = url.rsplit("/", 1)[-1]
        path = root / filename
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        data = path.read_bytes()
        if limit is not None:
            data = data[:limit]
        standard, updated = measure(name, data)
        total_standard += standard
        total_updated += updated
        wins += updated < standard

    rng = random.Random(0)
    synthetic = {
        "random-8k": rng.randbytes(8192),
        "biased-8k": bytes(0 if rng.random() < 0.9 else rng.randrange(1, 256) for _ in range(8192)),
        "periodic-8k": (bytes(range(64)) * 128),
    }
    for name, data in synthetic.items():
        standard, updated = measure(name, data)
        total_standard += standard
        total_updated += updated
        wins += updated < standard

    delta = total_updated - total_standard
    pct = 100.0 * delta / total_standard
    print(
        "TOTAL",
        "standard",
        total_standard,
        "updated",
        total_updated,
        "delta",
        delta,
        f"{pct:+.3f}%",
        "wins",
        f"{wins}/{len(FILES) + len(synthetic)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
