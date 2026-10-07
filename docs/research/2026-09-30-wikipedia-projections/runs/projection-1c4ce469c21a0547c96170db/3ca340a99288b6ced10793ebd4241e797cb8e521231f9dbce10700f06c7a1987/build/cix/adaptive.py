"""Adaptive multinomial coding.

This is the online Bayesian dual to the explicit CIX type-class representation. Instead
of transmitting a block histogram, each symbol is arithmetic-coded using a symmetric
Dirichlet-1/2 prior:

    P(symbol=s) = (count_s + 1/2) / (seen + 256/2)

Using integer frequencies this is exactly:

    freq_s = 2*count_s + 1
    total  = 2*seen + 256

No probability table is transmitted. Encoder and decoder update the same counts. A
deterministic context hash creates independent adaptive multinomial models per context
bucket.
"""

from __future__ import annotations

from dataclasses import dataclass

from .multinomial import (
    Fenwick,
    _ArithmeticDecoder,
    _ArithmeticEncoder,
    _context_bucket,
    vdecode,
    vencode,
)

ADAPTIVE_VERSION = 1


@dataclass
class _Model:
    counts: list[int]
    fenwick: Fenwick
    seen: int = 0

    @classmethod
    def create(cls) -> "_Model":
        counts = [0] * 256
        return cls(counts, Fenwick(counts), 0)

    @property
    def total(self) -> int:
        return 2 * self.seen + 256

    def interval(self, symbol: int) -> tuple[int, int, int]:
        low = 2 * self.fenwick.prefix(symbol) + symbol
        high = low + 2 * self.counts[symbol] + 1
        return low, high, self.total

    def select(self, target: int) -> tuple[int, int, int, int]:
        # Find greatest symbol whose interval start is <= target.
        lo = 0
        hi = 255
        while lo < hi:
            mid = (lo + hi + 1) // 2
            start = 2 * self.fenwick.prefix(mid) + mid
            if start <= target:
                lo = mid
            else:
                hi = mid - 1

        symbol = lo
        low, high, total = self.interval(symbol)
        if not low <= target < high:
            raise ValueError("adaptive multinomial target outside interval")
        return symbol, low, high, total

    def update(self, symbol: int) -> None:
        self.counts[symbol] += 1
        self.fenwick.add(symbol, 1)
        self.seen += 1


def _bucket(
    tail: bytearray,
    order: int,
    bucket_bits: int,
) -> int:
    if order == 0:
        return 0
    return _context_bucket(tail, order, bucket_bits)


def encode_adaptive(
    data: bytes,
    *,
    order: int = 0,
    bucket_bits: int = 8,
    prefix_history: bytes = b"",
) -> bytes:
    if not 0 <= order <= 16:
        raise ValueError("adaptive order outside supported range")
    if not 1 <= bucket_bits <= 16:
        raise ValueError("adaptive bucket bits outside supported range")

    models: dict[int, _Model] = {}
    tail = bytearray(prefix_history[-order:] if order else b"")
    encoder = _ArithmeticEncoder()

    for symbol in data:
        bucket = _bucket(tail, order, bucket_bits)
        model = models.get(bucket)
        if model is None:
            model = _Model.create()
            models[bucket] = model

        low, high, total = model.interval(symbol)
        encoder.encode(low, high, total)
        model.update(symbol)

        if order:
            tail.append(symbol)
            if len(tail) > order:
                del tail[:-order]

    payload, bit_length = encoder.finish()
    return (
        bytes((ADAPTIVE_VERSION, order, bucket_bits))
        + vencode(bit_length)
        + payload
    )


def decode_adaptive(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 3 or blob[0] != ADAPTIVE_VERSION:
        raise ValueError("unknown adaptive multinomial version")

    order = blob[1]
    bucket_bits = blob[2]
    if not 0 <= order <= 16:
        raise ValueError("invalid adaptive order")
    if not 1 <= bucket_bits <= 16:
        raise ValueError("invalid adaptive bucket bits")

    bit_length, pos = vdecode(blob, 3)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("adaptive payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    models: dict[int, _Model] = {}
    tail = bytearray(prefix_history[-order:] if order else b"")
    out = bytearray()

    for _ in range(source_length):
        bucket = _bucket(tail, order, bucket_bits)
        model = models.get(bucket)
        if model is None:
            model = _Model.create()
            models[bucket] = model

        target = decoder.target(model.total)
        symbol, low, high, total = model.select(target)
        decoder.update(low, high, total)
        model.update(symbol)
        out.append(symbol)

        if order:
            tail.append(symbol)
            if len(tail) > order:
                del tail[:-order]

    return bytes(out)
