"""Persistent adaptive multinomial models for CIXM5.

These models learn from every source block, regardless of which representation won for
that block. A later block can therefore use an order-0/1/2 probability prior learned
from earlier raw, LZ, BWT, numeric, or multinomial blocks without transmitting a model.

The coding distribution is the same integer Dirichlet-1/2 form used by adaptive.py.
Candidate encoding uses private working copies of touched context buckets; committing a
block updates the persistent state once, independent of the chosen block mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import math

from .adaptive import _Model
from .multinomial import (
    Fenwick,
    _ArithmeticDecoder,
    _ArithmeticEncoder,
    _context_bucket,
    vdecode,
    vencode,
)

STATEFUL_SPECS = (
    (0, 8),
    (1, 8),
    (2, 10),
)
STATE_LIMIT = 16384


def _bucket(tail: bytearray, order: int, bucket_bits: int) -> int:
    if order == 0:
        return 0
    return _context_bucket(tail, order, bucket_bits)


@dataclass
class PersistentAdaptiveState:
    order: int
    bucket_bits: int
    limit: int = STATE_LIMIT
    buckets: dict[int, list[int]] = field(default_factory=dict)

    def _working_model(
        self,
        bucket: int,
        working: dict[int, _Model],
    ) -> _Model:
        model = working.get(bucket)
        if model is not None:
            return model

        base = self.buckets.get(bucket)
        if base is None:
            counts = [0] * 256
        else:
            counts = base[:]

        model = _Model(counts, Fenwick(counts), sum(counts))
        working[bucket] = model
        return model

    def estimate_bits(self, data: bytes, prefix_history: bytes) -> float:
        """Estimate candidate log loss using the same private working updates."""
        working: dict[int, _Model] = {}
        tail = bytearray(prefix_history[-self.order:] if self.order else b"")
        bits = 0.0

        for symbol in data:
            bucket = _bucket(tail, self.order, self.bucket_bits)
            model = self._working_model(bucket, working)
            low, high, total = model.interval(symbol)
            frequency = high - low
            bits += math.log2(total) - math.log2(frequency)
            model.update(symbol)

            if self.order:
                tail.append(symbol)
                if len(tail) > self.order:
                    del tail[:-self.order]

        return bits

    def encode(self, data: bytes, prefix_history: bytes) -> bytes:
        working: dict[int, _Model] = {}
        tail = bytearray(prefix_history[-self.order:] if self.order else b"")
        encoder = _ArithmeticEncoder()

        for symbol in data:
            bucket = _bucket(tail, self.order, self.bucket_bits)
            model = self._working_model(bucket, working)
            low, high, total = model.interval(symbol)
            encoder.encode(low, high, total)
            model.update(symbol)

            if self.order:
                tail.append(symbol)
                if len(tail) > self.order:
                    del tail[:-self.order]

        payload, bit_length = encoder.finish()
        return vencode(bit_length) + payload

    def decode(
        self,
        blob: bytes,
        source_length: int,
        prefix_history: bytes,
    ) -> bytes:
        bit_length, pos = vdecode(blob, 0)
        byte_length = (bit_length + 7) // 8
        if pos + byte_length != len(blob):
            raise ValueError("persistent adaptive payload length mismatch")

        working: dict[int, _Model] = {}
        tail = bytearray(prefix_history[-self.order:] if self.order else b"")
        decoder = _ArithmeticDecoder(blob[pos:], bit_length)
        out = bytearray()

        for _ in range(source_length):
            bucket = _bucket(tail, self.order, self.bucket_bits)
            model = self._working_model(bucket, working)
            target = decoder.target(model.total)
            symbol, low, high, total = model.select(target)
            decoder.update(low, high, total)
            model.update(symbol)
            out.append(symbol)

            if self.order:
                tail.append(symbol)
                if len(tail) > self.order:
                    del tail[:-self.order]

        return bytes(out)

    def observe(self, data: bytes, prefix_history: bytes) -> None:
        tail = bytearray(prefix_history[-self.order:] if self.order else b"")
        touched: set[int] = set()

        for symbol in data:
            bucket = _bucket(tail, self.order, self.bucket_bits)
            counts = self.buckets.get(bucket)
            if counts is None:
                counts = [0] * 256
                self.buckets[bucket] = counts
            counts[symbol] += 1
            touched.add(bucket)

            if self.order:
                tail.append(symbol)
                if len(tail) > self.order:
                    del tail[:-self.order]

        for bucket in touched:
            counts = self.buckets[bucket]
            total = sum(counts)
            if total > self.limit:
                self.buckets[bucket] = [count // 2 for count in counts]


def make_persistent_states() -> list[PersistentAdaptiveState]:
    return [
        PersistentAdaptiveState(order, bucket_bits)
        for order, bucket_bits in STATEFUL_SPECS
    ]
