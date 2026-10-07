"""Track A composition-feedback screen: paid future counts versus causal models.

The decoder-reproducible causal context is the high nibble of the preceding
byte.  ``causal`` uses a Laplace-adaptive arithmetic model.  ``feedback`` first
transmits the complete sparse successor-count vector for every context, then
uses the exact evolving remaining counts as its arithmetic predictor.  Thus the
only extra information is the paid count vector; the residual coder is range
coding in both cases.  This measures composition feedback, not a rank advantage.
"""
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cix.multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder

MAGIC = b"CIXTF1"
DEVELOPMENT_RANGES = ((0, 65536), (100000000, 65536), (400000000, 65536))
HOLDOFF_RANGES = ((700000000, 65536), (850000000, 65536))


def sha(data): return hashlib.sha256(data).hexdigest()


def _context(previous): return previous >> 4


def _vectors(source):
    vectors = [[0] * 256 for _ in range(16)]
    for previous, value in zip(source, source[1:]):
        vectors[_context(previous)][value] += 1
    return vectors


def _write_vectors(out, vectors):
    start = len(out)
    for counts in vectors:
        active = [symbol for symbol, count in enumerate(counts) if count]
        mask = sum(1 << symbol for symbol in active)
        out.extend(mask.to_bytes(32, "little"))
        for symbol in active:
            out.extend(vencode(counts[symbol]))
    return len(out) - start


def _read_vectors(frame, pos):
    vectors = []
    for _ in range(16):
        if pos + 32 > len(frame): raise ValueError("truncated composition mask")
        mask = int.from_bytes(frame[pos:pos + 32], "little"); pos += 32
        active = [symbol for symbol in range(256) if mask >> symbol & 1]
        counts = [0] * 256
        if active:
            for symbol in active:
                count, pos = vdecode(frame, pos)
                if not count: raise ValueError("zero active count")
                counts[symbol] = count
        vectors.append(counts)
    return vectors, pos


def _interval(counts, symbol):
    total = sum(counts)
    if total <= 0 or counts[symbol] <= 0: raise ValueError("invalid predictor composition")
    lo = sum(counts[:symbol])
    return lo, lo + counts[symbol], total


def _encode_causal(source):
    coder = _ArithmeticEncoder(); models = [[1] * 256 for _ in range(16)]
    for previous, value in zip(source, source[1:]):
        counts = models[_context(previous)]; lo, hi, total = _interval(counts, value)
        coder.encode(lo, hi, total); counts[value] += 1
    return coder.finish()


def _encode_feedback(source, vectors):
    coder = _ArithmeticEncoder(); counts = [row[:] for row in vectors]
    for previous, value in zip(source, source[1:]):
        row = counts[_context(previous)]; lo, hi, total = _interval(row, value)
        coder.encode(lo, hi, total); row[value] -= 1
    return coder.finish()


def encode(source, method):
    if method not in ("causal", "feedback"): raise ValueError("invalid method")
    out = bytearray(MAGIC + bytes([0 if method == "causal" else 1]))
    out.extend(vencode(len(source))); out.extend(zlib.crc32(source).to_bytes(4, "big"))
    framing = len(out)
    if source: out.append(source[0])
    metadata = 0
    if method == "feedback":
        vectors = _vectors(source); metadata = _write_vectors(out, vectors)
        payload, bits = _encode_feedback(source, vectors)
    else:
        payload, bits = _encode_causal(source)
    out.extend(vencode(bits)); out.extend(payload)
    return bytes(out), {"method": method, "physical_bytes": len(out), "framing_bytes": framing,
                         "first_literal_bytes": int(bool(source)), "composition_metadata_bytes": metadata,
                         "payload_bytes": len(payload), "payload_bits": bits,
                         "contexts_used": sum(bool(sum(x)) for x in _vectors(source)), "frame_sha256": sha(bytes(out))}


def _decode_symbol(coder, counts):
    total = sum(counts); target = coder.target(total); lo = 0
    for symbol, count in enumerate(counts):
        if target < lo + count:
            coder.update(lo, lo + count, total); return symbol
        lo += count
    raise ValueError("arithmetic symbol outside composition")


def decode(frame):
    if len(frame) < 7 or frame[:6] != MAGIC or frame[6] not in (0, 1): raise ValueError("invalid frame")
    method = ("causal", "feedback")[frame[6]]; pos = 7
    original, pos = vdecode(frame, pos)
    if pos + 4 > len(frame): raise ValueError("truncated CRC")
    crc = int.from_bytes(frame[pos:pos + 4], "big"); pos += 4
    first = None
    if original:
        if pos >= len(frame): raise ValueError("missing first literal")
        first = frame[pos]; pos += 1
    vectors = None
    if method == "feedback": vectors, pos = _read_vectors(frame, pos)
    bits, pos = vdecode(frame, pos); size = (bits + 7) // 8
    if pos + size != len(frame): raise ValueError("payload framing mismatch")
    coder = _ArithmeticDecoder(frame[pos:], bits); out = bytearray()
    if original: out.append(first)
    if method == "causal": models = [[1] * 256 for _ in range(16)]
    while len(out) < original:
        ctx = _context(out[-1])
        if method == "causal":
            row = models[ctx]; value = _decode_symbol(coder, row); row[value] += 1
        else:
            row = vectors[ctx]
            value = _decode_symbol(coder, row); row[value] -= 1
        out.append(value)
    result = bytes(out)
    if zlib.crc32(result) != crc: raise ValueError("checksum mismatch")
    return result


def _synthetic(n=65536):
    state = 0xC0FFEE11; out = bytearray()
    for _ in range(n):
        state = (1103515245 * state + 12345) & 0xffffffff
        out.append((out[-1] if out and state % 5 else state >> 24) & 255)
    return bytes(out)


def _one(name, source):
    rows, frames = [], {}
    for method in ("causal", "feedback"):
        frame, row = encode(source, method); frames[method] = frame
        restored = decode(frame); row.update(round_trip=restored == source, restored_sha256=sha(restored))
        rows.append(row)
    return {"name": name, "input_bytes": len(source), "input_sha256": sha(source), "rows": rows}, frames


def run_trial(receipt, input_path, budget_seconds=300):
    if not 0 < budget_seconds <= 300: raise ValueError("invalid budget")
    receipt = Path(receipt).resolve()
    if receipt.exists(): raise FileExistsError("immutable receipt exists")
    start = time.monotonic(); source_path = Path(input_path); artifacts = receipt.parent / (receipt.stem + "-frames")
    artifacts.mkdir(parents=True, exist_ok=False)
    plan = {"hypothesis": "Paid context successor compositions may improve a causal predictor enough to repay their physical metadata.",
            "matched_control": "Causal high-nibble context arithmetic with no future composition; feedback uses the same arithmetic backend after paying its complete composition vector.",
            "expected_mechanism": "Known successor deficits reduce the candidate alphabet and force late context symbols.",
            "promotion_criteria": "feedback smaller by >=0.5% on two disjoint development regions, all child-process decodes exact; otherwise do not read holdouts.",
            "resource_budget": {"wall_seconds": budget_seconds, "cpu": "logical CPU 2", "ram_bytes": 2147483648, "swap_bytes": 0, "temporary_disk_bytes": 1073741824, "warmup": "none"},
            "heldout_ranges_untouched": [{"offset": o, "bytes": n} for o, n in HOLDOFF_RANGES]}
    inputs = [("synthetic-repeat-edit-seed-c0ffee11", _synthetic())]
    with source_path.open("rb") as handle:
        for offset, size in DEVELOPMENT_RANGES:
            handle.seek(offset); data = handle.read(size)
            if len(data) != size: raise ValueError("input too short")
            inputs.append((f"enwik9-offset-{offset}", data))
    results = []
    for name, source in inputs:
        if time.monotonic() - start > budget_seconds: raise TimeoutError("budget exhausted")
        row, frames = _one(name, source)
        for method, frame in frames.items():
            packed = artifacts / f"{name}-{method}.cixtf"; restored = packed.with_suffix(".restored")
            packed.write_bytes(frame)
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--decode", str(packed), "--output", str(restored)], check=True)
            if restored.read_bytes() != source: raise AssertionError("independent decoder mismatch")
            next(x for x in row["rows"] if x["method"] == method)["independent_decode_sha256"] = sha(restored.read_bytes())
        results.append(row)
    causal = sum(next(x for x in r["rows"] if x["method"] == "causal")["physical_bytes"] for r in results)
    feedback = sum(next(x for x in r["rows"] if x["method"] == "feedback")["physical_bytes"] for r in results)
    output = {"schema": "cix-bounded-track-a-feedback-v1", "phase": "completed", "hypothesis": plan,
              "implementation_sha256": sha(Path(__file__).read_bytes()), "canonical_input": str(source_path),
              "development_regions": results, "causal_total_bytes": causal, "feedback_total_bytes": feedback,
              "feedback_minus_causal_bytes": feedback - causal,
              "verification": "independent child decoder SHA-256 equals input for every physical frame",
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n"); return output


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--run", action="store_true"); p.add_argument("--receipt"); p.add_argument("--input"); p.add_argument("--budget-seconds", type=int, default=300); p.add_argument("--decode"); p.add_argument("--output"); a = p.parse_args()
    if a.decode:
        if not a.output: p.error("--decode requires --output")
        Path(a.output).write_bytes(decode(Path(a.decode).read_bytes()))
    elif a.run:
        if not a.receipt or not a.input: p.error("--run requires --receipt --input")
        print(json.dumps(run_trial(a.receipt, a.input, a.budget_seconds), sort_keys=True))
    else: p.error("choose --run or --decode")


if __name__ == "__main__": main()
