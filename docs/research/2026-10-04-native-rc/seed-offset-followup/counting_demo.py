"""Finite mathematical witness, not a CIX codec or performance benchmark."""

import hashlib
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
N = 12
MASKS = (0, (1 << N) - 1, int("01" * (N // 2), 2), int("10" * (N // 2), 2))


def generated_window(seed, offset):
    digest = hashlib.sha256(b"CIX-seed-offset-toy-v1:" + bytes([seed])).digest()
    bits = "".join(f"{byte:08b}" for byte in digest)
    return int(bits[offset : offset + N], 2)


def decode(code):
    if code[0] == "0":
        assert len(code) == 1 + N
        return int(code[1:], 2)
    assert len(code) == 9
    seed = int(code[1:3], 2)
    offset = int(code[3:7], 2)
    mask = MASKS[int(code[7:9], 2)]
    return generated_window(seed, offset) ^ mask


def main():
    candidates = {}
    for seed in range(4):
        for offset in range(16):
            base = generated_window(seed, offset)
            for mask_index, mask in enumerate(MASKS):
                target = base ^ mask
                code = f"1{seed:02b}{offset:04b}{mask_index:02b}"
                candidates.setdefault(target, code)

    chosen = {}
    lengths = Counter()
    residual_weights = Counter()
    for target in range(1 << N):
        code = candidates.get(target, f"0{target:012b}")
        assert decode(code) == target
        assert code not in chosen
        chosen[code] = target
        lengths[len(code)] += 1
        if code[0] == "1":
            residual_weights[MASKS[int(code[7:9], 2)].bit_count()] += 1
    # Every generated word has the same length; raw words begin with the other tag.
    kraft = sum(Fraction(count, 1 << length) for length, count in lengths.items())
    assert kraft <= 1
    average = Fraction(sum(length * count for length, count in lengths.items()), 1 << N)
    assert average >= N

    sample_seed, sample_offset, sample_mask_index = 0, 0, 2
    sample_base = generated_window(sample_seed, sample_offset)
    sample_mask = MASKS[sample_mask_index]
    sample_target = sample_base ^ sample_mask
    sample_code = f"1{sample_seed:02b}{sample_offset:04b}{sample_mask_index:02b}"
    assert sample_mask.bit_count() == N // 2
    assert decode(sample_code) == sample_target

    # Exact counting, not a random-codebook measurement. If every n-bit target
    # must be within radius r of one of M codewords, M*V(n,r) >= 2**n.
    bounds = []
    for radius in (0, 10, 102, 256, 512):
        n = 1024
        volume = sum(math.comb(n, i) for i in range(radius + 1))
        residual_bits = math.log2(volume)
        bounds.append({
            "input_bits": n,
            "maximum_flips": radius,
            "log2_hamming_ball_volume": residual_bits,
            "log2_minimum_candidate_count_lower_bound": n - residual_bits,
            "sum": n,
            "meaning": "Necessary covering bound, not sufficient construction; fixed residual family includes all masks of weight at most radius. Headers and rounding omitted."
        })

    result = {
        "scope": "Exhaustive toy counting with exact reconstruction; no real corpus or CIX archive measurement",
        "plan_sha256": hashlib.sha256((ROOT / "plan.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_bits": N,
        "targets_examined": 1 << N,
        "seed_offset_choices": 64,
        "seed_offset_mask_descriptions": 256,
        "distinct_generated_targets": len(candidates),
        "chosen_code_length_histogram": dict(sorted(lengths.items())),
        "chosen_generated_residual_hamming_weights": dict(sorted(residual_weights.items())),
        "uniform_source_average_bits": float(average),
        "uniform_source_average_exact": str(average),
        "raw_control_bits": N,
        "uniform_source_average_change_percent": (float(average) / N - 1) * 100,
        "constructed_source_code_bits": 9,
        "constructed_source_saving_percent_vs_12_raw_bits": 25,
        "constructed_source_note": "Source restricted to the distinct generated targets; deliberately correlated positive control, no real-data claim",
        "all_targets_roundtrip": True,
        "unique_chosen_codewords": len(chosen),
        "prefix_code": True,
        "kraft_sum": str(kraft),
        "half_bits_changed_positive_example": {
            "generated_window": f"{sample_base:012b}",
            "target": f"{sample_target:012b}",
            "residual": f"{sample_mask:012b}",
            "encoded_bits": sample_code,
            "encoded_length": len(sample_code),
            "decoded_exactly": True
        },
        "hamming_covering_bounds": bounds,
        "limitations": "Tiny fixed-format bit codes omit length/alignment/framing. This is not an optimized compression scheme, corpus test, speed measurement, novelty proof or production feature."
    }
    output = json.dumps(result, indent=2) + "\n"
    (ROOT / "results.json").write_text(output)
    print(output)


if __name__ == "__main__":
    main()
