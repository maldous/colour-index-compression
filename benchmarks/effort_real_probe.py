#!/usr/bin/env python3
"""Compare normal and maximum-effort universal CIX on real Canterbury members."""

from __future__ import annotations

import bz2
import gzip
import lzma
import time
import urllib.request
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None
try:
    import zstandard as zstd
except ImportError:
    zstd = None

from cix.cli import config_for_level
from cix.multinomial import StreamEncoder, decompress


FILES = {
    "alice29.txt": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "cp.html": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    "fields.c": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
}


def encode(data: bytes, level: int):
    cfg = config_for_level(level)
    start = time.perf_counter()
    enc = StreamEncoder(cfg)
    blob = enc.feed(data) + enc.finish()
    elapsed = time.perf_counter() - start
    assert decompress(blob) == data
    return blob, elapsed, enc.block_descriptions


def main():
    root = Path("benchmark-work/effort-real")
    root.mkdir(parents=True, exist_ok=True)

    for name, url in FILES.items():
        path = root / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        data = path.read_bytes()

        results = {}
        for level in (6, 9):
            blob, secs, models = encode(data, level)
            results[f"cix-{level}"] = {
                "bytes": len(blob),
                "seconds": secs,
                "models": models,
            }

        refs = {
            "gzip": len(gzip.compress(data, 9)),
            "bzip2": len(bz2.compress(data, 9)),
            "xz": len(lzma.compress(data, preset=9)),
            "brotli": (
                len(brotli.compress(data, quality=11))
                if brotli else None
            ),
            "zstd": (
                len(zstd.ZstdCompressor(level=19).compress(data))
                if zstd else None
            ),
        }
        print(name, len(data), results, "refs", refs, flush=True)


if __name__ == "__main__":
    main()
