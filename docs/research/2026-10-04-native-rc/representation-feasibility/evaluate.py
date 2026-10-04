#!/usr/bin/env python3
"""Exact finite-grammar feasibility screen; no corpus, CIX route or floats in coding."""

import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAMILIES = ("raw", "rational", "power", "generated", "direct_mask")


def gamma(value):
    assert value > 0
    binary = f"{value:b}"
    return "0" * (len(binary) - 1) + binary


def mask(n, index):
    return (0, (1 << n) - 1, int("01" * (n // 2), 2),
            int("10" * (n // 2), 2))[index]


def generated(n, seed, offset):
    size = (n + offset + 7) // 8
    data = hashlib.shake_256(b"CIX-feasibility-v1:" + bytes([seed])).digest(size)
    return (int.from_bytes(data, "big") >> (8 * size - offset - n)) & ((1 << n) - 1)


def root_floor(value, exponent):
    lo, hi = 0, 1 << ((value.bit_length() + exponent - 1) // exponent)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid ** exponent <= value:
            lo = mid
        else:
            hi = mid
    return lo


def signed(value):
    return "0" if value == 0 else "1" + str(int(value < 0)) + gamma(abs(value))


def best(codes):
    return min(codes, key=lambda code: (len(code), code))


def retain(table, value, code):
    old = table.get(value)
    if old is None or (len(code), code) < (len(old), old):
        table[value] = code


def build_tables(n, targets=None):
    start = time.perf_counter()
    rationals, generated_codes, masks = {}, {}, {}
    examined = retained_reduced = pruned_denominators = 0
    for q in range(1, 1024):
        w = q.bit_length()
        if 2 + len(gamma(w)) + 2 * w > n + 1:
            pruned_denominators += 1
            continue
        for p in range(q):
            examined += 1
            if math.gcd(p, q) != 1:
                continue
            retained_reduced += 1
            value = ((1 << n) * p) // q
            if targets is None or value in targets:
                retain(rationals, value, "10" + gamma(w) + f"{p:0{w}b}{q:0{w}b}")
    rational_seconds = time.perf_counter() - start
    start = time.perf_counter()
    for seed in range(4):
        for offset in range(16):
            value = generated(n, seed, offset)
            for index in range(4):
                retain(generated_codes, value ^ mask(n, index),
                       f"1110{seed:02b}{offset:04b}{index:02b}")
    generator_seconds = time.perf_counter() - start
    for index in range(4):
        retain(masks, mask(n, index), f"1111{index:02b}")
    count = len(generated_codes)
    return (rationals, generated_codes, masks), {
        "rational_pairs_examined_before_gcd": examined,
        "rational_reduced_pairs": retained_reduced,
        "rational_denominators_pruned_by_mandatory_size": pruned_denominators,
        "rational_targets_retained": len(rationals),
        "rational_table_seconds": rational_seconds,
        "generator_descriptions": 256,
        "generator_distinct_targets": count,
        "generator_table_seconds": generator_seconds,
        "generator_dictionary_ideal_rank_bits": math.log2(count),
        "generator_dictionary_fixed_rank_bits": (count - 1).bit_length(),
        "generator_direct_mask_overlap_targets": len(set(generated_codes) & set(masks)),
    }


def candidates(value, n, tables):
    result = {"raw": "0" + f"{value:0{n}b}"}
    codes = []
    for k in range(2, 6):
        width = (n + k - 1) // k
        lower = root_floor(value, k)
        assert lower ** k <= value < (lower + 1) ** k
        for a in (lower, lower + 1):
            if a < (1 << width):
                codes.append("110" + f"{k-2:02b}{a:0{width}b}" + signed(value - a ** k))
    result["power"] = best(codes)
    for family, table in zip(("rational", "generated", "direct_mask"), tables):
        if value in table:
            result[family] = table[value]
    return result


def encode(n, code):
    bits = gamma(n) + code
    padded = bits + "0" * (-len(bits) % 8)
    return int(padded, 2).to_bytes(len(padded) // 8, "big"), len(bits)


class Reader:
    def __init__(self, data):
        self.bits = "".join(f"{byte:08b}" for byte in data)
        self.pos = 0

    def take(self, count):
        if count <= 0 or self.pos + count > len(self.bits):
            raise ValueError("truncated frame")
        result = int(self.bits[self.pos:self.pos + count], 2)
        self.pos += count
        return result

    def gamma(self):
        width = 0
        while self.take(1) == 0:
            width += 1
        return (1 << width) | (self.take(width) if width else 0)


def decode(data):
    reader = Reader(data)
    n = reader.gamma()
    if n not in (16, 256):
        raise ValueError("length outside this frozen screen")
    if reader.take(1) == 0:
        value = reader.take(n)
    elif reader.take(1) == 0:
        w = reader.gamma()
        p, q = reader.take(w), reader.take(w)
        if not (0 <= p < q and q.bit_length() == w and math.gcd(p, q) == 1):
            raise ValueError("invalid rational")
        value = ((1 << n) * p) // q
    elif reader.take(1) == 0:
        k = reader.take(2) + 2
        a = reader.take((n + k - 1) // k)
        d = 0
        if reader.take(1):
            negative = reader.take(1)
            d = reader.gamma() * (-1 if negative else 1)
        value = a ** k + d
    elif reader.take(1) == 0:
        seed, offset, index = reader.take(2), reader.take(4), reader.take(2)
        value = generated(n, seed, offset) ^ mask(n, index)
    else:
        value = mask(n, reader.take(2))
    if not 0 <= value < (1 << n):
        raise ValueError("decoded value out of range")
    if len(reader.bits) - reader.pos >= 8 or "1" in reader.bits[reader.pos:]:
        raise ValueError("noncanonical or nonzero padding")
    return n, value


def select(options, excluded=None):
    return min((item for item in options.items() if item[0] != excluded),
               key=lambda item: (len(item[1]), item[1]))


def exhaustive():
    n = 16
    tables, setup = build_tables(n)
    header = len(gamma(n))
    count = 1 << n
    histogram_bits, histogram_bytes, selected = Counter(), Counter(), Counter()
    standalone_bits, standalone_bytes = Counter(), Counter()
    leave_out_bits, leave_out_bytes = Counter(), Counter()
    frame_hash, restored_hash = hashlib.sha256(), hashlib.sha256()
    total_bits = total_bytes = kraft_units = 0
    for value in range(count):
        options = candidates(value, n, tables)
        family, code = select(options)
        frame, length = encode(n, code)
        assert decode(frame) == (n, value)
        frame_hash.update(len(frame).to_bytes(2, "big") + frame)
        restored_hash.update(value.to_bytes(2, "big"))
        histogram_bits[length] += 1
        histogram_bytes[len(frame)] += 1
        selected[family] += 1
        total_bits += length
        total_bytes += len(frame)
        kraft_units += 1 << (n + 1 - len(code))
        for family in FAMILIES:
            one = best([options["raw"], options.get(family, options["raw"])])
            standalone_bits[family] += header + len(one)
            standalone_bytes[family] += (header + len(one) + 7) // 8
            if family != "raw":
                _, other = select(options, excluded=family)
                leave_out_bits[family] += header + len(other)
                leave_out_bytes[family] += (header + len(other) + 7) // 8
    assert kraft_units <= (1 << (n + 1))
    return {
        "n": n, "cases": count, "all_selected_frames_roundtrip": True,
        "setup": setup, "selected_by_family": dict(selected),
        "meaningful_bits_histogram": dict(sorted(histogram_bits.items())),
        "padded_bytes_histogram": dict(sorted(histogram_bytes.items())),
        "total_meaningful_bits": total_bits, "total_padded_bytes": total_bytes,
        "mean_meaningful_bits": total_bits / count,
        "mean_suffix_bits_excluding_common_length_header": total_bits / count - header,
        "mean_padded_bytes": total_bytes / count,
        "literal_input_bytes": count * 2,
        "raw_frame_meaningful_bits_each": header + n + 1,
        "raw_frame_bytes_each": (header + n + 8) // 8,
        "raw_frame_total_padded_bytes": count * ((header + n + 8) // 8),
        "conditional_selected_code_kraft_numerator": kraft_units,
        "conditional_selected_code_kraft_denominator": 1 << (n + 1),
        "standalone_with_raw_total_meaningful_bits": dict(standalone_bits),
        "standalone_with_raw_total_padded_bytes": dict(standalone_bytes),
        "leave_one_family_out_total_meaningful_bits": dict(leave_out_bits),
        "leave_one_family_out_total_padded_bytes": dict(leave_out_bytes),
        "marginal_bits_contributed": {k: v - total_bits for k, v in leave_out_bits.items()},
        "marginal_bytes_contributed": {k: v - total_bytes for k, v in leave_out_bytes.items()},
        "selected_frames_sha256_length_delimited": frame_hash.hexdigest(),
        "restored_inputs_sha256": restored_hash.hexdigest(),
    }


def constructed():
    n = 256
    a, b = (1 << 127) + 37, (1 << 85) + 27
    inputs = [("mask_" + str(i), mask(n, i)) for i in range(4)] + [
        ("square_exact", a * a), ("square_plus_3", a * a + 3),
        ("cube_exact", b ** 3), ("cube_minus_5", b ** 3 - 5),
        ("rational_257_over_509", (257 << n) // 509),
        ("generated_seed2_offset7", generated(n, 2, 7)),
        ("generated_seed2_offset7_mask01", generated(n, 2, 7) ^ mask(n, 2)),
    ]
    inputs += [("null_sha256_" + str(i), int.from_bytes(hashlib.sha256(
        b"CIX-feasibility-null-v1:" + bytes([i])).digest(), "big")) for i in range(4)]
    tables, setup = build_tables(n, targets={value for _, value in inputs})
    rows = []
    rejection_checks = 0
    for name, value in inputs:
        assert 0 <= value < (1 << n)
        options = candidates(value, n, tables)
        family, code = select(options)
        frame, length = encode(n, code)
        assert decode(frame) == (n, value)
        for candidate in options.values():
            candidate_frame, _ = encode(n, candidate)
            assert decode(candidate_frame) == (n, value)
        invalid_frames = [frame + b"\0", frame[:-1]]
        if length % 8:
            invalid_frames.append(frame[:-1] + bytes([frame[-1] | 1]))
        for invalid in invalid_frames:
            try:
                decode(invalid)
            except ValueError:
                rejection_checks += 1
            else:
                raise AssertionError("invalid frame accepted: " + name)
        costs = {}
        for key in FAMILIES:
            candidate = options.get(key)
            candidate_frame, candidate_length = encode(n, candidate) if candidate is not None else (None, None)
            costs[key] = {"meaningful_bits": candidate_length,
                          "padded_bytes": len(candidate_frame) if candidate_frame is not None else None}
        marginal = {}
        for key in FAMILIES[1:]:
            _, other = select(options, excluded=key)
            other_frame, other_length = encode(n, other)
            marginal[key] = {"meaningful_bits": other_length - length,
                             "padded_bytes": len(other_frame) - len(frame)}
        rows.append({"case": name, "input_hex": f"{value:064x}",
                     "selected_family": family, "meaningful_bits": length,
                     "padded_bytes": len(frame), "frame_hex": frame.hex(),
                     "input_bytes": 32, "family_costs": costs,
                     "leave_one_family_out_penalty": marginal})
    return {"n": n, "setup": setup, "cases": rows,
            "all_selected_and_available_family_frames_roundtrip": True,
            "malformed_frame_rejection_checks": rejection_checks}


def main():
    started = time.perf_counter()
    result = {
        "scope": "Exact finite mathematical frames, not CIX archives or real-data qualification",
        "plan_sha256": hashlib.sha256((HERE / "plan.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "selection_ties": "lexicographic among evaluated minimum-length candidates",
        "exhaustive_n16": exhaustive(), "constructed_and_null_n256": constructed(),
    }
    result["elapsed_seconds"] = time.perf_counter() - started
    (HERE / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "roundtrip_inputs": 65551,
                      "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
