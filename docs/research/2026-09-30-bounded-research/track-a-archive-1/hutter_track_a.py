"""Bounded Track A: matched-information candidate-rank versus range coding.

The predictor is deliberately small and decoder reproducible: after a literal
first byte it proposes that the next byte repeats the previous byte.  For each
previous-byte context both representations receive the exact number of success
events and failures.  They both charge that count vector, the first literal,
the exception bytes, framing, and an exact ordering representation.  ``rank``
enumerates the conditional type class; ``range`` arithmetic-codes the same
remaining-count process.  This is a discriminating CIX test, not a PAQ claim.
"""
import argparse
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path

# Permit direct immutable experiment invocation without a caller-set PYTHONPATH.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cix.multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder
from benchmarks.paq_cix_residual import rank_binary, unrank_binary, arith_binary, unarith_binary

MAGIC = b"CIXTA1"
DEVELOPMENT_RANGES = ((0, 65536), (100000000, 65536), (400000000, 65536))
HOLDOFF_RANGES = ((700000000, 65536), (850000000, 65536))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _events(source):
    if not source:
        return [b"" for _ in range(256)], b""
    groups = [bytearray() for _ in range(256)]
    exceptions = bytearray()
    for previous, value in zip(source, source[1:]):
        ok = value == previous
        groups[previous].append(ok)
        if not ok:
            exceptions.append(value)
    return [bytes(g) for g in groups], bytes(exceptions)


def encode(source, method):
    """Return a self-contained physical stream and all charged byte components."""
    if method not in ("rank", "range"):
        raise ValueError("method must be rank or range")
    groups, exceptions = _events(source)
    out = bytearray(MAGIC + bytes([0 if method == "rank" else 1]))
    out.extend(vencode(len(source)))
    out.extend(zlib.crc32(source).to_bytes(4, "big"))
    framing_bytes = len(out)
    if source:
        out.append(source[0])
    first_literal_bytes = int(bool(source))
    count_start = len(out)
    for stream in groups:
        n = len(stream)
        out.extend(vencode(n))
        if n:
            out.extend(vencode(sum(stream)))
    count_bytes = len(out) - count_start
    order_start = len(out)
    for stream in groups:
        n = len(stream)
        if not n:
            continue
        payload = rank_binary(stream) if method == "rank" else arith_binary(stream)
        out.extend(payload)
    ordering_bytes = len(out) - order_start
    out.extend(exceptions)
    stats = {
        "method": method,
        "physical_bytes": len(out),
        "framing_bytes": framing_bytes,
        "first_literal_bytes": first_literal_bytes,
        "count_metadata_bytes": count_bytes,
        "ordering_bytes": ordering_bytes,
        "exception_bytes": len(exceptions),
        "contexts_used": sum(bool(g) for g in groups),
        "events": max(0, len(source) - 1),
        "successes": sum(sum(g) for g in groups),
        "exceptions": len(exceptions),
        "frame_sha256": sha(bytes(out)),
    }
    return bytes(out), stats


def decode(frame):
    if len(frame) < len(MAGIC) + 1 or frame[:len(MAGIC)] != MAGIC or frame[len(MAGIC)] not in (0, 1):
        raise ValueError("invalid Track A frame")
    method = ("rank", "range")[frame[len(MAGIC)]]
    pos = len(MAGIC) + 1
    original, pos = vdecode(frame, pos)
    if pos + 4 > len(frame):
        raise ValueError("truncated checksum")
    checksum = int.from_bytes(frame[pos:pos + 4], "big")
    pos += 4
    first = None
    if original:
        if pos >= len(frame):
            raise ValueError("missing first literal")
        first = frame[pos]
        pos += 1
    counts = []
    for _ in range(256):
        n, pos = vdecode(frame, pos)
        k = 0
        if n:
            k, pos = vdecode(frame, pos)
            if k > n:
                raise ValueError("invalid success count")
        counts.append((n, k))
    groups = []
    for n, k in counts:
        if method == "rank":
            width = (math.comb(n, k) - 1).bit_length()
            size = (width + 7) // 8
            if pos + size > len(frame):
                raise ValueError("truncated rank")
            stream = unrank_binary(frame[pos:pos + size], n, k)
            pos += size
        else:
            stream, pos = unarith_binary(frame, pos, n, k)
        groups.append(stream)
    expected_exceptions = sum(n - k for n, k in counts)
    if pos + expected_exceptions != len(frame):
        raise ValueError("exception stream length mismatch")
    exceptions = iter(frame[pos:])
    indices = [0] * 256
    out = bytearray()
    if original:
        out.append(first)
    while len(out) < original:
        context = out[-1]
        index = indices[context]
        if index >= len(groups[context]):
            raise ValueError("context event underflow")
        success = groups[context][index]
        indices[context] += 1
        out.append(context if success else next(exceptions))
    if any(indices[i] != len(groups[i]) for i in range(256)):
        raise ValueError("unused context events")
    result = bytes(out)
    if zlib.crc32(result) != checksum:
        raise ValueError("checksum mismatch")
    return result


def _synthetic(n=65536):
    # Fixed high-repeat/edit mixture; seed encoded by recurrence constants.
    state = 0xC1A0F00D
    out = bytearray()
    for i in range(n):
        state = (1664525 * state + 1013904223) & 0xffffffff
        out.append(out[-1] if out and state % 7 else (state >> 16) & 0xff)
    return bytes(out)


def _measure(name, source, budget_seconds, work):
    start = time.monotonic()
    frames, rows = {}, []
    for method in ("rank", "range"):
        if time.monotonic() - start > budget_seconds:
            raise TimeoutError("trial budget exhausted before physical frames completed")
        frame, stat = encode(source, method)
        frames[method] = frame
        stat["round_trip"] = decode(frame) == source
        stat["restored_sha256"] = sha(decode(frame))
        rows.append(stat)
    if not all(row["round_trip"] for row in rows):
        raise AssertionError("in-process verification failed")
    return {"name": name, "input_bytes": len(source), "input_sha256": sha(source),
            "elapsed_seconds": time.monotonic() - start, "rows": rows}, frames


def run_trial(receipt, input_path, budget_seconds=300):
    """Write an immutable receipt.  This function has no hidden mutable state."""
    if budget_seconds <= 0 or budget_seconds > 300:
        raise ValueError("budget must be in (0, 300]")
    receipt = Path(receipt).resolve()
    if receipt.exists():
        raise FileExistsError("refusing to overwrite immutable receipt")
    source_path = Path(input_path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    began = time.time()
    hypotheses = {
        "hypothesis": "With identical previous-byte candidate predictions and paid per-context success counts, exact conditional ranks may use fewer physical bytes than arithmetic coding of the same remaining-count process.",
        "matched_control": "Arithmetic coding receives the identical context event sequences, count vector, exception sequence, first literal, source length, and checksum.",
        "expected_mechanism": "Conditional composition ranks eliminate the ordering uncertainty after a context's success count is known; range coding receives that same constraint.",
        "promotion_criteria": "Exact round trip on every development input; rank must beat range by >= 0.5% of total bytes on at least two disjoint development regions before any untouched holdout is read.",
        "resource_budget": {"wall_seconds": budget_seconds, "cpu": "logical CPU 2", "ram_bytes": 2147483648, "swap_bytes": 0, "temporary_disk_bytes": 1073741824, "warmup": "none"},
        "heldout_ranges_untouched": [{"offset": o, "bytes": n} for o, n in HOLDOFF_RANGES],
    }
    all_rows = []
    artifacts = receipt.parent / (receipt.stem + "-frames")
    artifacts.mkdir(parents=True, exist_ok=False)
    inputs = [("synthetic-repeat-edit-seed-c1a0f00d", _synthetic())]
    with source_path.open("rb") as handle:
        for offset, size in DEVELOPMENT_RANGES:
            handle.seek(offset)
            data = handle.read(size)
            if len(data) != size:
                raise ValueError("canonical input shorter than declared development region")
            inputs.append((f"enwik9-offset-{offset}", data))
    for name, data in inputs:
        row, frames = _measure(name, data, budget_seconds - (time.time() - began), artifacts)
        for method, frame in frames.items():
            path = artifacts / f"{name}-{method}.cix-ta"
            path.write_bytes(frame)
            # A fresh interpreter is the independent actual decoder check.
            restored = artifacts / f"{name}-{method}.restored"
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--decode", str(path), "--output", str(restored)], check=True)
            if restored.read_bytes() != data:
                raise AssertionError("independent decoder SHA mismatch")
            next(r for r in row["rows"] if r["method"] == method)["independent_decode_sha256"] = sha(restored.read_bytes())
        all_rows.append(row)
    rank_total = sum(next(r for r in row["rows"] if r["method"] == "rank")["physical_bytes"] for row in all_rows)
    range_total = sum(next(r for r in row["rows"] if r["method"] == "range")["physical_bytes"] for row in all_rows)
    result = {"schema": "cix-bounded-track-a-v1", "phase": "completed", "started_unix": began,
              "completed_unix": time.time(), "hypothesis": hypotheses,
              "implementation_sha256": sha(Path(__file__).read_bytes()),
              "canonical_input": str(source_path), "development_regions": all_rows,
              "rank_total_bytes": rank_total, "range_total_bytes": range_total,
              "rank_minus_range_bytes": rank_total - range_total,
              "verification": "independent child decoder SHA-256 equals input for every physical frame",
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--receipt")
    parser.add_argument("--input")
    parser.add_argument("--budget-seconds", type=int, default=300)
    parser.add_argument("--decode")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.decode:
        if not args.output:
            parser.error("--decode requires --output")
        Path(args.output).write_bytes(decode(Path(args.decode).read_bytes()))
    elif args.run:
        if not args.receipt or not args.input:
            parser.error("--run requires --receipt and --input")
        print(json.dumps(run_trial(args.receipt, args.input, args.budget_seconds), sort_keys=True))
    else:
        parser.error("choose --run or --decode")


if __name__ == "__main__":
    main()
