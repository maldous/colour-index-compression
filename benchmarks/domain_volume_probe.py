#!/usr/bin/env python3
"""Create or decode one self-contained domain-volume experiment artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from benchmarks import domain_volume


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--variant", choices=("original", "plane-stack", "delta-z", "jxl-planar3-e10"))
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.operation == "encode":
        if not args.variant:
            parser.error("--variant is required for encode")
        source = args.input.read_bytes()
        started = time.monotonic()
        frame = domain_volume.encode(source, args.variant)
        elapsed = time.monotonic() - started
        args.output.write_bytes(frame)
        row = {
            "variant": args.variant,
            "input_bytes": len(source),
            "input_sha256": hashlib.sha256(source).hexdigest(),
            "archive_bytes": len(frame),
            "archive_sha256": hashlib.sha256(frame).hexdigest(),
            "encode_seconds": elapsed,
            "representation": "exact original bytes" if args.variant == "original" else "self-contained domain-volume frame",
            "backend": "native_jxl" if args.variant == "jxl-planar3-e10" else "none; intended for a separately measured matched PAQ run",
        }
        if args.receipt:
            args.receipt.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
        print(json.dumps(row, sort_keys=True))
    else:
        started = time.monotonic()
        restored = domain_volume.decode(args.input.read_bytes())
        elapsed = time.monotonic() - started
        args.output.write_bytes(restored)
        print(json.dumps({"restored_bytes": len(restored), "restored_sha256": digest(args.output),
                          "decode_seconds": elapsed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
