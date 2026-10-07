#!/usr/bin/env python3
"""DIRECTIONAL-LANES-1: bounded deterministic-order transport screen."""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work" / "directional-lanes-v1"
PLAN = HERE / "plan.json"
MAGIC = b"DLV1"
CODECS = {1: "zlib9", 2: "xz1"}
TRANSFORMS = {
    0: "identity", 1: "reverse_bytes", 2: "reverse_bits", 3: "center_out",
    4: "lanes2_separate", 5: "lanes2_concatenated",
    6: "lanes3_separate", 7: "lanes3_concatenated",
    8: "lanes4_separate", 9: "lanes4_concatenated",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def centre_order(n):
    c = (n - 1) // 2
    out = []
    d = 0
    while len(out) < n:
        right = c + d
        left = c - d
        if d == 0:
            if 0 <= c < n:
                out.append(c)
        else:
            if right < n:
                out.append(right)
            if left >= 0:
                out.append(left)
        d += 1
    assert sorted(out) == list(range(n))
    return out


def bits_of(data):
    return [(byte >> (7 - bit)) & 1 for byte in data for bit in range(8)]


def pack(bits):
    out = bytearray((len(bits) + 7) // 8)
    for i, bit in enumerate(bits):
        out[i // 8] |= bit << (7 - (i % 8))
    return bytes(out)


def unpack_bits(data, count):
    if len(data) != (count + 7) // 8:
        raise ValueError("packed lane length")
    if count % 8 and data and (data[-1] & ((1 << (8 - count % 8)) - 1)):
        raise ValueError("nonzero lane padding")
    return [(data[i // 8] >> (7 - (i % 8))) & 1 for i in range(count)]


def lanes(data, k):
    allbits = bits_of(data)
    return [pack(allbits[j::k]) for j in range(k)]


def unlanes(parts, n, k):
    total = n * 8
    if len(parts) != k:
        raise ValueError("lane count")
    out = [0] * total
    for j, part in enumerate(parts):
        count = (total - 1 - j) // k + 1 if j < total else 0
        source = unpack_bits(part, count)
        out[j::k] = source
    return pack(out)


def transform(data, ident):
    if ident == 0:
        return [data]
    if ident == 1:
        return [data[::-1]]
    if ident == 2:
        return [pack(bits_of(data)[::-1])]
    if ident == 3:
        return [bytes(data[i] for i in centre_order(len(data)))]
    k = (ident - 4) // 2 + 2
    grouped = lanes(data, k)
    return grouped if ident % 2 == 0 else [b"".join(grouped)]


def inverse(parts, n, ident):
    if ident == 0:
        if len(parts) != 1 or len(parts[0]) != n: raise ValueError("identity")
        return parts[0]
    if ident == 1:
        if len(parts) != 1 or len(parts[0]) != n: raise ValueError("reverse bytes")
        return parts[0][::-1]
    if ident == 2:
        if len(parts) != 1 or len(parts[0]) != n: raise ValueError("reverse bits")
        return pack(bits_of(parts[0])[::-1])
    if ident == 3:
        if len(parts) != 1 or len(parts[0]) != n: raise ValueError("centre order")
        result = bytearray(n)
        for pos, byte in zip(centre_order(n), parts[0]): result[pos] = byte
        return bytes(result)
    k = (ident - 4) // 2 + 2
    if ident % 2 == 0:
        return unlanes(parts, n, k)
    lengths = [((n * 8 - 1 - j) // k + 1 + 7) // 8 if j < n * 8 else 0 for j in range(k)]
    if len(parts) != 1 or len(parts[0]) != sum(lengths): raise ValueError("concatenated lanes")
    joined = parts[0]
    split, at = [], 0
    for length in lengths:
        split.append(joined[at:at + length]); at += length
    return unlanes(split, n, k)


def compress(data, codec):
    return zlib.compress(data, 9) if codec == 1 else lzma.compress(data, format=lzma.FORMAT_XZ, preset=1)


def decompress(data, codec):
    if codec == 1:
        d = zlib.decompressobj(); result = d.decompress(data) + d.flush()
        if not d.eof or d.unused_data or d.unconsumed_tail: raise ValueError("bad zlib stream")
        return result
    d = lzma.LZMADecompressor(format=lzma.FORMAT_XZ); result = d.decompress(data)
    if not d.eof or d.unused_data: raise ValueError("bad xz stream")
    return result


def frame(data, ident, codec):
    raw = transform(data, ident)
    coded = [compress(part, codec) for part in raw]
    return MAGIC + struct.pack(">IBBB", len(data), ident, codec, len(coded)) + b"".join(struct.pack(">I", len(part)) + part for part in coded)


def unframe(blob):
    if len(blob) < 11 or blob[:4] != MAGIC: raise ValueError("bad frame magic")
    n, ident, codec, count = struct.unpack(">IBBB", blob[4:11])
    if ident not in TRANSFORMS or codec not in CODECS: raise ValueError("unknown frame choice")
    expected_count = ((ident - 4) // 2 + 2) if ident >= 4 and ident % 2 == 0 else 1
    if count != expected_count: raise ValueError("frame stream count")
    at, raw = 11, []
    for _ in range(count):
        if at + 4 > len(blob): raise ValueError("missing stream length")
        length = struct.unpack(">I", blob[at:at + 4])[0]; at += 4
        if at + length > len(blob): raise ValueError("truncated stream")
        raw.append(decompress(blob[at:at + length], codec)); at += length
    if at != len(blob): raise ValueError("trailing frame bytes")
    result = inverse(raw, n, ident)
    if len(result) != n: raise ValueError("restored length")
    return result


def validate_synthetic():
    for n in range(18):
        data = bytes((17 * i + 3) % 256 for i in range(n))
        for ident in TRANSFORMS:
            expected_parts = transform(data, ident)
            assert inverse(expected_parts, n, ident) == data, (n, ident, "transform")
            for codec in CODECS:
                assert unframe(frame(data, ident, codec)) == data, (n, ident, codec, "frame")


def input_records(plan):
    records = plan["inputs"]["source_windows"] + plan["inputs"]["compressed_middle_windows"]
    out = []
    for record in records:
        with open(record["path"], "rb") as handle:
            handle.seek(record["offset"]); data = handle.read(record["bytes"])
        actual = sha(data)
        if len(data) != record["bytes"] or actual != record["sample_sha256"]:
            raise ValueError(f"frozen input mismatch: {record['id']}")
        out.append((record, data))
    return out


def run():
    started = time.monotonic()
    plan_bytes = PLAN.read_bytes(); plan = json.loads(plan_bytes)
    validate_synthetic()
    records = input_records(plan)
    WORK.mkdir(parents=True, exist_ok=True)
    all_rows, retained, source_rows = [], [], []
    for record, data in records:
        rows = []
        for ident, name in TRANSFORMS.items():
            for codec, coder in CODECS.items():
                blob = frame(data, ident, codec)
                assert unframe(blob) == data
                row = {"transform_id": ident, "transform": name, "codec_id": codec, "codec": coder,
                       "frame_bytes": len(blob), "frame_sha256": sha(blob), "payload_bytes": len(blob) - 11 - 4 * len(transform(data, ident))}
                rows.append(row)
        identity_by_codec = {row["codec_id"]: row["frame_bytes"] for row in rows if row["transform_id"] == 0}
        best_identity = min(row["frame_bytes"] for row in rows if row["transform_id"] == 0)
        for row in rows:
            row["delta_vs_same_coder_identity"] = row["frame_bytes"] - identity_by_codec[row["codec_id"]]
            row["delta_vs_best_identity"] = row["frame_bytes"] - best_identity
            row["beats_same_coder_identity"] = row["delta_vs_same_coder_identity"] < 0
        best_by_codec = {codec: min((r for r in rows if r["codec_id"] == codec), key=lambda r: (r["frame_bytes"], r["transform_id"])) for codec in CODECS}
        for codec, row in best_by_codec.items():
            blob = frame(data, row["transform_id"], codec)
            name = f"{record['id']}--{CODECS[codec]}.dlv"
            path = WORK / name; path.write_bytes(blob)
            fresh = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--decode", str(path)], check=True, capture_output=True, text=True)
            restored = json.loads(fresh.stdout)
            if restored["sha256"] != sha(data) or restored["bytes"] != len(data): raise ValueError("fresh decode mismatch")
            retained.append({"id": record["id"], "category": record["category"], "codec": CODECS[codec], "path": str(path), "bytes": len(blob), "sha256": sha(blob), "fresh_restore": restored})
        best = min(rows, key=lambda r: (r["frame_bytes"], r["transform_id"], r["codec_id"]))
        source_rows.append({"id": record["id"], "category": record["category"], "source_bytes": len(data), "source_sha256": sha(data),
                            "best_identity_bytes": best_identity, "best": best, "rows": rows})
        all_rows.extend((record["category"], row) for row in rows)
    grouped = {}
    for category, row in all_rows:
        key = f"{category}/{row['transform']}/{row['codec']}"
        aggregate = grouped.setdefault(key, {"category": category, "transform": row["transform"], "codec": row["codec"], "samples": 0, "total_frame_bytes": 0, "total_delta_same_coder_identity": 0, "total_delta_best_identity": 0, "same_coder_wins": 0, "same_coder_ties": 0})
        aggregate["samples"] += 1; aggregate["total_frame_bytes"] += row["frame_bytes"]
        aggregate["total_delta_same_coder_identity"] += row["delta_vs_same_coder_identity"]
        aggregate["total_delta_best_identity"] += row["delta_vs_best_identity"]
        aggregate["same_coder_wins"] += int(row["delta_vs_same_coder_identity"] < 0)
        aggregate["same_coder_ties"] += int(row["delta_vs_same_coder_identity"] == 0)
    result = {"identity": plan["identity"], "plan_sha256": sha(plan_bytes), "script_sha256": sha(Path(__file__).read_bytes()),
              "python": sys.version, "zlib": zlib.ZLIB_RUNTIME_VERSION, "input_count": len(records), "synthetic_roundtrip": "0..17 bytes, all transforms/codecs passed",
              "sources": source_rows, "aggregate": sorted(grouped.values(), key=lambda x: (x["category"], x["codec"], x["transform"])),
              "retained_frames": retained, "all_real_frame_roundtrips": True, "fresh_process_frame_decodes": len(retained), "elapsed_seconds": time.monotonic() - started}
    (HERE / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    report(result)


def report(result):
    lines = ["# Directional lanes / centre-out feasibility screen", "", "This fixed 9-window, 4 KiB screen measures complete DLV1 transport frames, not CIX archives. DLV1 charges transform, coder, stream-count and stream-length fields. No input-specific permutation or selection metadata is omitted.", "", "All byte lengths 0 through 17 passed each transform/coder round trip. All real candidate frames restored in process; retained frames also restored in fresh processes.", "", "## Best per fixed sample", "", "| Sample | Category | Best identity bytes | Best diagnostic frame | Delta |", "|---|---|---:|---|---:|"]
    for source in result["sources"]:
        b = source["best"]
        lines.append(f"| {source['id']} | {source['category']} | {source['best_identity_bytes']} | {b['transform']} + {b['codec']} ({b['frame_bytes']}) | {b['delta_vs_best_identity']:+d} |")
    lines += ["", "The best-per-sample column is an outcome-selected diagnostic. A production encoder needs a predeclared selection rule and must charge its decision; it is not a claimed codec gain.", "", "## Aggregate physical-frame deltas", "", "Deltas are summed over each category's fixed samples. A negative number is smaller. ‘Wins’ means strictly smaller than the matching identity frame under the same coder.", "", "| Category | Transform | Coder | Total frame bytes | Delta vs same-coder identity | Delta vs best identity | Wins/ties |", "|---|---|---|---:|---:|---:|---:|"]
    for row in result["aggregate"]:
        lines.append(f"| {row['category']} | {row['transform']} | {row['codec']} | {row['total_frame_bytes']} | {row['total_delta_same_coder_identity']:+d} | {row['total_delta_best_identity']:+d} | {row['same_coder_wins']}/{row['same_coder_ties']} |")
    lines += ["", "## Interpretation", "", "Reversal and centre-out are fixed permutations, so any physical change comes solely from the downstream coder's finite-context behaviour. Bit-lane partitioning is also reversible but changes coder history and incurs separate-stream framing where used. This screen only assesses the exact requested variants and does not establish that lane partition is new theory, beneficial to CIX, or representative of full files.", "", f"Evidence: `plan.json`, `results.json`; frame files are intentionally outside Git under `{WORK}`. Elapsed: {result['elapsed_seconds']:.3f}s; fresh process decodes: {result['fresh_process_frame_decodes']}."]
    (HERE / "REPORT.txt").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--decode")
    args = parser.parse_args()
    if args.decode:
        data = unframe(Path(args.decode).read_bytes())
        print(json.dumps({"bytes": len(data), "sha256": sha(data)}))
    else:
        run()


if __name__ == "__main__": main()
