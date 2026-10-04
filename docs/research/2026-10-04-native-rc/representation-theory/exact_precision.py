"""Finite exact-precision checks; no floating-point or corpus compression."""

import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent
N = 12
LIMIT = 1 << N


def ceil_div(a, b):
    return (a + b - 1) // b


def integer_root(value, degree):
    if degree == 2:
        return math.isqrt(value)
    low, high = 0, 1 << ceil_div(value.bit_length(), degree)
    while low < high:
        middle = (low + high + 1) // 2
        if middle**degree <= value:
            low = middle
        else:
            high = middle - 1
    return low


def check_root(degree, precision):
    scale = 1 << (degree * precision)
    values = []
    integer_only = set()
    for target in range(LIMIT):
        integer_only.add(integer_root(target, degree))
        prefix = integer_root(target * scale, degree)
        # prefix <= 2^precision * root(target) < prefix+1.
        lower = ceil_div(prefix**degree, scale)
        upper = ceil_div((prefix + 1)**degree, scale) - 1
        assert lower == upper == target
        values.append(prefix)
    assert len(set(values)) == LIMIT
    return {
        "degree": degree,
        "input_count": LIMIT,
        "input_width_bits": N,
        "integer_only_distinct_outputs": len(integer_only),
        "integer_only_invertible": False,
        "fractional_precision_bits": precision,
        "exact_prefix_distinct_outputs": len(set(values)),
        "maximum_prefix_integer_bit_length": max(values).bit_length(),
        "exact_uniform_output_entropy_bits": N,
        "all_inverse_intervals_singleton": True,
        "qualification": "Conservative sufficient fixed precision, not minimal adaptive precision or optimized coding; generator/precision/length/framing costs not measured."
    }


def main():
    roots = [check_root(2, 7), check_root(3, 10)]
    reciprocal_precision = 2 * N
    scale = 1 << reciprocal_precision
    reciprocal = []
    full_width = []
    for target in range(1, LIMIT):
        prefix = scale // target
        lower = scale // (prefix + 1) + 1
        upper = scale // prefix
        assert lower == upper == target
        reciprocal.append(prefix)
        if target >= LIMIT // 2:
            full_width.append(prefix)
    assert len(set(reciprocal)) == LIMIT - 1
    assert len(set(full_width)) == LIMIT // 2

    square_codes = {}
    square_count = 0
    for target in range(LIMIT):
        root = math.isqrt(target)
        if root * root == target:
            code = f"1{root:06b}"
            decoded = int(code[1:], 2) ** 2
            square_count += 1
        else:
            code = f"0{target:012b}"
            decoded = int(code[1:], 2)
        assert decoded == target
        assert code not in square_codes
        square_codes[code] = target
    average = Fraction(sum(map(len, square_codes)), LIMIT)
    assert square_count == 64
    assert average >= N
    result = {
        "scope": "Exact finite integer calculations only, not corpus or CIX archive measurements",
        "plan_sha256": hashlib.sha256((ROOT / "plan.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "root_checks": roots,
        "reciprocal_check": {
            "inputs": "1 through 4095; zero excluded explicitly",
            "input_count": len(reciprocal),
            "fractional_precision_bits": reciprocal_precision,
            "distinct_prefixes": len(set(reciprocal)),
            "all_inverse_intervals_singleton": True,
            "full_width_subset": {
                "inputs": "2048 through 4095",
                "count": len(full_width),
                "uniform_information_bits": 11,
                "prefix_integer_min": min(full_width),
                "prefix_integer_max": max(full_width),
                "shortest_leading_zero_run_in_24_fractional_places": reciprocal_precision - max(full_width).bit_length(),
                "longest_leading_zero_run_in_24_fractional_places": reciprocal_precision - min(full_width).bit_length()
            },
            "qualification": "Precision is not encoded size. Leading zeros may be coded compactly; scale, precision and target length remain required or shared."
        },
        "perfect_square_positive_control": {
            "targets": LIMIT,
            "square_targets": square_count,
            "square_code_bits_including_tag": 7,
            "other_targets": LIMIT - square_count,
            "other_code_bits_including_tag": 13,
            "uniform_average_bits": float(average),
            "uniform_average_exact": str(average),
            "raw_control_bits": N,
            "all_targets_roundtrip": True,
            "qualification": "Source-specific savings exist; this toy is not an optimal code or evidence of real compressed assets being perfect powers."
        },
        "all_checks_passed": True
    }
    text = json.dumps(result, indent=2) + "\n"
    (ROOT / "results.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
