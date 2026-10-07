#!/usr/bin/env python3
"""Causal decoding-order diagnostic. ORV1 transport carries literal symbols."""
import hashlib
import json
import lzma
import math
import pathlib
import struct
import subprocess
import sys
import time
import zlib
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[3] / "benchmark-work/decoding-order-v1"
PATTERNS = [(-1,), (1,), (-2, -1), (1, 2), (-1, 1)]
NAMES = ["forward", "reverse", "fixed_anchors", "adaptive_anchors", "center_out"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Counts:
    def __init__(self):
        self.counts = Counter()
        self.total = 0
        self.mode = 0

    def add(self, value):
        self.counts[value] += 1
        self.total += 1
        a, b = self.counts[value], self.counts[self.mode]
        if a > b or (a == b and value < self.mode):
            self.mode = value


class Model:
    def __init__(self):
        self.global_counts = Counts()
        self.contexts = {}
        self.prediction_evaluations = 0

    def prediction(self, known, position):
        self.prediction_evaluations += 1
        assert known[position] is None
        selected, selected_id, rank = None, -1, None
        for index, offsets in enumerate(PATTERNS):
            places = [position + o for o in offsets]
            if any(p < 0 or p >= len(known) or known[p] is None for p in places):
                continue
            key = (index, tuple(known[p] for p in places))
            table = self.contexts.get(key)
            if table is None or table.total < 4:
                continue
            candidate_rank = (len(offsets), table.total, -index)
            if rank is None or candidate_rank > rank:
                selected, selected_id, rank = table, index, candidate_rank
        return Forecast(self.global_counts, selected, selected_id)

    def observe(self, known, position, value):
        assert known[position] is None
        known[position] = value
        self.global_counts.add(value)
        for index, offsets in enumerate(PATTERNS):
            for center in {position - o for o in (0,) + offsets}:
                places = [center] + [center + o for o in offsets]
                if any(p < 0 or p >= len(known) or known[p] is None for p in places):
                    continue
                key = (index, tuple(known[center + o] for o in offsets))
                self.contexts.setdefault(key, Counts()).add(known[center])


class Forecast:
    def __init__(self, global_counts, context, context_id):
        self.global_counts, self.context = global_counts, context
        self.context_id = context_id
        self.global_denominator = global_counts.total + 256
        self.denominator = self.global_denominator * (context.total + 8) if context else self.global_denominator

    def numerator(self, symbol):
        base = self.global_counts.counts[symbol] + 1
        return self.context.counts[symbol] * self.global_denominator + 8 * base if self.context else base

    def maximum(self):
        # Outside the context support, probability is a common multiple of the
        # global prior. Its mode plus all context-supported symbols suffice.
        symbols = {self.global_counts.mode}
        if self.context:
            symbols.update(self.context.counts)
        return max(self.numerator(x) for x in symbols), self.denominator


def fixed_order(length, mode):
    if mode == 0:
        return list(range(length))
    if mode == 1:
        return list(range(length - 1, -1, -1))
    if mode in (2, 3):
        anchors = sorted(set(range(0, length, 32)) | {length - 1})
        return anchors + ([x for x in range(length) if x not in anchors] if mode == 2 else [])
    left, right = (length - 1) // 2, (length - 1) // 2 + 1
    result = []
    while left >= 0 or right < length:
        if left >= 0:
            result.append(left)
            left -= 1
        if right < length:
            result.append(right)
            right += 1
    return result


def next_adaptive(model, known):
    winner, score, forecast = None, None, None
    for pos, value in enumerate(known):
        if value is not None:
            continue
        if pos > 0 and known[pos - 1] is None and pos + 1 < len(known) and known[pos + 1] is None:
            continue
        current = model.prediction(known, pos)
        numerator, denominator = current.maximum()
        if score is None or numerator * score[1] > score[0] * denominator:
            winner, score, forecast = pos, (numerator, denominator), current
    assert winner is not None
    return winner, forecast


def traverse(length, mode, original=None, transport=None):
    assert (original is None) != (transport is None)
    started = time.perf_counter()
    model = Model()
    recovered, wire = bytearray(length), bytearray()
    trace = hashlib.sha256()
    usage = Counter()
    loss = 0.0
    anchor_loss, anchor_count, cursor = 0.0, 0, 0
    for base in range(0, length, 256):
        size = min(256, length - base)
        known = [None] * size
        order = fixed_order(size, mode)
        anchors = set(fixed_order(size, 3)) if mode in (2, 3) else set()
        for step in range(size):
            if mode == 3 and step >= len(order):
                position, prediction = next_adaptive(model, known)
            else:
                position = order[step]
                prediction = model.prediction(known, position)
            # Target is read only after the schedule and distribution are fixed.
            actual = original[base + position] if original is not None else transport[cursor]
            numerator, denominator = prediction.numerator(actual), prediction.denominator
            assert 0 < numerator <= denominator
            bits = math.log2(denominator) - math.log2(numerator)
            loss += bits
            if position in anchors:
                anchor_loss += bits
                anchor_count += 1
            trace.update(struct.pack(">IBQQ", base + position, prediction.context_id + 1, numerator, denominator))
            usage[str(prediction.context_id)] += 1
            wire.append(actual)
            recovered[base + position] = actual
            model.observe(known, position, actual)
            cursor += 1
        assert all(value is not None for value in known)
    return bytes(recovered), bytes(wire), {
        "order": NAMES[mode], "ideal_bits": loss,
        "bits_per_input_byte": loss / length if length else 0,
        "anchor_ideal_bits_included": anchor_loss, "anchor_symbols": anchor_count,
        "context_usage": dict(usage), "prediction_evaluations": model.prediction_evaluations,
        "context_table_count": len(model.contexts), "trace_sha256": trace.hexdigest(),
        "wall_seconds": time.perf_counter() - started,
    }


def decode_literal_frame(frame):
    assert frame[:4] == b"ORV1" and len(frame) >= 9
    length, mode = struct.unpack(">IB", frame[4:9])
    assert mode < 5 and len(frame) == length + 9
    restored, _, metrics = traverse(length, mode, transport=frame[9:])
    return restored, metrics


def synthetic_checks():
    model = Model()
    for _ in range(16):
        for left in (0, 1):
            for right in (0, 1):
                known = [None] * 3
                for pos, value in enumerate((left, left ^ right, right)):
                    model.observe(known, pos, value)
    total, table_count = model.global_counts.total, len(model.contexts)
    query = [0, None, 1]
    pred = model.prediction(query, 1)
    assert pred.context_id == 4
    assert sum(pred.numerator(x) for x in range(256)) == pred.denominator
    assert pred.numerator(1) * pred.global_denominator > (model.global_counts.counts[1] + 1) * pred.denominator
    assert query == [0, None, 1] and total == model.global_counts.total and table_count == len(model.contexts)
    fixtures = [("zero", bytes(1024)), ("alternating", bytes([0, 1]) * 512),
                ("pseudorandom", hashlib.shake_256(b"CIX-order-null-v1").digest(1024))]
    rows = []
    for name, data in fixtures:
        for mode in range(5):
            restored, wire, metrics = traverse(len(data), mode, original=data)
            frame = b"ORV1" + struct.pack(">IB", len(data), mode) + wire
            decoded, replay = decode_literal_frame(frame)
            assert restored == decoded == data
            assert replay["trace_sha256"] == metrics["trace_sha256"]
            rows.append({"fixture": name, "order": NAMES[mode], "ideal_bits": metrics["ideal_bits"]})
    for n in range(18):
        data = bytes(range(n))
        for mode in range(5):
            restored, wire, _ = traverse(n, mode, original=data)
            assert restored == data
            assert decode_literal_frame(b"ORV1" + struct.pack(">IB", n, mode) + wire)[0] == data
    return {"xor_context_normalization_and_causality": True,
            "xor_target_probability": pred.numerator(1) / pred.denominator,
            "fixture_rows": rows, "short_lengths_all_orders_roundtrip": True}


def run():
    started = time.perf_counter()
    plan = json.loads((HERE / "plan-amendment.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    assert not list(OUT.glob("*.orv")), "preserve prior output"
    result = {"plan_sha256": sha((HERE / "plan-amendment.json").read_bytes()),
              "script_sha256": sha(pathlib.Path(__file__).read_bytes()),
              "scope": "Ideal predictive bits; literal replay transports are not compressed archives",
              "synthetic": synthetic_checks(), "samples": []}
    print("synthetic checks passed", flush=True)
    for sample in plan["inputs"]:
        with open(sample["path"], "rb") as stream:
            stream.seek(sample["offset"])
            data = stream.read(sample["bytes"])
        assert sha(data) == sample["sample_sha256"]
        rows = []
        for mode in range(5):
            restored, wire, metrics = traverse(len(data), mode, original=data)
            assert restored == data
            frame = b"ORV1" + struct.pack(">IB", len(data), mode) + wire
            path = OUT / (sample["id"] + "-" + NAMES[mode] + ".orv")
            restored_path = path.with_suffix(".restored")
            path.write_bytes(frame)
            completed = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                "decode", str(path), str(restored_path)], check=True, capture_output=True, text=True)
            receipt = json.loads(completed.stdout)
            assert receipt["sha256"] == sample["sample_sha256"]
            assert receipt["trace_sha256"] == metrics["trace_sha256"]
            assert restored_path.read_bytes() == data
            restored_path.unlink()
            metrics["literal_transport_bytes_NOT_compressed"] = len(frame)
            metrics["literal_transport_path"] = str(path)
            metrics["literal_transport_sha256"] = sha(frame)
            metrics["fresh_replay"] = receipt
            rows.append(metrics)
        result["samples"].append({"source": sample, "orders": rows,
            "ordinary_coder_payload_bytes_separate_from_ideal_loss": {
                "zlib9": len(zlib.compress(data, 9)), "xz1": len(lzma.compress(data, preset=1))}})
        (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"sample": sample["id"], "ideal_bits": {x["order"]: x["ideal_bits"] for x in rows}}), flush=True)
    standard = [s for s in result["samples"] if s["source"]["family"] == "standard-corpus"]
    totals = {name: sum(s["orders"][i]["ideal_bits"] for s in standard) for i, name in enumerate(NAMES)}
    adaptive_baseline = min(totals[name] for name in NAMES if name != "adaptive_anchors")
    directional = min(totals["forward"], totals["reverse"])
    gates = {}
    for name in ("adaptive_anchors", "fixed_anchors", "center_out"):
        i = NAMES.index(name)
        control_names = [n for n in NAMES if n != name] if name == "adaptive_anchors" else ["forward", "reverse"]
        baseline = adaptive_baseline if name == "adaptive_anchors" else directional
        wins = sum(s["orders"][i]["ideal_bits"] < min(s["orders"][NAMES.index(n)]["ideal_bits"] for n in control_names) for s in standard)
        gain = baseline - totals[name]
        gates[name] = {"baseline_ideal_bits": baseline, "gain_ideal_bits": gain,
                       "gain_percent": 100 * gain / baseline, "individual_wins": wins,
                       "pass": gain >= 0.01 * baseline and wins >= 3}
    result["standard_sample_totals_ideal_bits"] = totals
    result["standard_bytes"] = sum(s["source"]["bytes"] for s in standard)
    result["gates"] = gates
    result["fresh_real_replay_count"] = 30
    result["elapsed_seconds"] = time.perf_counter() - started
    (HERE / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"gates": gates, "seconds": result["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "decode":
        value, metrics = decode_literal_frame(pathlib.Path(sys.argv[2]).read_bytes())
        pathlib.Path(sys.argv[3]).write_bytes(value)
        print(json.dumps({"sha256": sha(value), "bytes": len(value), "trace_sha256": metrics["trace_sha256"]}))
    else:
        run()
