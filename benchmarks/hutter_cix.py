"""Offline draft runner for the stdlib-only CIX Hutter text profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from cix.cli import main_compress, main_decompress


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("options", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.operation == "encode":
        return main_compress([str(args.source), "-o", str(args.destination), *args.options])
    if args.options:
        parser.error("decode takes no codec options")
    return main_decompress([str(args.source), "-o", str(args.destination)])


if __name__ == "__main__":
    raise SystemExit(main())
