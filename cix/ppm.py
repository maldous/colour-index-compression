"""Native Prediction-by-Partial-Matching model for CIX.

Format-agnostic causal PPM with exclusion and selectable escape estimators. The encoder
may physically try several generic escape laws and store the winning law in the block;
the decoder needs no semantic information or trained model.
"""
from __future__ import annotations

import math
from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

PPM_VERSION = 2
CONTEXT_LIMIT = 16384

ESCAPE_ONE = 0
ESCAPE_DISTINCT = 1
ESCAPE_HALF_DISTINCT = 2
ESCAPE_SINGLETONS = 3
ESCAPE_METHODS = (
    ESCAPE_ONE,
    ESCAPE_DISTINCT,
    ESCAPE_HALF_DISTINCT,
    ESCAPE_SINGLETONS,
)


def _ctx(history: bytearray, order: int) -> bytes:
    return bytes(history[-order:]) if order else b""


def _rescale(counts: dict[int, int]) -> None:
    if sum(counts.values()) <= CONTEXT_LIMIT:
        return
    for symbol in list(counts):
        counts[symbol] = max(1, (counts[symbol] + 1) // 2)


def _eligible(counts: dict[int, int] | None, excluded: set[int]) -> list[int]:
    if not counts:
        return []
    return [symbol for symbol in sorted(counts) if symbol not in excluded]


def _escape_mass(
    counts: dict[int, int],
    symbols: list[int],
    method: int,
) -> int:
    if method == ESCAPE_ONE:
        return 1
    if method == ESCAPE_DISTINCT:
        return max(1, len(symbols))
    if method == ESCAPE_HALF_DISTINCT:
        return max(1, (len(symbols) + 1) // 2)
    if method == ESCAPE_SINGLETONS:
        return max(1, sum(1 for symbol in symbols if counts[symbol] == 1))
    raise ValueError("unknown PPM escape method")


def estimate_ppm_bits(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
    escape_method: int = ESCAPE_DISTINCT,
) -> float:
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")
    if escape_method not in ESCAPE_METHODS:
        raise ValueError("invalid PPM escape method")

    sample = data[:sample_limit]
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    bits = 0.0

    for symbol in sample:
        excluded: set[int] = set()
        coded = False
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.get(context)
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            mass = sum(counts[s] for s in symbols)
            escape = _escape_mass(counts, symbols, escape_method)
            total = mass + escape

            if symbol in counts and symbol not in excluded:
                bits += math.log2(total) - math.log2(counts[symbol])
                coded = True
                break

            bits += math.log2(total) - math.log2(escape)
            excluded.update(symbols)

        if not coded:
            bits += math.log2(max(1, 256 - len(excluded)))

        highest = min(max_order, len(history))
        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.setdefault(context, {})
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    if not sample:
        return 0.0
    return bits * (len(data) / len(sample))


def _encode_ppm_method(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes,
    escape_method: int,
) -> bytes:
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    encoder = _ArithmeticEncoder()

    for symbol in data:
        excluded: set[int] = set()
        coded = False
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.get(context)
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            mass = sum(counts[s] for s in symbols)
            escape = _escape_mass(counts, symbols, escape_method)
            total = mass + escape

            if symbol in counts and symbol not in excluded:
                low = 0
                for candidate in symbols:
                    high = low + counts[candidate]
                    if candidate == symbol:
                        encoder.encode(low, high, total)
                        coded = True
                        break
                    low = high
                if coded:
                    break
            else:
                encoder.encode(mass, total, total)
                excluded.update(symbols)

        if not coded:
            remaining = [s for s in range(256) if s not in excluded]
            rank = remaining.index(symbol)
            encoder.encode(rank, rank + 1, len(remaining))

        highest = min(max_order, len(history))
        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.setdefault(context, {})
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    payload, bit_length = encoder.finish()
    return (
        bytes((PPM_VERSION, max_order, escape_method))
        + vencode(bit_length)
        + payload
    )


def encode_ppm(
    data: bytes,
    *,
    max_order: int = 4,
    prefix_history: bytes = b"",
    escape_method: int | None = None,
) -> bytes:
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")
    if escape_method is not None:
        if escape_method not in ESCAPE_METHODS:
            raise ValueError("invalid PPM escape method")
        return _encode_ppm_method(
            data,
            max_order=max_order,
            prefix_history=prefix_history,
            escape_method=escape_method,
        )

    # Exact MDL selection: try all generic escape laws and retain physical minimum.
    return min(
        (
            _encode_ppm_method(
                data,
                max_order=max_order,
                prefix_history=prefix_history,
                escape_method=method,
            )
            for method in ESCAPE_METHODS
        ),
        key=len,
    )


def decode_ppm(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 3 or blob[0] != PPM_VERSION:
        raise ValueError("unknown PPM version")
    max_order = blob[1]
    escape_method = blob[2]
    if not 0 <= max_order <= 8:
        raise ValueError("invalid PPM order")
    if escape_method not in ESCAPE_METHODS:
        raise ValueError("invalid PPM escape method")

    bit_length, pos = vdecode(blob, 3)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("PPM payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    out = bytearray()

    for _ in range(source_length):
        excluded: set[int] = set()
        symbol = None
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.get(context)
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            mass = sum(counts[s] for s in symbols)
            escape = _escape_mass(counts, symbols, escape_method)
            total = mass + escape
            target = decoder.target(total)

            if target < mass:
                low = 0
                for candidate in symbols:
                    high = low + counts[candidate]
                    if target < high:
                        decoder.update(low, high, total)
                        symbol = candidate
                        break
                    low = high
                if symbol is None:
                    raise ValueError("PPM symbol interval not found")
                break

            decoder.update(mass, total, total)
            excluded.update(symbols)

        if symbol is None:
            remaining = [s for s in range(256) if s not in excluded]
            target = decoder.target(len(remaining))
            if not 0 <= target < len(remaining):
                raise ValueError("PPM fallback target outside alphabet")
            symbol = remaining[target]
            decoder.update(target, target + 1, len(remaining))

        out.append(symbol)

        highest = min(max_order, len(history))
        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.setdefault(context, {})
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    return bytes(out)
