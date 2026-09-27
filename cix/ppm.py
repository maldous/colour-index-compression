"""Native Prediction-by-Partial-Matching model for CIX.

Format-agnostic causal PPM with exclusion, selectable escape estimators, and deterministic
recent-history warmup. Encoder and decoder already share previously decoded bytes, so v3
uses a bounded suffix of that history to train context statistics before coding each
block. This preserves streaming while avoiding destructive model resets at block edges.
"""
from __future__ import annotations

import math
from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

PPM_VERSION = 4
CONTEXT_LIMIT = 16384
PPM_HISTORY_MAX = 65536
PPM_HISTORY_MIN = 4096

ESCAPE_ONE = 0
ESCAPE_DISTINCT = 1
ESCAPE_HALF_DISTINCT = 2
ESCAPE_SINGLETONS = 3
ESCAPE_LEARNED = 4
ESCAPE_METHODS = (
    ESCAPE_ONE,
    ESCAPE_DISTINCT,
    ESCAPE_HALF_DISTINCT,
    ESCAPE_SINGLETONS,
    ESCAPE_LEARNED,
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
    *,
    escapes: int = 0,
    hits: int = 0,
) -> int:
    if method == ESCAPE_ONE:
        return 1
    if method == ESCAPE_DISTINCT:
        return max(1, len(symbols))
    if method == ESCAPE_HALF_DISTINCT:
        return max(1, (len(symbols) + 1) // 2)
    if method == ESCAPE_SINGLETONS:
        return max(1, sum(1 for symbol in symbols if counts[symbol] == 1))
    if method == ESCAPE_LEARNED:
        mass = sum(counts[symbol] for symbol in symbols)
        numerator = mass * (escapes + 1)
        denominator = hits + 2
        learned = (numerator + denominator // 2) // denominator
        return max(1, min(2 * len(symbols), learned))
    raise ValueError("unknown PPM escape method")


def _update_reliability(
    reliability: dict[bytes, list[int]],
    context: bytes,
    *,
    escaped: bool,
) -> None:
    state = reliability.setdefault(context, [0, 0])
    state[0 if escaped else 1] += 1
    if state[0] + state[1] > CONTEXT_LIMIT:
        state[0] = (state[0] + 1) // 2
        state[1] = (state[1] + 1) // 2


def _observe_symbol(
    tables: dict[bytes, dict[int, int]],
    history: bytearray,
    symbol: int,
    max_order: int,
) -> None:
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


def _prime_from_history(
    prefix_history: bytes,
    block_length: int,
    max_order: int,
) -> tuple[dict[bytes, dict[int, int]], bytearray]:
    """Train a fresh block model from a deterministic recent-history suffix.

    The horizon scales with block size but is bounded. The few bytes immediately
    preceding the training suffix seed the first training contexts without themselves
    contributing counts.
    """
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray()
    if not prefix_history:
        return tables, history

    training_length = min(
        len(prefix_history),
        PPM_HISTORY_MAX,
        max(PPM_HISTORY_MIN, block_length * 2),
    )
    start = len(prefix_history) - training_length

    if max_order and start:
        history.extend(prefix_history[max(0, start - max_order) : start])

    for symbol in prefix_history[start:]:
        _observe_symbol(tables, history, symbol, max_order)

    return tables, history


def _fresh_legacy_state(
    prefix_history: bytes,
    max_order: int,
) -> tuple[dict[bytes, dict[int, int]], bytearray]:
    """PPM v2 behaviour retained for old payload decoding."""
    return {}, bytearray(prefix_history[-max_order:] if max_order else b"")


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
    if not sample:
        return 0.0

    tables, history = _prime_from_history(
        prefix_history, len(data), max_order
    )
    reliability: dict[bytes, list[int]] = {}
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
            escapes, hits = reliability.get(context, (0, 0))
            escape = _escape_mass(
                counts, symbols, escape_method, escapes=escapes, hits=hits
            )
            total = mass + escape

            if symbol in counts and symbol not in excluded:
                bits += math.log2(total) - math.log2(counts[symbol])
                if escape_method == ESCAPE_LEARNED:
                    _update_reliability(reliability, context, escaped=False)
                coded = True
                break

            bits += math.log2(total) - math.log2(escape)
            if escape_method == ESCAPE_LEARNED:
                _update_reliability(reliability, context, escaped=True)
            excluded.update(symbols)

        if not coded:
            bits += math.log2(max(1, 256 - len(excluded)))

        _observe_symbol(tables, history, symbol, max_order)

    return bits * (len(data) / len(sample))


def _encode_ppm_method(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes,
    escape_method: int,
) -> bytes:
    tables, history = _prime_from_history(
        prefix_history, len(data), max_order
    )
    reliability: dict[bytes, list[int]] = {}
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
            escapes, hits = reliability.get(context, (0, 0))
            escape = _escape_mass(
                counts, symbols, escape_method, escapes=escapes, hits=hits
            )
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
                    if escape_method == ESCAPE_LEARNED:
                        _update_reliability(reliability, context, escaped=False)
                    break
            else:
                encoder.encode(mass, total, total)
                if escape_method == ESCAPE_LEARNED:
                    _update_reliability(reliability, context, escaped=True)
                excluded.update(symbols)

        if not coded:
            remaining = [s for s in range(256) if s not in excluded]
            rank = remaining.index(symbol)
            encoder.encode(rank, rank + 1, len(remaining))

        _observe_symbol(tables, history, symbol, max_order)

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
    if len(blob) < 3 or blob[0] not in (2, 3, PPM_VERSION):
        raise ValueError("unknown PPM version")

    version = blob[0]
    max_order = blob[1]
    escape_method = blob[2]
    if not 0 <= max_order <= 8:
        raise ValueError("invalid PPM order")
    if escape_method not in ESCAPE_METHODS:
        raise ValueError("invalid PPM escape method")
    if escape_method == ESCAPE_LEARNED and version < 4:
        raise ValueError("learned PPM escape requires version 4")

    bit_length, pos = vdecode(blob, 3)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("PPM payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    if version == 2:
        tables, history = _fresh_legacy_state(prefix_history, max_order)
    else:
        tables, history = _prime_from_history(
            prefix_history, source_length, max_order
        )

    out = bytearray()
    reliability: dict[bytes, list[int]] = {}

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
            escapes, hits = reliability.get(context, (0, 0))
            escape = _escape_mass(
                counts, symbols, escape_method, escapes=escapes, hits=hits
            )
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
                if escape_method == ESCAPE_LEARNED:
                    _update_reliability(reliability, context, escaped=False)
                break

            decoder.update(mass, total, total)
            if escape_method == ESCAPE_LEARNED:
                _update_reliability(reliability, context, escaped=True)
            excluded.update(symbols)

        if symbol is None:
            remaining = [s for s in range(256) if s not in excluded]
            target = decoder.target(len(remaining))
            if not 0 <= target < len(remaining):
                raise ValueError("PPM fallback target outside alphabet")
            symbol = remaining[target]
            decoder.update(target, target + 1, len(remaining))

        out.append(symbol)
        _observe_symbol(tables, history, symbol, max_order)

    return bytes(out)
