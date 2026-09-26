"""Online format-agnostic context-expert arithmetic model.

Several byte-context orders predict in parallel. A deterministic exponentially decayed
log-loss score selects the currently best expert before each symbol. Because the score is
computed only from already-decoded bytes, encoder and decoder choose the same expert
without transmitting per-symbol model IDs.
"""

from __future__ import annotations

import math

from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

EXPERT_VERSION = 1
CONTEXT_LIMIT = 4096
DECAY = 0.98


def _context(history: bytearray, order: int) -> bytes:
    return bytes(history[-order:]) if order else b""


def _rescale(counts: dict[int, int]) -> None:
    if sum(counts.values()) <= CONTEXT_LIMIT:
        return
    for symbol in list(counts):
        counts[symbol] = max(1, (counts[symbol] + 1) // 2)


def _interval(counts: dict[int, int] | None, symbol: int) -> tuple[int, int, int]:
    if counts is None:
        return symbol, symbol + 1, 256
    low = symbol
    for candidate, count in counts.items():
        if candidate < symbol:
            low += count
    high = low + counts.get(symbol, 0) + 1
    total = sum(counts.values()) + 256
    return low, high, total


def _decode_symbol(
    decoder: _ArithmeticDecoder,
    counts: dict[int, int] | None,
) -> int:
    total = (sum(counts.values()) if counts else 0) + 256
    target = decoder.target(total)
    cumulative = 0
    for symbol in range(256):
        frequency = (counts.get(symbol, 0) if counts else 0) + 1
        high = cumulative + frequency
        if target < high:
            decoder.update(cumulative, high, total)
            return symbol
        cumulative = high
    raise ValueError("context-expert target outside alphabet")


def _update_loss(
    loss: float,
    counts: dict[int, int] | None,
    symbol: int,
) -> float:
    observed = counts.get(symbol, 0) if counts else 0
    total = (sum(counts.values()) if counts else 0) + 256
    symbol_mass = observed + 1
    instantaneous = math.log2(total) - math.log2(symbol_mass)
    return loss * DECAY + instantaneous


def estimate_expert_bits(
    data: bytes,
    *,
    orders: tuple[int, ...] = (0, 1, 2, 4),
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
) -> float:
    """Estimate switching-expert log loss without emitting a bitstream."""
    orders = tuple(sorted(set(orders)))
    if not orders or orders[0] != 0 or any(not 0 <= order <= 8 for order in orders):
        raise ValueError("expert orders must include 0 and lie in 0..8")

    sample = data[:sample_limit]
    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[bytes, dict[int, int]]] = [dict() for _ in orders]
    losses = [0.0] * len(orders)
    bits = 0.0

    for symbol in sample:
        contexts = [_context(history, order) for order in orders]
        counts_list = [
            tables[index].get(context)
            for index, context in enumerate(contexts)
        ]
        selected = min(range(len(orders)), key=lambda index: (losses[index], index))
        counts = counts_list[selected]
        observed = counts.get(symbol, 0) if counts else 0
        total = (sum(counts.values()) if counts else 0) + 256
        bits += math.log2(total) - math.log2(observed + 1)

        for index, model_counts in enumerate(counts_list):
            losses[index] = _update_loss(losses[index], model_counts, symbol)

        for index, context in enumerate(contexts):
            model_counts = tables[index].get(context)
            if model_counts is None:
                model_counts = {}
                tables[index][context] = model_counts
            model_counts[symbol] = model_counts.get(symbol, 0) + 1
            _rescale(model_counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    if not sample:
        return 0.0
    return bits * (len(data) / len(sample))


def encode_expert_mix(
    data: bytes,
    *,
    orders: tuple[int, ...] = (0, 1, 2, 4),
    prefix_history: bytes = b"",
) -> bytes:
    orders = tuple(sorted(set(orders)))
    if not orders or orders[0] != 0 or any(not 0 <= order <= 8 for order in orders):
        raise ValueError("expert orders must include 0 and lie in 0..8")

    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[bytes, dict[int, int]]] = [dict() for _ in orders]
    losses = [0.0] * len(orders)
    encoder = _ArithmeticEncoder()

    for symbol in data:
        contexts = [_context(history, order) for order in orders]
        counts_list = [
            tables[index].get(context)
            for index, context in enumerate(contexts)
        ]
        selected = min(range(len(orders)), key=lambda index: (losses[index], index))
        low, high, total = _interval(counts_list[selected], symbol)
        encoder.encode(low, high, total)

        for index, counts in enumerate(counts_list):
            losses[index] = _update_loss(losses[index], counts, symbol)

        for index, context in enumerate(contexts):
            counts = tables[index].get(context)
            if counts is None:
                counts = {}
                tables[index][context] = counts
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    payload, bit_length = encoder.finish()
    out = bytearray((EXPERT_VERSION, len(orders)))
    out.extend(orders)
    out += vencode(bit_length)
    out += payload
    return bytes(out)


def decode_expert_mix(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 2 or blob[0] != EXPERT_VERSION:
        raise ValueError("unknown context-expert version")

    count = blob[1]
    if not 1 <= count <= 9 or len(blob) < 2 + count:
        raise ValueError("invalid context-expert order count")
    orders = tuple(blob[2 : 2 + count])
    if tuple(sorted(set(orders))) != orders or orders[0] != 0 or orders[-1] > 8:
        raise ValueError("invalid context-expert orders")

    bit_length, pos = vdecode(blob, 2 + count)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("context-expert payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    max_order = max(orders)
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    tables: list[dict[bytes, dict[int, int]]] = [dict() for _ in orders]
    losses = [0.0] * len(orders)
    out = bytearray()

    for _ in range(source_length):
        contexts = [_context(history, order) for order in orders]
        counts_list = [
            tables[index].get(context)
            for index, context in enumerate(contexts)
        ]
        selected = min(range(len(orders)), key=lambda index: (losses[index], index))
        symbol = _decode_symbol(decoder, counts_list[selected])
        out.append(symbol)

        for index, counts in enumerate(counts_list):
            losses[index] = _update_loss(losses[index], counts, symbol)

        for index, context in enumerate(contexts):
            counts = tables[index].get(context)
            if counts is None:
                counts = {}
                tables[index][context] = counts
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    return bytes(out)
