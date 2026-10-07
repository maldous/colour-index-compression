"""Bounded, byte-order-preserving markup stack predictor for Hutter research.

This is a conservative wrapper around the existing text-safe CIXV3 stack
transform.  It accepts only balanced, lexically complete markup fragments;
anything with a malformed tag, literal ``<`` outside a recognized token, or an
unclosed stack is left byte-for-byte literal.  On accepted fragments an expected
closing tag is replaced by a marker.  The transform itself is self describing.
"""
from benchmarks import markup_columns as stack
from benchmarks import competitive_codec as paq
from cix.multinomial import vencode, vdecode
import hashlib
import json
import resource
import subprocess
import sys
import time
import zlib
from pathlib import Path

MAGIC = b"CIXSO1"
ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT_RANGES = ((0, 32768), (100000000, 32768), (400000000, 32768))


def _reliable(data):
    """Return true only for a whole balanced fragment the stack decoder can replay."""
    state = []
    at = 0
    for match in stack.TOKEN.finditer(data):
        if b"<" in data[at:match.start()]:
            return False
        token = match.group(); at = match.end()
        name = stack.NAME.match(token)
        if not name:  # comment, CDATA, processing instruction
            continue
        tag = name.group(1)
        if token.startswith(b"</"):
            if not state or tag != state[-1]:
                return False
            state.pop()
        elif not token.rstrip().endswith(b"/>"):
            state.append(tag)
    return not state and b"<" not in data[at:]


def encode(data, mode=1):
    if mode not in (0, 1):
        raise ValueError("unsupported structure mode")
    if not mode or not _reliable(data):
        return data, {"mode": 0, "eligible": False, "literal_fallback_bytes": len(data),
                      "transformed_bytes": len(data), "forced_closing_tags": 0}
    transformed, stats = stack.encode_stack(data, text=True)
    # A self describing transform with no prediction event only adds overhead.
    if not stats["forced_closing_tags"]:
        return data, {"mode": 0, "eligible": True, "literal_fallback_bytes": len(data),
                      "transformed_bytes": len(data), "forced_closing_tags": 0}
    return transformed, {**stats, "mode": 1, "eligible": True, "literal_fallback_bytes": 0}


def decode(transformed, mode, accounting=None):
    if mode == 0:
        return transformed
    if mode != 1:
        raise ValueError("unsupported structure mode")
    return stack.decode_stack(transformed)


def sha(data): return hashlib.sha256(data).hexdigest()


def _frame(source, mode, payload):
    return MAGIC + bytes([mode]) + vencode(len(source)) + zlib.crc32(source).to_bytes(4, "big") + payload


def encode_frame(source, options="-4"):
    """Select completed raw/stack+PAQ frames by physical size, raw on ties."""
    raw_payload = paq.encode_paq(source, "v215", options)
    raw_frame = _frame(source, 0, raw_payload)
    transformed, info = encode(source)
    if info["mode"]:
        structure_payload = paq.encode_paq(transformed, "v215", options)
        structure_frame = _frame(source, 1, structure_payload)
    else:
        structure_payload = raw_payload
        structure_frame = raw_frame
    selected = "structure" if len(structure_frame) < len(raw_frame) else "raw"
    frame = structure_frame if selected == "structure" else raw_frame
    outer_framing_bytes = len(MAGIC) + len(vencode(len(source))) + 4
    stats = {"options": options, "backend": "paq8px-v215", "raw_complete_bytes": len(raw_frame),
             "structure_complete_bytes": len(structure_frame), "selected": selected,
             "physical_bytes": len(frame), "raw_payload_bytes": len(raw_payload),
             "structure_payload_bytes": len(structure_payload), "outer_framing_bytes": outer_framing_bytes,
             "selector_bytes": 1,
             "frame_sha256": sha(frame), "raw_frame_sha256": sha(raw_frame),
             "structure_frame_sha256": sha(structure_frame), **info}
    return frame, stats


def decode_frame(frame):
    if len(frame) < 11 or frame[:6] != MAGIC or frame[6] not in (0, 1):
        raise ValueError("invalid structure PAQ frame")
    mode = frame[6]; original, pos = vdecode(frame, 7)
    if pos + 4 > len(frame): raise ValueError("truncated frame checksum")
    crc = int.from_bytes(frame[pos:pos + 4], "big")
    raw = paq.decode(frame[pos + 4:])
    restored = decode(raw, mode)
    if len(restored) != original or zlib.crc32(restored) != crc:
        raise ValueError("structure PAQ restoration mismatch")
    return restored


def _synthetic():
    return (b'<?xml version="1.0"?><page><ref n="1">alpha</ref><x><![CDATA[</>]]></x><!--c--></page>\n' * 360)


def run_trial(receipt, input_path, budget_seconds=300, options="-4"):
    """Immutable small-screen runner; resource limits are supplied externally."""
    receipt = Path(receipt).resolve()
    if receipt.exists() or not 0 < budget_seconds <= 300: raise ValueError("immutable receipt or invalid budget")
    source_path = Path(input_path); artifacts = receipt.parent / (receipt.stem + "-frames")
    artifacts.mkdir(parents=True, exist_ok=False); began = time.monotonic()
    plan = {"hypothesis": "On balanced XML-like fragments, exact stack-predicted closing-tag identities give unchanged PAQ v215 a smaller byte stream after transform/framing costs.",
            "matched_control": "Same PAQ v215 backend and -4 option over original bytes; final selection compares completed self-contained frames.",
            "mechanism": "Byte-order-preserving CIXV3 closing-tag markers; malformed or incomplete fragments are literal fallback.",
            "resource_budget": {"wall_seconds": budget_seconds, "cpu": "logical CPU 2", "ram_bytes": 2147483648, "swap_bytes": 0, "temporary_disk_bytes": 1073741824, "warmup": "none"},
            "promotion_criteria": "All child decoder hashes exact and transformed completed frame smaller on at least two fixed development regions; otherwise no reserved holdout is read.",
            "reserved_holdouts_untouched": [{"offset": 600000000, "bytes": 32768}, {"offset": 900000000, "bytes": 32768}]}
    inputs = [("synthetic-balanced-xml", _synthetic())]
    with source_path.open("rb") as handle:
        for offset, size in DEVELOPMENT_RANGES:
            handle.seek(offset); data = handle.read(size)
            if len(data) != size: raise ValueError("canonical input too short")
            inputs.append((f"enwik9-offset-{offset}", data))
    rows = []
    for name, data in inputs:
        if time.monotonic() - began > budget_seconds: raise TimeoutError("screen budget exhausted")
        start = time.monotonic(); frame, stats = encode_frame(data, options)
        packed = artifacts / f"{name}.cixso"; restored = packed.with_suffix(".restored"); packed.write_bytes(frame)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--decode", str(packed), "--output", str(restored)], check=True)
        if restored.read_bytes() != data: raise AssertionError("independent decoder mismatch")
        rows.append({"name": name, "input_bytes": len(data), "input_sha256": sha(data), **stats,
                     "encode_seconds": time.monotonic() - start, "round_trip": True,
                     "independent_decode_sha256": sha(restored.read_bytes())})
    output = {"schema": "cix-bounded-structure-order-v1", "phase": "completed", "hypothesis": plan,
              "implementation_sha256": sha(Path(__file__).read_bytes()), "rows": rows,
              "verification": "fresh child decoder SHA-256 equals input for every selected physical frame",
              "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    receipt.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n"); return output


def main():
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true"); parser.add_argument("--receipt"); parser.add_argument("--input"); parser.add_argument("--budget-seconds", type=int, default=300); parser.add_argument("--options", default="-4"); parser.add_argument("--decode"); parser.add_argument("--output")
    args = parser.parse_args()
    if args.decode:
        if not args.output: parser.error("--decode requires --output")
        Path(args.output).write_bytes(decode_frame(Path(args.decode).read_bytes()))
    elif args.run:
        if not args.receipt or not args.input: parser.error("--run requires --receipt --input")
        print(json.dumps(run_trial(args.receipt, args.input, args.budget_seconds, args.options), sort_keys=True))
    else: parser.error("choose --run or --decode")


if __name__ == "__main__":
    main()
