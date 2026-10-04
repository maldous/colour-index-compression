"""Exact multinomial helper closure used by extracted specialist codecs.

This module intentionally exports only the helper API reached by the runtime
specialist closures; it is not the CIXM portfolio stream implementation.
"""
from __future__ import annotations

import math
from typing import Iterable

def vencode(x: int) -> bytes:
    if x < 0:
        raise ValueError("negative varint")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def vdecode(data: bytes, pos: int = 0) -> tuple[int, int]:
    x = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        b = data[pos]
        pos += 1
        x |= (b & 0x7F) << shift
        if not (b & 0x80):
            return x, pos
        shift += 7
        if shift > 70:
            raise ValueError("varint too large")


def _fixed_bytes(x: int, width_bits: int) -> bytes:
    if width_bits <= 0:
        return b""
    return x.to_bytes((width_bits + 7) // 8, "big")


def _read_fixed(data: bytes, pos: int, width_bits: int) -> tuple[int, int]:
    size = (width_bits + 7) // 8
    if pos + size > len(data):
        raise ValueError("truncated fixed-width integer")
    if not size:
        return 0, pos
    return int.from_bytes(data[pos : pos + size], "big"), pos + size


def combination_rank_colex(positions: Iterable[int]) -> int:
    return sum(math.comb(p, i + 1) for i, p in enumerate(positions))


def combination_unrank_colex(rank: int, k: int, universe: int) -> list[int]:
    if k == 0:
        return []
    if k < 0 or k > universe:
        raise ValueError("invalid combination")
    limit = math.comb(universe, k)
    if rank < 0 or rank >= limit:
        raise ValueError("combination rank outside range")

    result = []
    x = universe - 1
    for i in range(k, 0, -1):
        while math.comb(x, i) > rank:
            x -= 1
        result.append(x)
        rank -= math.comb(x, i)
        x -= 1
    result.sort()
    return result


def _composition_rank(parts: list[int]) -> int:
    if not parts or any(x <= 0 for x in parts):
        raise ValueError("composition parts must be positive")
    if len(parts) == 1:
        return 0
    cuts = []
    total = 0
    for p in parts[:-1]:
        total += p
        cuts.append(total - 1)
    return combination_rank_colex(cuts)


def _composition_unrank(rank: int, total: int, part_count: int) -> list[int]:
    if part_count <= 0:
        if total == 0:
            return []
        raise ValueError("invalid composition")
    if part_count == 1:
        return [total]
    cuts = [x + 1 for x in combination_unrank_colex(rank, part_count - 1, total - 1)]
    parts = []
    previous = 0
    for cut in cuts:
        parts.append(cut - previous)
        previous = cut
    parts.append(total - previous)
    return parts


class Fenwick:
    def __init__(self, counts: list[int]):
        self.n = len(counts)
        self.tree = [0] * (self.n + 1)
        for i, value in enumerate(counts):
            if value:
                self.add(i, value)

    def add(self, i: int, delta: int) -> None:
        i += 1
        while i <= self.n:
            self.tree[i] += delta
            i += i & -i

    def prefix(self, i: int) -> int:
        s = 0
        while i:
            s += self.tree[i]
            i -= i & -i
        return s

    def select(self, order: int) -> int:
        idx = 0
        bit = 1 << (self.n.bit_length() - 1)
        while bit:
            nxt = idx + bit
            if nxt <= self.n and self.tree[nxt] <= order:
                order -= self.tree[nxt]
                idx = nxt
            bit >>= 1
        if idx >= self.n:
            raise ValueError("Fenwick select outside range")
        return idx


def _counts(data: bytes) -> list[int]:
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    return counts


def multinomial_cardinality(counts: list[int]) -> int:
    """Exact n! / product(n_i!) without constructing all factorials."""
    remaining = sum(counts)
    total = 1
    for c in counts:
        if c:
            total *= math.comb(remaining, c)
            remaining -= c
    return total


def permutation_rank(data: bytes, counts: list[int]) -> int:
    """Lexicographic rank inside the multiset permutation/type class."""
    remaining = len(data)
    cardinality = multinomial_cardinality(counts)
    mutable = counts[:]
    fenwick = Fenwick(mutable)
    rank = 0

    for symbol in data:
        cumulative = fenwick.prefix(symbol)
        if cumulative:
            rank += (cardinality * cumulative) // remaining

        symbol_count = mutable[symbol]
        cardinality = (cardinality * symbol_count) // remaining
        mutable[symbol] -= 1
        fenwick.add(symbol, -1)
        remaining -= 1

    return rank


def permutation_unrank(rank: int, counts: list[int]) -> bytes:
    remaining = sum(counts)
    cardinality = multinomial_cardinality(counts)
    if rank < 0 or rank >= cardinality:
        raise ValueError("permutation rank outside type class")

    mutable = counts[:]
    fenwick = Fenwick(mutable)
    out = bytearray()

    while remaining:
        target_order = (rank * remaining) // cardinality
        symbol = fenwick.select(target_order)
        cumulative = fenwick.prefix(symbol)

        rank -= (cardinality * cumulative) // remaining
        symbol_count = mutable[symbol]
        cardinality = (cardinality * symbol_count) // remaining

        mutable[symbol] -= 1
        fenwick.add(symbol, -1)
        remaining -= 1
        out.append(symbol)

    return bytes(out)


TYPECLASS_RANK = 0
TYPECLASS_RANGE = 1
TYPECLASS_RANGE_THRESHOLD = 2048

_ARITH_PREC = 32
_ARITH_MAX = (1 << _ARITH_PREC) - 1
_ARITH_HALF = 1 << (_ARITH_PREC - 1)
_ARITH_Q1 = 1 << (_ARITH_PREC - 2)
_ARITH_Q3 = 3 * _ARITH_Q1


class _ArithmeticBitWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.current = 0
        self.used = 0
        self.bit_length = 0

    def write(self, bit: int) -> None:
        self.current = (self.current << 1) | (1 if bit else 0)
        self.used += 1
        self.bit_length += 1
        if self.used == 8:
            self.buffer.append(self.current)
            self.current = 0
            self.used = 0

    def finish(self) -> tuple[bytes, int]:
        if self.used:
            self.buffer.append(self.current << (8 - self.used))
        return bytes(self.buffer), self.bit_length


class _ArithmeticBitReader:
    def __init__(self, data: bytes, bit_length: int) -> None:
        self.data = data
        self.bit_length = bit_length
        self.pos = 0

    def read(self) -> int:
        if self.pos >= self.bit_length:
            self.pos += 1
            return 0
        bit = (self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1
        self.pos += 1
        return bit


class _ArithmeticEncoder:
    def __init__(self) -> None:
        self.low = 0
        self.high = _ARITH_MAX
        self.pending = 0
        self.writer = _ArithmeticBitWriter()

    def _emit(self, bit: int) -> None:
        self.writer.write(bit)
        while self.pending:
            self.writer.write(bit ^ 1)
            self.pending -= 1

    def encode(self, low_count: int, high_count: int, total: int) -> None:
        interval = self.high - self.low + 1
        self.high = self.low + (interval * high_count // total) - 1
        self.low = self.low + (interval * low_count // total)

        while True:
            if self.high < _ARITH_HALF:
                self._emit(0)
            elif self.low >= _ARITH_HALF:
                self._emit(1)
                self.low -= _ARITH_HALF
                self.high -= _ARITH_HALF
            elif self.low >= _ARITH_Q1 and self.high < _ARITH_Q3:
                self.pending += 1
                self.low -= _ARITH_Q1
                self.high -= _ARITH_Q1
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) + 1

    def finish(self) -> tuple[bytes, int]:
        self.pending += 1
        self._emit(0 if self.low < _ARITH_Q1 else 1)
        return self.writer.finish()


class _ArithmeticDecoder:
    def __init__(self, data: bytes, bit_length: int) -> None:
        self.reader = _ArithmeticBitReader(data, bit_length)
        self.low = 0
        self.high = _ARITH_MAX
        self.value = 0
        for _ in range(_ARITH_PREC):
            self.value = (self.value << 1) | self.reader.read()

    def target(self, total: int) -> int:
        interval = self.high - self.low + 1
        return ((self.value - self.low + 1) * total - 1) // interval

    def update(self, low_count: int, high_count: int, total: int) -> None:
        interval = self.high - self.low + 1
        self.high = self.low + (interval * high_count // total) - 1
        self.low = self.low + (interval * low_count // total)

        while True:
            if self.high < _ARITH_HALF:
                # The interval is already in the lower half: no offset is due.
                self.low, self.high, self.value = self.low, self.high, self.value
            elif self.low >= _ARITH_HALF:
                self.low -= _ARITH_HALF
                self.high -= _ARITH_HALF
                self.value -= _ARITH_HALF
            elif self.low >= _ARITH_Q1 and self.high < _ARITH_Q3:
                self.low -= _ARITH_Q1
                self.high -= _ARITH_Q1
                self.value -= _ARITH_Q1
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) + 1
            self.value = (self.value << 1) | self.reader.read()


def _range_encode_type_sequence(data: bytes, counts: list[int]) -> tuple[bytes, int]:
    mutable = counts[:]
    fenwick = Fenwick(mutable)
    remaining = len(data)
    encoder = _ArithmeticEncoder()

    for symbol in data:
        low = fenwick.prefix(symbol)
        high = low + mutable[symbol]
        encoder.encode(low, high, remaining)
        mutable[symbol] -= 1
        fenwick.add(symbol, -1)
        remaining -= 1

    return encoder.finish()


def _range_decode_type_sequence(
    payload: bytes,
    bit_length: int,
    counts: list[int],
) -> bytes:
    mutable = counts[:]
    fenwick = Fenwick(mutable)
    remaining = sum(counts)
    decoder = _ArithmeticDecoder(payload, bit_length)
    out = bytearray()

    while remaining:
        target = decoder.target(remaining)
        symbol = fenwick.select(target)
        low = fenwick.prefix(symbol)
        high = low + mutable[symbol]
        decoder.update(low, high, remaining)

        out.append(symbol)
        mutable[symbol] -= 1
        fenwick.add(symbol, -1)
        remaining -= 1

    return bytes(out)


def encode_type_class(data: bytes) -> bytes:
    return vencode(len(data)) + encode_type_class_known_n(data)


def decode_type_class(data: bytes, pos: int = 0) -> tuple[bytes, int]:
    n, pos = vdecode(data, pos)
    return decode_type_class_known_n(data, pos, n)


def encode_type_class_known_n(data: bytes) -> bytes:
    n = len(data)
    counts = _counts(data)
    active = [symbol for symbol, count in enumerate(counts) if count]
    m = len(active)

    out = bytearray(vencode(m))
    if n == 0:
        if m:
            raise AssertionError("empty block has active symbols")
        return bytes(out)

    if not (1 <= m <= min(256, n)):
        raise AssertionError("invalid active alphabet size")

    if m < 256:
        set_width = (math.comb(256, m) - 1).bit_length()
        out += _fixed_bytes(combination_rank_colex(active), set_width)

    parts = [counts[s] for s in active]
    if m > 1:
        histogram_width = (math.comb(n - 1, m - 1) - 1).bit_length()
        out += _fixed_bytes(_composition_rank(parts), histogram_width)

    cardinality = multinomial_cardinality(counts)
    sequence_width = (cardinality - 1).bit_length()

    if n >= TYPECLASS_RANGE_THRESHOLD and cardinality > 1:
        payload, bit_length = _range_encode_type_sequence(data, counts)
        out.append(TYPECLASS_RANGE)
        out += vencode(bit_length)
        out += payload
    else:
        out.append(TYPECLASS_RANK)
        out += _fixed_bytes(permutation_rank(data, counts), sequence_width)

    return bytes(out)


def _decode_type_class_counts(data: bytes, pos: int, n: int, m: int) -> tuple[list[int], int]:
    if m == 256:
        active = list(range(256))
    else:
        set_width = (math.comb(256, m) - 1).bit_length()
        set_rank, pos = _read_fixed(data, pos, set_width)
        active = combination_unrank_colex(set_rank, m, 256)
    if m == 1:
        parts = [n]
    else:
        histogram_width = (math.comb(n - 1, m - 1) - 1).bit_length()
        histogram_rank, pos = _read_fixed(data, pos, histogram_width)
        parts = _composition_unrank(histogram_rank, n, m)
    counts = [0] * 256
    for symbol, count in zip(active, parts):
        counts[symbol] = count
    return counts, pos


def _decode_type_class_sequence(data: bytes, pos: int, counts: list[int]) -> tuple[bytes, int]:
    cardinality = multinomial_cardinality(counts)
    if pos >= len(data):
        raise ValueError("missing type-class sequence mode")
    mode = data[pos]
    if mode == TYPECLASS_RANK:
        rank, pos = _read_fixed(data, pos + 1, (cardinality - 1).bit_length())
        if rank >= cardinality:
            raise ValueError("invalid sequence rank")
        return permutation_unrank(rank, counts), pos
    if mode == TYPECLASS_RANGE:
        bits, pos = vdecode(data, pos + 1); end = pos + (bits + 7) // 8
        if end > len(data):
            raise ValueError("truncated type-class range stream")
        return _range_decode_type_sequence(data[pos:end], bits, counts), end
    raise ValueError("unknown type-class sequence mode")


def decode_type_class_known_n(data: bytes, pos: int, n: int) -> tuple[bytes, int]:
    m, pos = vdecode(data, pos)
    if n == 0:
        if m != 0:
            raise ValueError("active symbols in empty type class")
        return b"", pos
    if not (1 <= m <= min(256, n)):
        raise ValueError("invalid active alphabet size")

    counts, pos = _decode_type_class_counts(data, pos, n, m)
    return _decode_type_class_sequence(data, pos, counts)
