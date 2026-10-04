"""Small exact algebra/counting calculations, not a compression benchmark."""

import hashlib
import json
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def step(state, tap):
    return (state >> 1) | (((state ^ (state >> tap)) & 1) << 3)


def output(state, tap, phase=0, length=64):
    for _ in range(phase):
        state = step(state, tap)
    value = 0
    for _ in range(length):
        value = (value << 1) | (state & 1)
        state = step(state, tap)
    return value


def period(state, tap):
    original = state
    for length in range(1, 17):
        state = step(state, tap)
        if state == original:
            return length
    raise AssertionError("state failed to return within finite state bound")


def main():
    first = [output(seed, 1) for seed in range(16)]
    second = [output(seed, 3) for seed in range(16)]
    same_pairs = {a ^ b for a in first for b in first}
    different_pairs = {a ^ b for a in first for b in second}
    phases = {output(seed, 1, phase) for seed in range(16) for phase in range(15)}
    for a in range(16):
        for b in range(16):
            assert first[a] ^ first[b] == first[a ^ b]
    assert phases == set(first) == same_pairs
    assert len(different_pairs) == 256
    period_values = {str(tap): [period(seed, tap) for seed in range(16)] for tap in (1, 3)}
    assert all(values == [1] + [15] * 15 for values in period_values.values())

    pair_models = []
    for seed_bits in (32, 64):
        target_bits = 128
        entries = 1 << seed_bits
        expected = Fraction(entries * entries, 1 << target_bits)
        pair_models.append({
            "target_bits": target_bits,
            "seed_bits_each": seed_bits,
            "two_seed_bits_without_framing": 2 * seed_bits,
            "entries_per_list": entries,
            "nominal_pair_candidates": entries * entries,
            "ideal_expected_exact_matches": str(expected),
            "ideal_probability_upper_bound": str(min(Fraction(1), expected)),
            "one_list_vectors_only_bytes": entries * (target_bits // 8),
            "excluded_memory": "Seed labels, hash table, allocation overhead and second-list buffering",
            "assumption": "Two independent lists of uniformly random target-width vectors; fixed target. Not a measurement or claim of independence for actual PRNG windows."
        })

    result = {
        "scope": "Exact finite algebra and closed-form counting only",
        "plan_sha256": hashlib.sha256((ROOT / "plan.json").read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "prefix_code_uniform_source_saving_bounds": [
            {"saving_bits": gain, "probability_upper_bound": str(Fraction(1, 1 << gain))}
            for gain in (8, 16, 32, 64)
        ],
        "linear_recurrence": {
            "state_bits": 4,
            "output_bits": 64,
            "period_by_seed_and_tap": period_values,
            "single_family_unique_outputs": len(set(first)),
            "seed_phase_descriptions": 16 * 15,
            "seed_phase_unique_outputs": len(phases),
            "same_family_seed_pair_descriptions": 256,
            "same_family_pair_unique_outputs": len(same_pairs),
            "different_family_seed_pair_descriptions": 256,
            "different_family_pair_unique_outputs": len(different_pairs),
            "same_family_xor_equals_xored_seed_for_all_pairs": True,
            "limitation": "Toy linear recurrences, not high-quality random generators; no real-data or strong-compressor comparison."
        },
        "two_list_xor_search_models": pair_models,
        "production_changes": False,
        "corpus_access": False
    }
    text = json.dumps(result, indent=2) + "\n"
    (ROOT / "results.json").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
