#!/usr/bin/env python3
"""Pinned direct-zstd control adapter for the bounded Hutter screening runner."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import zstandard as zstd
import zstandard.backend_c as backend


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def checked_backend(expected: str) -> None:
    actual = digest(Path(backend.__file__))
    if actual != expected:
        raise SystemExit("zstandard backend hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--backend-sha256", required=True)
    args = parser.parse_args(); checked_backend(args.backend_sha256)
    if args.mode == "encode":
        args.output.write_bytes(zstd.ZstdCompressor(level=19).compress(args.input.read_bytes()))
    else:
        args.output.write_bytes(zstd.ZstdDecompressor().decompress(args.input.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
