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
CANONICAL_SHA256 = "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc"


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


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def run(command: list[str], output: Path, *, cpu: int) -> dict:
    metrics, log = output.with_suffix(".time"), output.with_suffix(".log")
    wrapped = ["taskset", "-c", str(cpu), "/usr/bin/time", "-f", "%e %U %S %M", "-o", str(metrics), *command]
    started = time.perf_counter()
    with log.open("wb") as sink:
        code = subprocess.run(wrapped, cwd=ROOT, stdout=sink, stderr=subprocess.STDOUT).returncode
    elapsed = time.perf_counter() - started
    values = metrics.read_text().strip().split() if metrics.exists() else []
    details = {"command": command, "cpu": cpu, "outer_wall_seconds": elapsed, "returncode": code,
               "log": str(log), "completed": code == 0}
    if len(values) == 4:
        details.update(inner_wall_seconds=float(values[0]), user_cpu_seconds=float(values[1]),
                       system_cpu_seconds=float(values[2]), peak_rss_kib=int(values[3]))
    if code:
        raise RuntimeError(json.dumps(details, sort_keys=True))
    return details


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
    preflight = {"source": str(args.source), "prefix_bytes": args.bytes, "runner_sha256": digest(Path(__file__))}
    try:
        source_sha256 = digest(args.source)
        if source_sha256 != CANONICAL_SHA256:
            raise ValueError("source SHA-256 is not canonical enwik9")
        prefix(args.source, inp, args.bytes)
    except Exception as error:
        write_json(out / "failed.json", {"state": "FAILED_PREFLIGHT", "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                         "preflight": preflight, "error": str(error)})
        raise
    binary = ROOT / "benchmark-work/references/paq8px-v215/build-local/paq8px"
    if not binary.is_file():
        raise FileNotFoundError(binary)
    policy = {"engine": "paq8px-v215 reference text backend", "options": ["-10L", "-forcetext", "-simd", "AVX2"],
              "binary_sha256": digest(binary), "runner_sha256": digest(Path(__file__)),
              "source": str(args.source), "source_sha256": source_sha256, "prefix_bytes": args.bytes,
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "qualifying": False, "nonqualifying_reason": "prefix only; no full enwik9 or submission accounting"}
    started = {"state": "STARTED", "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "policy": policy,
               "input": {"bytes": inp.stat().st_size, "sha256": digest(inp)}}
    write_json(out / "started.json", started)
    try:
        encode = run([str(binary), "-10L", "-forcetext", "-simd", "AVX2", str(inp), str(archive)], archive, cpu=args.cpu)
        write_json(out / "encode.json", {"state": "COMPLETE", **started, "archive": {"bytes": archive.stat().st_size, "sha256": digest(archive)}, "encode": encode})
        decode = run([str(binary), "-d", "-simd", "AVX2", str(archive), str(restored)], restored, cpu=args.cpu)
        input_hash, restored_hash = digest(inp), digest(restored)
        if inp.stat().st_size != restored.stat().st_size or input_hash != restored_hash:
            raise ValueError("round trip byte count or hash mismatch")
        record = {"completed_at": dt.datetime.now(dt.timezone.utc).isoformat(), "policy": policy,
                  "input": {"bytes": inp.stat().st_size, "sha256": input_hash},
                  "archive": {"bytes": archive.stat().st_size, "sha256": digest(archive)},
                  "restored": {"bytes": restored.stat().st_size, "sha256": restored_hash},
                  "round_trip": True, "encode": encode, "decode": decode}
        write_json(out / "complete.json", record)
        print(json.dumps(record, indent=2))
        return 0
    except Exception as error:
        write_json(out / "failed.json", {"state": "FAILED", "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                         "policy": policy, "error": str(error)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
