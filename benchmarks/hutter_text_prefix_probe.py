#!/usr/bin/env python3
"""Bounded, non-qualifying canonical-enwik9 prefix experiment.

The default PAQ8px v215 `-10L -forcetext` path is the strongest currently
available local text baseline that stays below the Hutter 10 GB RAM limit by its
documented nominal level. Results are physical archives plus independent SHA-256
restoration proof, but a prefix is never a Hutter score or full-file estimate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import resource
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = Path("/home/user/src/cix-baseline-data/inputs/enwik9")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prefix(source: Path, target: Path, size: int, *, expected_size: int = 1_000_000_000) -> None:
    if source.stat().st_size != expected_size:
        raise ValueError("source is not the canonical one-billion-byte enwik9 input")
    with source.open("rb") as inp, target.open("xb") as out:
        remaining = size
        while remaining:
            block = inp.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError("source ended before requested prefix")
            out.write(block)
            remaining -= len(block)


def run(command: list[str], output: Path, *, cpu: int) -> dict:
    metrics, log = output.with_suffix(".time"), output.with_suffix(".log")
    wrapped = ["taskset", "-c", str(cpu), "/usr/bin/time", "-f", "%e %M", "-o", str(metrics), *command]
    started = time.perf_counter()
    with log.open("wb") as sink:
        code = subprocess.run(wrapped, cwd=ROOT, stdout=sink, stderr=subprocess.STDOUT).returncode
    elapsed = time.perf_counter() - started
    if code:
        raise RuntimeError(f"command failed ({code}); see {log}")
    process_seconds, peak_rss_kib = metrics.read_text().strip().split()[-2:]
    return {"command": command, "cpu": cpu, "wall_seconds": elapsed,
            "process_seconds": float(process_seconds), "peak_rss_kib": int(peak_rss_kib), "log": str(log)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=CANONICAL)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--cpu", type=int, required=True)
    args = parser.parse_args()
    if args.bytes <= 0 or args.bytes > 64 * 1024 * 1024:
        parser.error("--bytes must be in 1..64 MiB for this bounded prefix probe")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inp, archive, restored = out / "enwik9-prefix.bin", out / "stream.paq8px", out / "restored.bin"
    prefix(args.source, inp, args.bytes)
    binary = ROOT / "benchmark-work/references/paq8px-v215/build-local/paq8px"
    if not binary.is_file():
        raise FileNotFoundError(binary)
    policy = {"engine": "paq8px-v215", "options": ["-10L", "-forcetext", "-simd", "AVX2"],
              "binary_sha256": digest(binary), "source": str(args.source), "prefix_bytes": args.bytes,
              "qualifying": False, "nonqualifying_reason": "prefix only; no full enwik9 or submission accounting"}
    encode = run([str(binary), "-10L", "-forcetext", "-simd", "AVX2", str(inp), str(archive)], archive, cpu=args.cpu)
    decode = run([str(binary), "-d", "-simd", "AVX2", str(archive), str(restored)], restored, cpu=args.cpu)
    if digest(inp) != digest(restored):
        raise ValueError("round trip hash mismatch")
    record = {"completed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "policy": policy,
              "input": {"bytes": inp.stat().st_size, "sha256": digest(inp)},
              "archive": {"bytes": archive.stat().st_size, "sha256": digest(archive)},
              "restored": {"bytes": restored.stat().st_size, "sha256": digest(restored)},
              "round_trip": True, "encode": encode, "decode": decode}
    (out / "complete.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
