"""Deterministic bitwise context mixing for universal CIX.

The model works entirely on bytes already decoded. For each bit it combines several
context-order predictors using integer likelihood weights. Current-byte prefix bits are
part of every context, which lets the binary model learn arbitrary byte alphabets without
format-specific knowledge.

No selector stream is stored: decoder state deterministically reproduces expert contexts,
weights and updates.
"""

from __future__ import annotations

import math

from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

MIXER_VERSION = 1
PROB_SCALE = 1 << 15
COUNT_LIMIT = 4096
WEIGHT_SCALE = 1 << 14


def _context_key(
    history: bytearray,
    order: int,
    bit_pos: int,
    prefix: int,
) -> tuple[bytes, int, int]:
    context = bytes(history[-order:]) if order else b""
    return context, bit_pos, prefix


def _probability(counts: list[int] | None) -> int:
    if counts is None:
        return PROB_SCALE // 2
    zero, one = counts
    total = zero + one + 2
    value = ((one + 1) * PROB_SCALE) // total
    return min(PROB_SCALE - 1, max(1, value))


def _update_counts(counts: list[int], bit: int) -> None:
    counts[bit] += 1
    if counts[0] + counts[1] > COUNT_LIMIT:
        counts[0] = max(0, counts[0] // 2)
        counts[1] = max(0, counts[1] // 2)


def _mixed_probability(probabilities: list[int], weights: list[int]) -> int:
    total_weight = sum(weights)
    if total_weight <= 0:
        return PROB_SCALE // 2
    mixed = sum(p * w for p, w in zip(probabilities, weights)) // total_weight
    return min(PROB_SCALE - 1, max(1, mixed))


def _update_weights(
    weights: list[int],
    probabilities: list[int],
    bit: int,
) -> None:
    # Likelihood ratio around p=0.5: a calibrated 0.5 predictor keeps its weight;
    # better predictors grow relative to worse predictors.
    for index, probability in enumerate(probabilities):
        likelihood = probability if bit else PROB_SCALE - probability
        weights[index] = max(
            1,
            (weights[index] * likelihood) // (PROB_SCALE // 2),
        )

    # Keep integer magnitudes bounded without changing relative ranking much.
    maximum = max(weights)
    if maximum > (1 << 24):
        for index, weight in enumerate(weights):
            weights[index] = max(1, weight >> 8)


def estimate_mixer_bits(
    data: bytes,
    *,
    orders: tuple[int, ...] = (0, 1, 2, 4),
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
) -> float:
    orders = tuple(sorted(set(orders)))
    if not orders or orders[0] != 0 or any(order < 0 or order > 8 for order in orders):
        raise ValueError("mixer orders must include 0 and lie in 0..8")

    sample = data[:sample_limit]
    if not sample:
        return 0.0

    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[tuple[bytes, int, int], list[int]]] = [
        {} for _ in orders
    ]
    weights = [WEIGHT_SCALE] * len(orders)
    bits = 0.0

    for byte in sample:
        prefix = 0
        for bit_pos in range(8):
            bit = (byte >> (7 - bit_pos)) & 1
            keys = [
                _context_key(history, order, bit_pos, prefix)
                for order in orders
            ]
            counts_list = [
                tables[index].get(key)
                for index, key in enumerate(keys)
            ]
            probabilities = [_probability(counts) for counts in counts_list]
            mixed = _mixed_probability(probabilities, weights)
            mass = mixed if bit else PROB_SCALE - mixed
            bits += math.log2(PROB_SCALE) - math.log2(mass)

            _update_weights(weights, probabilities, bit)
            for index, key in enumerate(keys):
                counts = tables[index].get(key)
                if counts is None:
                    counts = [0, 0]
                    tables[index][key] = counts
                _update_counts(counts, bit)

            prefix = (prefix << 1) | bit

        if max_order:
            history.append(byte)
            if len(history) > max_order:
                del history[:-max_order]

    return bits * (len(data) / len(sample))


def encode_mixer(
    data: bytes,
    *,
    orders: tuple[int, ...] = (0, 1, 2, 4),
    prefix_history: bytes = b"",
) -> bytes:
    orders = tuple(sorted(set(orders)))
    if not orders or orders[0] != 0 or any(order < 0 or order > 8 for order in orders):
        raise ValueError("mixer orders must include 0 and lie in 0..8")

    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[tuple[bytes, int, int], list[int]]] = [
        {} for _ in orders
    ]
    weights = [WEIGHT_SCALE] * len(orders)
    encoder = _ArithmeticEncoder()

    for byte in data:
        prefix = 0
        for bit_pos in range(8):
            bit = (byte >> (7 - bit_pos)) & 1
            keys = [
                _context_key(history, order, bit_pos, prefix)
                for order in orders
            ]
            counts_list = [
                tables[index].get(key)
                for index, key in enumerate(keys)
            ]
            probabilities = [_probability(counts) for counts in counts_list]
            mixed = _mixed_probability(probabilities, weights)

            if bit:
                encoder.encode(PROB_SCALE - mixed, PROB_SCALE, PROB_SCALE)
            else:
                encoder.encode(0, PROB_SCALE - mixed, PROB_SCALE)

            _update_weights(weights, probabilities, bit)
            for index, key in enumerate(keys):
                counts = tables[index].get(key)
                if counts is None:
                    counts = [0, 0]
                    tables[index][key] = counts
                _update_counts(counts, bit)

            prefix = (prefix << 1) | bit

        if max_order:
            history.append(byte)
            if len(history) > max_order:
                del history[:-max_order]

    payload, bit_length = encoder.finish()
    out = bytearray((MIXER_VERSION, len(orders)))
    out.extend(orders)
    out += vencode(bit_length)
    out += payload
    return bytes(out)


def decode_mixer(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 2 or blob[0] != MIXER_VERSION:
        raise ValueError("unknown mixer version")

    count = blob[1]
    if not 1 <= count <= 9 or len(blob) < 2 + count:
        raise ValueError("invalid mixer order count")
    orders = tuple(blob[2 : 2 + count])
    if tuple(sorted(set(orders))) != orders or orders[0] != 0 or orders[-1] > 8:
        raise ValueError("invalid mixer orders")

    bit_length, pos = vdecode(blob, 2 + count)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("mixer payload length mismatch")

    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[tuple[bytes, int, int], list[int]]] = [
        {} for _ in orders
    ]
    weights = [WEIGHT_SCALE] * len(orders)
    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    out = bytearray()

    for _ in range(source_length):
        byte = 0
        prefix = 0
        for bit_pos in range(8):
            keys = [
                _context_key(history, order, bit_pos, prefix)
                for order in orders
            ]
            counts_list = [
                tables[index].get(key)
                for index, key in enumerate(keys)
            ]
            probabilities = [_probability(counts) for counts in counts_list]
            mixed = _mixed_probability(probabilities, weights)
            zero_mass = PROB_SCALE - mixed
            target = decoder.target(PROB_SCALE)

            if target < zero_mass:
                bit = 0
                decoder.update(0, zero_mass, PROB_SCALE)
            else:
                bit = 1
                decoder.update(zero_mass, PROB_SCALE, PROB_SCALE)

            _update_weights(weights, probabilities, bit)
            for index, key in enumerate(keys):
                counts = tables[index].get(key)
                if counts is None:
                    counts = [0, 0]
                    tables[index][key] = counts
                _update_counts(counts, bit)

            byte = (byte << 1) | bit
            prefix = (prefix << 1) | bit

        out.append(byte)
        if max_order:
            history.append(byte)
            if len(history) > max_order:
                del history[:-max_order]

    return bytes(out)
