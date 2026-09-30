"""Generic reversible byte-column coding for the Wikipedia D2 ablation.

This deliberately has no page parser, numeric normalization, or text policy.
Callers provide only already-eligible byte values.  A column is either literal,
or pays its sorted byte palette and complete counts before using the same
remaining-count arithmetic or exact rank order model.
"""
from __future__ import annotations

from cix.multinomial import vdecode, vencode
from benchmarks.mysql_record_constraints import order_decode, order_encode

MAGIC = b"WCOL1"
RAW, REMAINING, RANK = 0, 1, 2
MAX_DISTINCT, MIN_VALUES, MAX_VALUE_BYTES, MAX_GROUP_VALUES = 256, 4, 1 << 20, 1024


def _pack(value: bytes) -> bytes:
    return vencode(len(value)) + value


def _read(blob: bytes, pos: int) -> tuple[bytes, int]:
    length, pos = vdecode(blob, pos); end = pos + length
    if end > len(blob): raise ValueError("truncated column value")
    return blob[pos:end], end


def _raw(values: list[bytes]) -> bytes:
    return b"".join(_pack(value) for value in values)


def _eligible(values: list[bytes]) -> tuple[bool, str | None]:
    if len(values) < MIN_VALUES: return False, "too_few_values"
    if len(values) > MAX_GROUP_VALUES: return False, "group_too_large"
    if any(len(value) >= MAX_VALUE_BYTES for value in values): return False, "long_value"
    if len(set(values)) > MAX_DISTINCT: return False, "too_many_distinct"
    return True, None


def encode(values: list[bytes], mode: str = "raw") -> tuple[bytes, dict]:
    if mode not in ("raw", "remaining", "rank"): raise ValueError("invalid column mode")
    if any(not isinstance(value, bytes) for value in values): raise TypeError("values must be bytes")
    raw_payload = _raw(values); raw_frame = MAGIC + bytes([RAW]) + vencode(len(values)) + raw_payload
    eligible, reason = _eligible(values)
    selector = RAW; actual = "raw"; palette_bytes = count_bytes = order_bytes = 0; order_kind = None
    payload = raw_payload
    if mode != "raw" and eligible:
        palette = sorted(set(values)); counts = [values.count(value) for value in palette]
        ids = [palette.index(value) for value in values]
        selector = REMAINING if mode == "remaining" else RANK
        # Both non-literal candidates receive exactly the same paid palette,
        # counts and one whole-column partition. The only difference is order coding.
        body = bytearray(vencode(len(palette)))
        for value, count in zip(palette, counts):
            before = len(body); body.extend(_pack(value)); palette_bytes += len(body) - before
            before = len(body); body.extend(vencode(count)); count_bytes += len(body) - before
        ordering = order_encode(ids, counts, 3 if selector == REMAINING else 4)
        order_bytes = len(ordering); order_kind = ordering[0]; body.extend(_pack(ordering)); payload = bytes(body); actual = mode
    frame = MAGIC + bytes([selector]) + vencode(len(values)) + payload
    literal_payload_bytes = len(raw_payload) if selector == RAW else 0
    framing_bytes = len(frame) - literal_payload_bytes - palette_bytes - count_bytes - order_bytes
    stats = {"requested_mode": mode, "actual_mode": actual, "eligible": eligible, "fallback_reason": reason,
             "values": len(values), "distinct": len(set(values)), "raw_payload_bytes": len(raw_payload),
             "raw_physical_bytes": len(raw_frame), "literal_payload_bytes": literal_payload_bytes,
             "palette_bytes": palette_bytes, "count_bytes": count_bytes, "order_bytes": order_bytes,
             "order_kind": order_kind, "framing_bytes": framing_bytes,
             "physical_bytes": len(frame), "selector": selector}
    if sum(stats[key] for key in ("literal_payload_bytes", "palette_bytes", "count_bytes", "order_bytes", "framing_bytes")) != len(frame):
        raise AssertionError("column physical accounting mismatch")
    return frame, stats


def decode(blob: bytes, n: int) -> list[bytes]:
    if not blob.startswith(MAGIC) or len(blob) <= len(MAGIC): raise ValueError("invalid column frame")
    selector = blob[len(MAGIC)]; count, pos = vdecode(blob, len(MAGIC) + 1)
    if count != n: raise ValueError("column length mismatch")
    if selector == RAW:
        out = []
        for _ in range(n): value, pos = _read(blob, pos); out.append(value)
    elif selector in (REMAINING, RANK):
        if n > MAX_GROUP_VALUES: raise ValueError("coded column group too large")
        distinct, pos = vdecode(blob, pos)
        if not 1 <= distinct <= MAX_DISTINCT: raise ValueError("invalid palette size")
        palette, counts = [], []
        for _ in range(distinct):
            value, pos = _read(blob, pos); amount, pos = vdecode(blob, pos)
            if not amount: raise ValueError("zero count")
            palette.append(value); counts.append(amount)
        if palette != sorted(palette) or len(set(palette)) != len(palette) or sum(counts) != n: raise ValueError("invalid palette/counts")
        ordering, pos = _read(blob, pos); ids = order_decode(ordering, counts)
        out = [palette[index] for index in ids]
    else: raise ValueError("invalid selector")
    if pos != len(blob): raise ValueError("trailing column bytes")
    return out
