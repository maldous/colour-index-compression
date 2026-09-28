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
PPM_STANDARD_VERSION = 3
PPM_UPDATE_EXCLUSION_VERSION = 4
PPM_SEE_VERSION = 5
SEE_PRIOR_ESCAPE = 1
SEE_PRIOR_HIT = 2
SEE_RESCALE_LIMIT = 256
CONTEXT_LIMIT = 16384
PPM_HISTORY_MAX = 65536
PPM_HISTORY_MIN = 4096

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


def _see_key(
    order: int,
    counts: dict[int, int],
    symbols: list[int],
) -> tuple[int, int, int]:
    """Coarse secondary context for adaptive escape estimation."""
    total = sum(counts[symbol] for symbol in symbols)
    distinct_bucket = min(7, max(1, len(symbols)).bit_length() - 1)
    total_bucket = min(15, max(1, total).bit_length() - 1)
    return order, distinct_bucket, total_bucket


def _see_state(
    states: dict[tuple[int, int, int], tuple[int, int]],
    key: tuple[int, int, int],
) -> tuple[int, int]:
    return states.get(key, (SEE_PRIOR_ESCAPE, SEE_PRIOR_HIT))


def _see_update(
    states: dict[tuple[int, int, int], tuple[int, int]],
    key: tuple[int, int, int],
    *,
    escaped: bool,
) -> None:
    escape_count, hit_count = _see_state(states, key)
    if escaped:
        escape_count += 1
    else:
        hit_count += 1
    if escape_count + hit_count > SEE_RESCALE_LIMIT:
        escape_count = max(1, (escape_count + 1) // 2)
        hit_count = max(1, (hit_count + 1) // 2)
    states[key] = (escape_count, hit_count)


def _observe_symbol(
    tables: dict[bytes, dict[int, int]],
    history: bytearray,
    symbol: int,
    max_order: int,
    *,
    min_order: int = 0,
) -> None:
    highest = min(max_order, len(history))
    min_order = max(0, min(min_order, highest))
    for order in range(highest, min_order - 1, -1):
        context = _ctx(history, order)
        counts = tables.setdefault(context, {})
        counts[symbol] = counts.get(symbol, 0) + 1
        _rescale(counts)

    if max_order:
        history.append(symbol)
        if len(history) > max_order:
            del history[:-max_order]


def _update_floor(
    tables: dict[bytes, dict[int, int]],
    history: bytearray,
    symbol: int,
    max_order: int,
) -> int:
    """Lowest order to update under PPM update exclusion.

    If the symbol is predicted by order k, orders below k are not updated.
    A novel symbol (order -1 fallback) updates all available contexts.
    """
    highest = min(max_order, len(history))
    for order in range(highest, -1, -1):
        counts = tables.get(_ctx(history, order))
        if counts and symbol in counts:
            return order
    return 0


def _prime_from_history(
    prefix_history: bytes,
    block_length: int,
    max_order: int,
    *,
    update_exclusion: bool = False,
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
        floor = (
            _update_floor(tables, history, symbol, max_order)
            if update_exclusion
            else 0
        )
        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=floor,
        )

    return tables, history


def _prime_see_from_history(
    prefix_history: bytes,
    block_length: int,
    max_order: int,
    *,
    update_exclusion: bool,
) -> tuple[
    dict[bytes, dict[int, int]],
    bytearray,
    dict[tuple[int, int, int], tuple[int, int]],
]:
    """Warm both PPM counts and secondary escape statistics from history."""
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray()
    states: dict[tuple[int, int, int], tuple[int, int]] = {}
    if not prefix_history:
        return tables, history, states

    training_length = min(
        len(prefix_history),
        PPM_HISTORY_MAX,
        max(PPM_HISTORY_MIN, block_length * 2),
    )
    start = len(prefix_history) - training_length
    if max_order and start:
        history.extend(prefix_history[max(0, start - max_order) : start])

    for symbol in prefix_history[start:]:
        excluded: set[int] = set()
        matched_order = 0
        highest = min(max_order, len(history))
        for order in range(highest, -1, -1):
            counts = tables.get(_ctx(history, order))
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue
            assert counts is not None
            key = _see_key(order, counts, symbols)
            hit = symbol in counts and symbol not in excluded
            _see_update(states, key, escaped=not hit)
            if hit:
                matched_order = order
                break
            excluded.update(symbols)

        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    return tables, history, states


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
    update_exclusion: bool = False,
) -> float:
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")
    if escape_method not in ESCAPE_METHODS:
        raise ValueError("invalid PPM escape method")

    sample = data[:sample_limit]
    if not sample:
        return 0.0

    tables, history = _prime_from_history(
        prefix_history,
        len(data),
        max_order,
        update_exclusion=update_exclusion,
    )
    bits = 0.0

    for symbol in sample:
        excluded: set[int] = set()
        coded = False
        matched_order = 0
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
                matched_order = order
                break

            bits += math.log2(total) - math.log2(escape)
            excluded.update(symbols)

        if not coded:
            bits += math.log2(max(1, 256 - len(excluded)))

        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    return bits * (len(data) / len(sample))



def _estimate_ppm_portfolio_variant_bits(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes,
    sample_limit: int,
    update_exclusion: bool,
) -> float:
    """Estimate all active escape models for one update policy in one shared pass."""
    sample = data[:sample_limit]
    if not sample:
        return 0.0

    tables, history, states = _prime_see_from_history(
        prefix_history,
        len(data),
        max_order,
        update_exclusion=update_exclusion,
    )
    fixed_bits = {method: 0.0 for method in ESCAPE_METHODS}
    see_bits = 0.0

    for symbol in sample:
        excluded: set[int] = set()
        coded = False
        matched_order = 0
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            counts = tables.get(_ctx(history, order))
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            mass = sum(counts[s] for s in symbols)
            key = _see_key(order, counts, symbols)
            escape_count, hit_count = _see_state(states, key)
            event_total = escape_count + hit_count
            hit = symbol in counts and symbol not in excluded

            if hit:
                count = counts[symbol]
                for method in ESCAPE_METHODS:
                    escape = _escape_mass(counts, symbols, method)
                    fixed_bits[method] += math.log2(mass + escape) - math.log2(count)
                see_bits += math.log2(event_total) - math.log2(hit_count)
                see_bits += math.log2(mass) - math.log2(count)
                _see_update(states, key, escaped=False)
                coded = True
                matched_order = order
                break

            for method in ESCAPE_METHODS:
                escape = _escape_mass(counts, symbols, method)
                fixed_bits[method] += math.log2(mass + escape) - math.log2(escape)
            see_bits += math.log2(event_total) - math.log2(escape_count)
            _see_update(states, key, escaped=True)
            excluded.update(symbols)

        if not coded:
            fallback = math.log2(max(1, 256 - len(excluded)))
            for method in ESCAPE_METHODS:
                fixed_bits[method] += fallback
            see_bits += fallback

        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    scale = len(data) / len(sample)
    return min(min(fixed_bits.values()), see_bits) * scale


def estimate_ppm_portfolio_bits(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
) -> float:
    """Estimate the best currently encodable PPM variant for order selection."""
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")
    if sample_limit <= 0:
        raise ValueError("sample_limit must be positive")
    if not data:
        return 0.0

    return min(
        _estimate_ppm_portfolio_variant_bits(
            data,
            max_order=max_order,
            prefix_history=prefix_history,
            sample_limit=sample_limit,
            update_exclusion=update_exclusion,
        )
        for update_exclusion in (False, True)
    )

def _encode_ppm_method(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes,
    escape_method: int,
    update_exclusion: bool,
    initial_state: tuple[dict[bytes, dict[int, int]], bytearray] | None = None,
    max_bytes: int | None = None,
) -> bytes | None:
    if initial_state is None:
        tables, history = _prime_from_history(
            prefix_history, len(data), max_order,
            update_exclusion=update_exclusion,
        )
    else:
        # Escape laws share the same training statistics. Clone once per law;
        # never let a candidate mutate another candidate's starting model.
        tables = {context: counts.copy() for context, counts in initial_state[0].items()}
        history = initial_state[1].copy()
    encoder = _ArithmeticEncoder()

    for index, symbol in enumerate(data):
        if max_bytes is not None and index % 256 == 0:
            bits = encoder.writer.bit_length
            if 3 + len(vencode(bits)) + (bits + 7) // 8 >= max_bytes:
                return None
        excluded: set[int] = set()
        coded = False
        matched_order = 0
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
                        matched_order = order
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

        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    payload, bit_length = encoder.finish()
    version = (
        PPM_UPDATE_EXCLUSION_VERSION
        if update_exclusion
        else PPM_STANDARD_VERSION
    )
    return (
        bytes((version, max_order, escape_method))
        + vencode(bit_length)
        + payload
    )



def _encode_ppm_see(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes,
    update_exclusion: bool,
    max_bytes: int | None = None,
) -> bytes | None:
    tables, history, states = _prime_see_from_history(
        prefix_history,
        len(data),
        max_order,
        update_exclusion=update_exclusion,
    )
    encoder = _ArithmeticEncoder()

    for index, symbol in enumerate(data):
        if max_bytes is not None and index % 256 == 0:
            bits = encoder.writer.bit_length
            if 3 + len(vencode(bits)) + (bits + 7) // 8 >= max_bytes:
                return None
        excluded: set[int] = set()
        coded = False
        matched_order = 0
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            counts = tables.get(_ctx(history, order))
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            key = _see_key(order, counts, symbols)
            escape_count, hit_count = _see_state(states, key)
            event_total = escape_count + hit_count
            hit = symbol in counts and symbol not in excluded

            if hit:
                encoder.encode(0, hit_count, event_total)
                mass = sum(counts[s] for s in symbols)
                low = 0
                for candidate in symbols:
                    high = low + counts[candidate]
                    if candidate == symbol:
                        encoder.encode(low, high, mass)
                        coded = True
                        matched_order = order
                        break
                    low = high
                _see_update(states, key, escaped=False)
                break

            encoder.encode(hit_count, event_total, event_total)
            _see_update(states, key, escaped=True)
            excluded.update(symbols)

        if not coded:
            remaining = [s for s in range(256) if s not in excluded]
            rank = remaining.index(symbol)
            encoder.encode(rank, rank + 1, len(remaining))

        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    payload, bit_length = encoder.finish()
    flags = 1 if update_exclusion else 0
    return bytes((PPM_SEE_VERSION, max_order, flags)) + vencode(bit_length) + payload


def _decode_ppm_see(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes,
) -> bytes:
    if len(blob) < 3 or blob[0] != PPM_SEE_VERSION:
        raise ValueError("invalid PPM SEE payload")
    max_order = blob[1]
    flags = blob[2]
    if not 0 <= max_order <= 8 or flags & ~1:
        raise ValueError("invalid PPM SEE header")
    update_exclusion = bool(flags & 1)

    bit_length, pos = vdecode(blob, 3)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("PPM SEE payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    tables, history, states = _prime_see_from_history(
        prefix_history,
        source_length,
        max_order,
        update_exclusion=update_exclusion,
    )
    out = bytearray()

    for _ in range(source_length):
        excluded: set[int] = set()
        symbol = None
        matched_order = 0
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            counts = tables.get(_ctx(history, order))
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            key = _see_key(order, counts, symbols)
            escape_count, hit_count = _see_state(states, key)
            event_total = escape_count + hit_count
            target = decoder.target(event_total)

            if target < hit_count:
                decoder.update(0, hit_count, event_total)
                mass = sum(counts[s] for s in symbols)
                symbol_target = decoder.target(mass)
                low = 0
                for candidate in symbols:
                    high = low + counts[candidate]
                    if symbol_target < high:
                        decoder.update(low, high, mass)
                        symbol = candidate
                        matched_order = order
                        break
                    low = high
                if symbol is None:
                    raise ValueError("PPM SEE symbol interval not found")
                _see_update(states, key, escaped=False)
                break

            decoder.update(hit_count, event_total, event_total)
            _see_update(states, key, escaped=True)
            excluded.update(symbols)

        if symbol is None:
            remaining = [s for s in range(256) if s not in excluded]
            target = decoder.target(len(remaining))
            if not 0 <= target < len(remaining):
                raise ValueError("PPM SEE fallback outside alphabet")
            symbol = remaining[target]
            decoder.update(target, target + 1, len(remaining))

        out.append(symbol)
        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    return bytes(out)


def encode_ppm(
    data: bytes,
    *,
    max_order: int = 4,
    prefix_history: bytes = b"",
    escape_method: int | None = None,
    update_exclusion: bool | None = None,
    secondary_escape: bool | None = None,
) -> bytes:
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")
    if escape_method is not None and escape_method not in ESCAPE_METHODS:
        raise ValueError("invalid PPM escape method")

    variants = (
        (False, True)
        if update_exclusion is None
        else (update_exclusion,)
    )
    methods = (
        (escape_method,)
        if escape_method is not None
        else ESCAPE_METHODS
    )

    # Exact physical selection: incumbent escape laws remain available and
    # secondary escape estimation is an additional reversible competitor.
    best: bytes | None = None
    if secondary_escape is not True:
        for variant in variants:
            initial = _prime_from_history(
                prefix_history, len(data), max_order, update_exclusion=variant,
            )
            for method in methods:
                candidate = _encode_ppm_method(
                    data, max_order=max_order, prefix_history=prefix_history,
                    escape_method=method, update_exclusion=variant,
                    initial_state=initial, max_bytes=len(best) if best is not None else None,
                )
                if candidate is not None and (best is None or len(candidate) < len(best)):
                    best = candidate
    if secondary_escape is not False:
        for variant in variants:
            candidate = _encode_ppm_see(
                data, max_order=max_order, prefix_history=prefix_history,
                update_exclusion=variant, max_bytes=len(best) if best is not None else None,
            )
            if candidate is not None and (best is None or len(candidate) < len(best)):
                best = candidate
    if best is None:
        raise ValueError("no PPM variants requested")
    return best


def decode_ppm(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 3:
        raise ValueError("truncated PPM payload")
    if blob[0] == PPM_SEE_VERSION:
        return _decode_ppm_see(
            blob,
            source_length=source_length,
            prefix_history=prefix_history,
        )
    if blob[0] not in (
        2,
        PPM_STANDARD_VERSION,
        PPM_UPDATE_EXCLUSION_VERSION,
    ):
        raise ValueError("unknown PPM version")

    version = blob[0]
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
    update_exclusion = version == PPM_UPDATE_EXCLUSION_VERSION
    if version == 2:
        tables, history = _fresh_legacy_state(prefix_history, max_order)
    else:
        tables, history = _prime_from_history(
            prefix_history,
            source_length,
            max_order,
            update_exclusion=update_exclusion,
        )

    out = bytearray()

    for _ in range(source_length):
        excluded: set[int] = set()
        symbol = None
        matched_order = 0
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
                        matched_order = order
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
        _observe_symbol(
            tables,
            history,
            symbol,
            max_order,
            min_order=matched_order if update_exclusion else 0,
        )

    return bytes(out)
