"""CIX multinomial codec.

A physical, lossless research codec built around multinomial enumerative coding.

Core block identity:

    |T(c)| = n! / product_i(n_i!)

where n_i is the count of byte value i in a block.

A block stores:
- which byte symbols are active, itself as a combination rank;
- the positive composition (n_i), itself as a stars-and-bars combination rank;
- the exact permutation rank of the byte sequence inside that type class.

Context mode generalises the same idea. Positions are deterministically routed into
context buckets. Every bucket is encoded as its own multinomial type class. The decoder
reconstructs the original sequence by consuming the next symbol from the bucket selected
by the already-decoded context.

The stream layer is adaptive: block boundaries can move when the observed distribution
changes, and every block independently chooses raw, plain-multinomial, or a context model.
"""

from __future__ import annotations

import hashlib
import math
import struct
import zlib
from dataclasses import dataclass, field
from typing import Iterable

MAGIC = b"CIXM5"
MODE_RAW = 0
MODE_MULTINOMIAL = 1
MODE_CONTEXT = 2
MODE_LZ = 3
MODE_BWT = 4
MODE_TRANSFORM = 5
MODE_BITPLANE = 6
MODE_CHAIN = 7
MODE_NUMERIC = 8
MODE_REFERENCE = 9
MODE_ADAPTIVE = 10
MODE_SPARSE = 11
MODE_RUNS = 12
MODE_PERSISTENT_ADAPTIVE = 13
MODE_RECORD = 14
MODE_PERIODIC = 15
MODE_PPM = 16
MODE_EXPERT_MIX = 17
MODE_WAVELET = 18
MODE_FIXED_MIX = 19
MODE_END = 255
MAX_HISTORY_BYTES = 16 << 20
MAX_DEDUP_BLOCKS = 4096


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
                pass
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


def decode_type_class_known_n(data: bytes, pos: int, n: int) -> tuple[bytes, int]:
    m, pos = vdecode(data, pos)
    if n == 0:
        if m != 0:
            raise ValueError("active symbols in empty type class")
        return b"", pos
    if not (1 <= m <= min(256, n)):
        raise ValueError("invalid active alphabet size")

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

    cardinality = multinomial_cardinality(counts)
    sequence_width = (cardinality - 1).bit_length()

    if pos >= len(data):
        raise ValueError("missing type-class sequence mode")
    sequence_mode = data[pos]
    pos += 1

    if sequence_mode == TYPECLASS_RANK:
        sequence_rank, pos = _read_fixed(data, pos, sequence_width)
        if sequence_rank >= cardinality:
            raise ValueError("invalid sequence rank")
        result = permutation_unrank(sequence_rank, counts)

    elif sequence_mode == TYPECLASS_RANGE:
        bit_length, pos = vdecode(data, pos)
        byte_length = (bit_length + 7) // 8
        end = pos + byte_length
        if end > len(data):
            raise ValueError("truncated type-class range stream")
        result = _range_decode_type_sequence(data[pos:end], bit_length, counts)
        pos = end

    else:
        raise ValueError("unknown type-class sequence mode")

    return result, pos


def _context_bucket(tail: bytes | bytearray, order: int, bucket_bits: int) -> int:
    if order <= 0:
        return 0

    ctx = tail[-order:]
    if order == 1 and bucket_bits >= 8:
        return ctx[-1] if ctx else 0

    h = 1469598103934665603
    for b in ctx:
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h & ((1 << bucket_bits) - 1)


def encode_context_type_classes(
    data: bytes,
    *,
    order: int,
    bucket_bits: int,
    prefix_history: bytes = b"",
) -> bytes:
    if not (1 <= order <= 16):
        raise ValueError("context order outside supported range")
    if not (1 <= bucket_bits <= 16):
        raise ValueError("bucket bits outside supported range")

    bucket_count = 1 << bucket_bits
    buckets: dict[int, bytearray] = {}
    tail = bytearray(prefix_history[-order:])

    for symbol in data:
        bucket = _context_bucket(tail, order, bucket_bits)
        buckets.setdefault(bucket, bytearray()).append(symbol)
        tail.append(symbol)
        if len(tail) > order:
            del tail[:-order]

    ids = sorted(buckets)
    q = len(ids)
    n = len(data)

    out = bytearray((order, bucket_bits))
    out += vencode(q)

    if q and q < bucket_count:
        bucket_set_width = (math.comb(bucket_count, q) - 1).bit_length()
        out += _fixed_bytes(combination_rank_colex(ids), bucket_set_width)

    lengths = [len(buckets[bucket]) for bucket in ids]
    if q > 1:
        length_width = (math.comb(n - 1, q - 1) - 1).bit_length()
        out += _fixed_bytes(_composition_rank(lengths), length_width)

    for bucket in ids:
        out += encode_type_class_known_n(bytes(buckets[bucket]))

    return bytes(out)


def decode_context_type_classes(
    data: bytes,
    pos: int,
    n: int,
    *,
    prefix_history: bytes = b"",
) -> tuple[bytes, int]:
    if pos + 2 > len(data):
        raise ValueError("truncated context model")

    order = data[pos]
    bucket_bits = data[pos + 1]
    pos += 2

    if not (1 <= order <= 16 and 1 <= bucket_bits <= 16):
        raise ValueError("invalid context parameters")

    bucket_count = 1 << bucket_bits
    q, pos = vdecode(data, pos)
    if q > min(bucket_count, n):
        raise ValueError("invalid active bucket count")

    if q == 0:
        if n:
            raise ValueError("non-empty block has no buckets")
        return b"", pos

    if q == bucket_count:
        ids = list(range(bucket_count))
    else:
        bucket_set_width = (math.comb(bucket_count, q) - 1).bit_length()
        bucket_set_rank, pos = _read_fixed(data, pos, bucket_set_width)
        ids = combination_unrank_colex(bucket_set_rank, q, bucket_count)

    if q == 1:
        lengths = [n]
    else:
        length_width = (math.comb(n - 1, q - 1) - 1).bit_length()
        length_rank, pos = _read_fixed(data, pos, length_width)
        lengths = _composition_unrank(length_rank, n, q)

    streams: dict[int, bytes] = {}
    for bucket, length in zip(ids, lengths):
        stream, pos = decode_type_class_known_n(data, pos, length)
        streams[bucket] = stream

    cursors = {bucket: 0 for bucket in streams}
    tail = bytearray(prefix_history[-order:])
    out = bytearray()

    for _ in range(n):
        bucket = _context_bucket(tail, order, bucket_bits)
        stream = streams.get(bucket)
        if stream is None:
            raise ValueError("decoder selected absent context bucket")
        cursor = cursors[bucket]
        if cursor >= len(stream):
            raise ValueError("context stream exhausted early")

        symbol = stream[cursor]
        cursors[bucket] = cursor + 1
        out.append(symbol)

        tail.append(symbol)
        if len(tail) > order:
            del tail[:-order]

    if any(cursors[b] != len(streams[b]) for b in streams):
        raise ValueError("unused symbols in context streams")

    return bytes(out), pos


@dataclass(frozen=True)
class ContextModel:
    order: int
    bucket_bits: int


@dataclass
class StreamConfig:
    min_block: int = 2048
    max_block: int = 16384
    probe_stride: int = 1024
    split_gain_bits: float = 128.0
    min_savings_bytes: int = 1
    context_models: tuple[ContextModel, ...] = (
        ContextModel(1, 6),
        ContextModel(1, 8),
        ContextModel(2, 8),
        ContextModel(2, 10),
        ContextModel(3, 10),
        ContextModel(4, 10),
        ContextModel(4, 12),
        ContextModel(6, 12),
    )
    history_bytes: int = 1 << 20
    enable_lz: bool = True
    enable_bwt: bool = True
    enable_transforms: bool = True
    enable_bitplanes: bool = True
    enable_chains: bool = False
    enable_numeric: bool = True
    chunk_mode: str = "hybrid"
    content_mask_bits: int = 13
    lz_window_bytes: int = 1 << 20
    lz_chain: int = 32
    bwt_max_block: int = 65536
    context_beam: int = 4
    transform_beam: int = 6
    chain_beam: int = 4
    enable_dedup: bool = True
    dedup_blocks: int = 1024
    enable_adaptive: bool = True
    adaptive_beam: int = 3
    enable_sparse: bool = True
    enable_runs: bool = True
    enable_persistent_adaptive: bool = True
    enable_record: bool = True
    record_beam: int = 2
    enable_periodic: bool = True
    periodic_beam: int = 3
    structured_block_target: int = 65536
    enable_ppm: bool = True
    ppm_order: int = 4
    ppm_beam: int = 1
    ppm_orders: tuple[int, ...] = ()
    enable_expert_mix: bool = True
    expert_orders: tuple[int, ...] = (0, 1, 2, 4)
    enable_wavelet: bool = True
    enable_fixed_mix: bool = False
    fixed_mix_max_block: int = 32768

    @classmethod
    def extreme(cls) -> "StreamConfig":
        return cls(
            min_block=4096,
            max_block=32768,
            probe_stride=1024,
            split_gain_bits=64.0,
            history_bytes=MAX_HISTORY_BYTES,
            lz_window_bytes=MAX_HISTORY_BYTES,
            lz_chain=96,
            enable_chains=True,
            context_beam=6,
            transform_beam=10,
            chain_beam=6,
            adaptive_beam=6,
            enable_record=True,
            record_beam=6,
            enable_periodic=True,
            periodic_beam=8,
            structured_block_target=65536,
            enable_ppm=True,
            ppm_order=6,
            ppm_beam=9,
            ppm_orders=(0, 1, 2, 3, 4, 5, 6, 7, 8),
            enable_expert_mix=True,
            expert_orders=(0, 1, 2, 3, 4, 6),
            enable_fixed_mix=True,
            fixed_mix_max_block=32768,
            chunk_mode="hybrid",
            content_mask_bits=14,
            context_models=(
                ContextModel(1, 6),
                ContextModel(1, 8),
                ContextModel(2, 8),
                ContextModel(2, 10),
                ContextModel(3, 10),
                ContextModel(4, 10),
                ContextModel(4, 12),
                ContextModel(6, 12),
                ContextModel(8, 12),
            ),
        )


@dataclass
class EncodedBlock:
    mode: int
    source_length: int
    payload: bytes
    description: str

    @property
    def framed(self) -> bytes:
        return (
            bytes((self.mode,))
            + vencode(self.source_length)
            + vencode(len(self.payload))
            + self.payload
        )


def _context_model_estimate(
    data: bytes,
    model: ContextModel,
    prefix_history: bytes,
) -> float:
    bucket_count = 1 << model.bucket_bits
    bucket_counts: dict[int, list[int]] = {}
    lengths: dict[int, int] = {}
    tail = bytearray(prefix_history[-model.order:])

    for symbol in data:
        bucket = _context_bucket(tail, model.order, model.bucket_bits)
        counts = bucket_counts.get(bucket)
        if counts is None:
            counts = [0] * 256
            bucket_counts[bucket] = counts
            lengths[bucket] = 0
        counts[symbol] += 1
        lengths[bucket] += 1

        tail.append(symbol)
        if len(tail) > model.order:
            del tail[:-model.order]

    ids = sorted(bucket_counts)
    q = len(ids)
    n = len(data)
    size = 3.0

    if q and q < bucket_count:
        size += math.log2(math.comb(bucket_count, q)) / 8.0
    if q > 1:
        size += math.log2(math.comb(n - 1, q - 1)) / 8.0

    for bucket in ids:
        size += _approx_typeclass_bytes_from_counts(
            bucket_counts[bucket], lengths[bucket]
        )
    return size


def _looks_bwt_worthy(data: bytes) -> bool:
    """Format-agnostic BWT prefilter based only on byte structure."""
    if len(data) < 64:
        return False

    sample = data[: min(len(data), 8192)]
    if len(set(sample)) <= 64:
        return True

    seen = set()
    repeats = 0
    total = 0
    # Use overlapping byte shingles; no text/format assumptions.
    for pos in range(0, max(0, len(sample) - 4)):
        token = sample[pos : pos + 4]
        total += 1
        if token in seen:
            repeats += 1
        else:
            seen.add(token)

    run_changes = 1 + sum(
        left != right for left, right in zip(sample, sample[1:])
    )
    run_density = run_changes / max(1, len(sample))
    repeat_density = repeats / max(1, total)
    return repeat_density >= 0.025 or run_density <= 0.55


def _bitplane_estimate(data: bytes) -> float:
    n = len(data)
    if not n:
        return 1.0
    bits = 8.0
    for shift in range(8):
        ones = sum((byte >> shift) & 1 for byte in data)
        minority = min(ones, n - ones)
        bits += 8.0 * len(vencode(minority))
        if minority:
            bits += math.log2(math.comb(n, minority))
    return bits / 8.0


def encode_best_block(
    block: bytes,
    *,
    prefix_history: bytes,
    config: StreamConfig,
) -> EncodedBlock:
    candidates: list[EncodedBlock] = [
        EncodedBlock(MODE_RAW, len(block), block, "raw"),
        EncodedBlock(
            MODE_MULTINOMIAL,
            len(block),
            encode_type_class_known_n(block),
            "multinomial-256",
        ),
    ]

    if config.enable_wavelet and len(block) >= 2:
        try:
            from .wavelet import encode_wavelet, estimate_wavelet_bits

            direct_size = len(candidates[1].framed)
            estimate_bytes = estimate_wavelet_bits(block) / 8.0
            if estimate_bytes <= direct_size * 1.03 + 8:
                payload = encode_wavelet(block)
                candidates.append(
                    EncodedBlock(
                        MODE_WAVELET,
                        len(block),
                        payload,
                        "hierarchical-colour-index",
                    )
                )
        except Exception:
            pass

    profiled_contexts = sorted(
        (
            (
                _context_model_estimate(block, model, prefix_history),
                model,
            )
            for model in config.context_models
        ),
        key=lambda item: (item[0], item[1].order, item[1].bucket_bits),
    )
    context_beam = config.context_beam
    for _, model in profiled_contexts[: context_beam]:
        payload = encode_context_type_classes(
            block,
            order=model.order,
            bucket_bits=model.bucket_bits,
            prefix_history=prefix_history,
        )
        candidates.append(
            EncodedBlock(
                MODE_CONTEXT,
                len(block),
                payload,
                f"context-multinomial-o{model.order}-b{model.bucket_bits}",
            )
        )

    if config.enable_adaptive:
        try:
            from .adaptive import encode_adaptive

            payload = encode_adaptive(block, order=0, bucket_bits=8)
            candidates.append(
                EncodedBlock(
                    MODE_ADAPTIVE,
                    len(block),
                    payload,
                    "adaptive-multinomial-o0",
                )
            )

            for _, model in profiled_contexts[: config.adaptive_beam]:
                payload = encode_adaptive(
                    block,
                    order=model.order,
                    bucket_bits=model.bucket_bits,
                    prefix_history=prefix_history,
                )
                candidates.append(
                    EncodedBlock(
                        MODE_ADAPTIVE,
                        len(block),
                        payload,
                        f"adaptive-multinomial-o{model.order}-b{model.bucket_bits}",
                    )
                )
        except Exception:
            pass

    if config.enable_sparse and len(block) >= 2:
        counts = _counts(block)
        dominant_count = max(counts)
        if dominant_count * 4 >= len(block):
            try:
                from .sparse import encode_sparse_block

                payload, description = encode_sparse_block(block)
                candidates.append(
                    EncodedBlock(MODE_SPARSE, len(block), payload, description)
                )
            except Exception:
                pass

    if config.enable_runs and len(block) >= 2:
        run_count = 1 + sum(
            left != right for left, right in zip(block, block[1:])
        )
        if run_count * 3 <= len(block) * 2:
            try:
                from .runs import encode_run_block

                payload, description = encode_run_block(block)
                candidates.append(
                    EncodedBlock(MODE_RUNS, len(block), payload, description)
                )
            except Exception:
                pass

    if config.enable_lz and len(block) >= 16:
        try:
            from .lz import encode_lz_block

            payload, description = encode_lz_block(
                block,
                prefix_history=prefix_history,
                context_models=config.context_models,
                window=min(config.lz_window_bytes, MAX_HISTORY_BYTES),
                chain=config.lz_chain,
            )
            candidates.append(
                EncodedBlock(MODE_LZ, len(block), payload, description)
            )
        except Exception:
            pass

    if (
        config.enable_bwt
        and 32 <= len(block) <= config.bwt_max_block
        and _looks_bwt_worthy(block)
    ):
        try:
            from .bwt import encode_bwt_block

            payload, description = encode_bwt_block(block)
            candidates.append(
                EncodedBlock(MODE_BWT, len(block), payload, description)
            )
        except Exception:
            pass

    if (
        config.enable_ppm
        and len(block) >= 512
        and _looks_bwt_worthy(block)
    ):
        try:
            from .ppm import encode_ppm, estimate_ppm_portfolio_bits

            order_candidates = (
                sorted(set(config.ppm_orders))
                if config.ppm_orders
                else sorted(
                    {
                        max(0, config.ppm_order - 2),
                        max(0, config.ppm_order - 1),
                        config.ppm_order,
                    }
                )
            )
            if any(order < 0 or order > 8 for order in order_candidates):
                raise ValueError("PPM order candidate outside supported range")
            profiled_ppm = sorted(
                (
                    estimate_ppm_portfolio_bits(
                        block,
                        max_order=order,
                        prefix_history=prefix_history,
                        sample_limit=len(block),
                    ),
                    order,
                )
                for order in order_candidates
            )
            current_best = min(len(candidate.framed) for candidate in candidates)
            plausible_ppm = [
                (bits, order)
                for bits, order in profiled_ppm
                if bits / 8.0 <= current_best * 1.08 + 32
            ]
            for _, order in plausible_ppm[: max(1, config.ppm_beam)]:
                payload = encode_ppm(
                    block,
                    max_order=order,
                    prefix_history=prefix_history,
                )
                candidates.append(
                    EncodedBlock(
                        MODE_PPM,
                        len(block),
                        payload,
                        f"ppm-o{order}",
                    )
                )
        except Exception:
            pass

    if (
        config.enable_expert_mix
        and len(block) >= 512
        and _looks_bwt_worthy(block)
    ):
        try:
            from .expertmix import encode_expert_mix, estimate_expert_bits

            current_best = min(len(candidate.framed) for candidate in candidates)
            estimate = estimate_expert_bits(
                block,
                orders=config.expert_orders,
                prefix_history=prefix_history,
            )
            if estimate / 8.0 <= current_best * 1.08 + 32:
                payload = encode_expert_mix(
                    block,
                    orders=config.expert_orders,
                    prefix_history=prefix_history,
                )
                candidates.append(
                    EncodedBlock(
                        MODE_EXPERT_MIX,
                        len(block),
                        payload,
                        "context-expert-" + "-".join(map(str, config.expert_orders)),
                    )
                )
        except Exception:
            pass

    if (
        config.enable_fixed_mix
        and 512 <= len(block) <= config.fixed_mix_max_block
        and _looks_bwt_worthy(block)
    ):
        try:
            from .fixedmix import encode_fixed_mix

            payload = encode_fixed_mix(
                block,
                prefix_history=prefix_history,
            )
            candidates.append(
                EncodedBlock(
                    MODE_FIXED_MIX,
                    len(block),
                    payload,
                    "fixed-point-context-mixer",
                )
            )
        except Exception:
            pass

    if config.enable_transforms and len(block) >= 4:
        try:
            from .transforms import encode_transform_block

            payload, description = encode_transform_block(
                block, beam=config.transform_beam
            )
            candidates.append(
                EncodedBlock(MODE_TRANSFORM, len(block), payload, description)
            )
        except Exception:
            pass

    if config.enable_numeric and len(block) >= 6:
        try:
            from .numeric import encode_numeric_block

            payload, description = encode_numeric_block(block)
            candidates.append(
                EncodedBlock(MODE_NUMERIC, len(block), payload, description)
            )
        except Exception:
            pass

    if config.enable_record and len(block) >= 256:
        try:
            from .record import best_record_estimate, encode_record_block

            estimate = best_record_estimate(block)
            current_best = min(len(candidate.framed) for candidate in candidates)
            if estimate + 8.0 < current_best:
                payload, description = encode_record_block(
                    block, beam=config.record_beam
                )
                candidates.append(
                    EncodedBlock(MODE_RECORD, len(block), payload, description)
                )
        except Exception:
            pass

    if config.enable_periodic and len(block) >= 256:
        try:
            from .periodic import best_periodic_estimate, encode_periodic_block

            estimate = best_periodic_estimate(block)
            current_best = min(len(candidate.framed) for candidate in candidates)
            if estimate + 8.0 < current_best:
                payload, description = encode_periodic_block(
                    block, beam=config.periodic_beam
                )
                candidates.append(
                    EncodedBlock(MODE_PERIODIC, len(block), payload, description)
                )
        except Exception:
            pass

    if config.enable_bitplanes and len(block) >= 2:
        try:
            current_best = min(len(candidate.framed) for candidate in candidates)
            if _bitplane_estimate(block) <= current_best * 1.05 + 16:
                from .bitplanes import encode_bitplanes

                payload, description = encode_bitplanes(block)
                candidates.append(
                    EncodedBlock(MODE_BITPLANE, len(block), payload, description)
                )
        except Exception:
            pass

    if config.enable_chains and len(block) >= 32:
        try:
            from .chain import encode_chain_block

            payload, description = encode_chain_block(
                block,
                context_models=config.context_models,
                beam=config.chain_beam,
            )
            candidates.append(
                EncodedBlock(MODE_CHAIN, len(block), payload, description)
            )
        except Exception:
            pass

    best = min(candidates, key=lambda candidate: len(candidate.framed))
    raw_size = len(candidates[0].framed)
    if raw_size - len(best.framed) < config.min_savings_bytes:
        return candidates[0]
    return best


def _varint_size(x: int) -> int:
    return len(vencode(x))


def _approx_typeclass_bytes_from_counts(counts: list[int], n: int) -> float:
    if n == 0:
        return 1.0

    active = [c for c in counts if c]
    m = len(active)
    size = _varint_size(m)

    if m < 256:
        size += (math.log2(math.comb(256, m)) + 7.0) / 8.0
    if m > 1:
        size += (math.log2(math.comb(n - 1, m - 1)) + 7.0) / 8.0

    log_cardinality = (
        math.lgamma(n + 1)
        - sum(math.lgamma(c + 1) for c in active)
    ) / math.log(2.0)
    size += (max(0.0, log_cardinality) + 7.0) / 8.0
    return size


def _best_split(buffer: bytes, config: StreamConfig) -> int | None:
    n = len(buffer)
    if n < config.min_block * 2:
        return None

    total_counts = _counts(buffer)
    whole = _approx_typeclass_bytes_from_counts(total_counts, n)

    left_counts = [0] * 256
    right_counts = total_counts[:]
    best_gain_bits = config.split_gain_bits
    best_cut: int | None = None

    next_probe = config.min_block
    for i, symbol in enumerate(buffer, start=1):
        left_counts[symbol] += 1
        right_counts[symbol] -= 1

        if i != next_probe:
            continue
        if n - i < config.min_block:
            break

        left = _approx_typeclass_bytes_from_counts(left_counts, i)
        right = _approx_typeclass_bytes_from_counts(right_counts, n - i)
        split_cost = left + right + 6.0
        gain_bits = (whole - split_cost) * 8.0
        if gain_bits > best_gain_bits:
            best_gain_bits = gain_bits
            best_cut = i

        next_probe += config.probe_stride

    return best_cut


def _gear_value(byte: int) -> int:
    # SplitMix64-derived fixed gear value: deterministic without storing a table.
    x = (byte + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return (x ^ (x >> 31)) & 0xFFFFFFFFFFFFFFFF


_GEAR = tuple(_gear_value(byte) for byte in range(256))


def _content_boundary(buffer: bytes, config: StreamConfig) -> int | None:
    if config.chunk_mode not in ("content", "hybrid"):
        return None
    if len(buffer) < config.min_block:
        return None

    mask = (1 << config.content_mask_bits) - 1
    value = 0
    stop = min(len(buffer), config.max_block)
    for index, byte in enumerate(buffer[:stop], start=1):
        value = ((value << 1) + _GEAR[byte]) & 0xFFFFFFFFFFFFFFFF
        if index >= config.min_block and (value & mask) == 0:
            return index
    return None


@dataclass
class StreamEncoder:
    """Incremental encoder.

    feed() returns bytes that are immediately safe to write to a socket/file.
    No final source length or block count is required up front. finish() emits
    the last buffered block followed by the end footer (length + CRC32).
    """
    config: StreamConfig = field(default_factory=StreamConfig)
    _buffer: bytearray = field(default_factory=bytearray, init=False)
    _history: bytearray = field(default_factory=bytearray, init=False)
    _source_length: int = field(default=0, init=False)
    _crc: int = field(default=0, init=False)
    _started: bool = field(default=False, init=False)
    _finished: bool = field(default=False, init=False)
    _descriptions: list[str] = field(default_factory=list, init=False)
    _next_check: int = field(default=0, init=False)
    _block_index: int = field(default=0, init=False)
    _dedup: dict[bytes, list[tuple[int, bytes]]] = field(
        default_factory=dict, init=False
    )
    _persistent_states: list = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.config.min_block <= 0:
            raise ValueError("min_block must be positive")
        if self.config.max_block < self.config.min_block:
            raise ValueError("max_block must be >= min_block")
        if self.config.probe_stride <= 0:
            raise ValueError("probe_stride must be positive")
        max_order = max((m.order for m in self.config.context_models), default=0)
        if self.config.history_bytes < max_order:
            raise ValueError("history_bytes must cover the largest context order")
        if not 0 < self.config.history_bytes <= MAX_HISTORY_BYTES:
            raise ValueError("history_bytes outside CIXM3 supported range")
        if not 0 < self.config.lz_window_bytes <= MAX_HISTORY_BYTES:
            raise ValueError("lz_window_bytes outside CIXM3 supported range")
        if self.config.chunk_mode not in ("adaptive", "content", "hybrid", "fixed"):
            raise ValueError("unknown chunk_mode")
        if not 4 <= self.config.content_mask_bits <= 24:
            raise ValueError("content_mask_bits outside supported range")
        if not self.config.max_block <= self.config.structured_block_target <= (1 << 20):
            raise ValueError("structured_block_target outside supported range")
        if not 0 <= self.config.dedup_blocks <= MAX_DEDUP_BLOCKS:
            raise ValueError("dedup_blocks outside CIXM5 supported range")
        from .stateful import make_persistent_states
        self._persistent_states = make_persistent_states()
        self._next_check = min(self.config.max_block, self.config.min_block * 2)

    def _header(self) -> bytes:
        if self._started:
            return b""
        self._started = True
        return MAGIC + vencode(self.config.history_bytes)

    def feed(self, data: bytes) -> bytes:
        if self._finished:
            raise ValueError("encoder already finished")

        emitted = bytearray(self._header())
        if not data:
            return bytes(emitted)

        self._source_length += len(data)
        self._crc = zlib.crc32(data, self._crc)
        self._buffer.extend(data)

        while len(self._buffer) >= self._next_check:
            probe = bytes(self._buffer[: self._next_check])
            structured = _looks_bwt_worthy(probe)
            effective_max = (
                self.config.structured_block_target
                if structured and self.config.chunk_mode != "fixed"
                else self.config.max_block
            )

            # Strong byte-level repetition/run structure benefits from a longer
            # model horizon. Holding the block open is format agnostic: the same
            # shingle/run statistic is used for every byte stream.
            # A longer horizon may help stationary repeated structure, but it
            # must never disable change-point detection. Streaming data can switch
            # regimes at any time, so an MDL-profitable entropy split always wins.
            entropy_cut = (
                _best_split(probe, self.config)
                if self.config.chunk_mode in ("adaptive", "hybrid")
                else None
            )
            content_cut = (
                _content_boundary(probe, self.config)
                if not structured
                else None
            )

            cuts = [cut for cut in (entropy_cut, content_cut) if cut is not None]
            cut = min(cuts) if cuts else None

            if cut is not None:
                emitted += self._emit(cut)
                self._next_check = min(
                    self.config.max_block, self.config.min_block * 2
                )
                continue

            if self._next_check >= effective_max:
                emitted += self._emit(effective_max)
                self._next_check = min(
                    self.config.max_block, self.config.min_block * 2
                )
                continue

            self._next_check = min(
                effective_max,
                self._next_check + self.config.probe_stride,
            )

        return bytes(emitted)

    def _emit(self, count: int) -> bytes:
        block = bytes(self._buffer[:count])
        del self._buffer[:count]

        encoded = None
        digest = hashlib.blake2b(block, digest_size=8).digest()

        if self.config.enable_dedup and self.config.dedup_blocks:
            minimum_index = self._block_index - self.config.dedup_blocks
            entries = self._dedup.get(digest, [])
            for previous_index, previous_block in reversed(entries):
                if previous_index < minimum_index:
                    break
                if previous_block == block:
                    distance = self._block_index - previous_index
                    encoded = EncodedBlock(
                        MODE_REFERENCE,
                        len(block),
                        vencode(distance),
                        f"dedup-block-distance-{distance}",
                    )
                    break

        prefix_history = bytes(self._history)

        if encoded is None:
            encoded = encode_best_block(
                block,
                prefix_history=prefix_history,
                config=self.config,
            )

            if self.config.enable_persistent_adaptive:
                for model_id, state in enumerate(self._persistent_states):
                    try:
                        estimate = state.estimate_bits(block, prefix_history)
                        if estimate / 8.0 > len(encoded.framed) * 1.08 + 32:
                            continue
                        payload = bytes((model_id,)) + state.encode(
                            block, prefix_history
                        )
                        candidate = EncodedBlock(
                            MODE_PERSISTENT_ADAPTIVE,
                            len(block),
                            payload,
                            f"persistent-adaptive-o{state.order}-b{state.bucket_bits}",
                        )
                        if len(candidate.framed) < len(encoded.framed):
                            encoded = candidate
                    except Exception:
                        pass

        self._descriptions.append(encoded.description)

        for state in self._persistent_states:
            state.observe(block, prefix_history)

        entries = self._dedup.setdefault(digest, [])
        entries.append((self._block_index, block))
        minimum_index = self._block_index - self.config.dedup_blocks
        while entries and entries[0][0] < minimum_index:
            del entries[0]
        self._block_index += 1

        self._history.extend(block)
        if len(self._history) > self.config.history_bytes:
            del self._history[:-self.config.history_bytes]

        return encoded.framed

    def finish(self) -> bytes:
        if self._finished:
            return b""

        emitted = bytearray(self._header())
        if self._buffer:
            emitted += self._emit(len(self._buffer))

        emitted.append(MODE_END)
        emitted += vencode(self._source_length)
        emitted += struct.pack("<I", self._crc & 0xFFFFFFFF)
        self._finished = True
        return bytes(emitted)

    @property
    def block_descriptions(self) -> tuple[str, ...]:
        return tuple(self._descriptions)


@dataclass
class StreamDecoder:
    history_bytes: int | None = None
    _buffer: bytearray = field(default_factory=bytearray, init=False)
    _history: bytearray = field(default_factory=bytearray, init=False)
    _decoded_length: int = field(default=0, init=False)
    _crc: int = field(default=0, init=False)
    _started: bool = field(default=False, init=False)
    _finished: bool = field(default=False, init=False)
    _recent_blocks: list[bytes] = field(default_factory=list, init=False)
    _persistent_states: list = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        from .stateful import make_persistent_states
        self._persistent_states = make_persistent_states()

    def feed(self, data: bytes) -> bytes:
        if self._finished and data:
            raise ValueError("data after CIX end footer")
        self._buffer.extend(data)
        out = bytearray()

        if not self._started:
            if len(self._buffer) < len(MAGIC):
                return b""
            if bytes(self._buffer[: len(MAGIC)]) != MAGIC:
                raise ValueError("not a CIX multinomial stream")
            try:
                encoded_history, header_end = vdecode(
                    bytes(self._buffer), len(MAGIC)
                )
            except ValueError as exc:
                if "truncated" in str(exc):
                    return b""
                raise
            if not 0 < encoded_history <= MAX_HISTORY_BYTES:
                raise ValueError("invalid CIX history window")
            if self.history_bytes is not None and self.history_bytes != encoded_history:
                raise ValueError("decoder history override does not match stream")
            self.history_bytes = encoded_history
            del self._buffer[:header_end]
            self._started = True

        while self._buffer and not self._finished:
            mode = self._buffer[0]

            if mode == MODE_END:
                try:
                    total, p = vdecode(bytes(self._buffer), 1)
                except ValueError as exc:
                    if "truncated" in str(exc):
                        break
                    raise
                if len(self._buffer) < p + 4:
                    break
                expected_crc = struct.unpack_from("<I", self._buffer, p)[0]
                if total != self._decoded_length:
                    raise ValueError("decoded length mismatch")
                if expected_crc != (self._crc & 0xFFFFFFFF):
                    raise ValueError("CIX checksum mismatch")
                del self._buffer[: p + 4]
                self._finished = True
                break

            try:
                source_length, p = vdecode(bytes(self._buffer), 1)
                payload_length, p = vdecode(bytes(self._buffer), p)
            except ValueError as exc:
                if "truncated" in str(exc):
                    break
                raise

            frame_end = p + payload_length
            if len(self._buffer) < frame_end:
                break

            payload = bytes(self._buffer[p:frame_end])
            del self._buffer[:frame_end]

            if mode == MODE_RAW:
                if payload_length != source_length:
                    raise ValueError("raw payload length mismatch")
                block = payload

            elif mode == MODE_MULTINOMIAL:
                block, consumed = decode_type_class_known_n(payload, 0, source_length)
                if consumed != len(payload):
                    raise ValueError("unused multinomial payload bytes")

            elif mode == MODE_CONTEXT:
                block, consumed = decode_context_type_classes(
                    payload,
                    0,
                    source_length,
                    prefix_history=bytes(self._history),
                )
                if consumed != len(payload):
                    raise ValueError("unused context payload bytes")

            elif mode == MODE_LZ:
                from .lz import decode_lz_block

                block = decode_lz_block(
                    payload,
                    source_length=source_length,
                    prefix_history=bytes(self._history),
                )

            elif mode == MODE_BWT:
                from .bwt import decode_bwt_block

                block = decode_bwt_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_TRANSFORM:
                from .transforms import decode_transform_block

                block = decode_transform_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_BITPLANE:
                from .bitplanes import decode_bitplanes

                block = decode_bitplanes(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_CHAIN:
                from .chain import decode_chain_block

                block = decode_chain_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_NUMERIC:
                from .numeric import decode_numeric_block

                block = decode_numeric_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_REFERENCE:
                distance, consumed = vdecode(payload, 0)
                if consumed != len(payload):
                    raise ValueError("unused block-reference bytes")
                if not 0 < distance <= len(self._recent_blocks):
                    raise ValueError("block reference outside retained history")
                block = self._recent_blocks[-distance]
                if len(block) != source_length:
                    raise ValueError("block-reference length mismatch")

            elif mode == MODE_ADAPTIVE:
                from .adaptive import decode_adaptive

                block = decode_adaptive(
                    payload,
                    source_length=source_length,
                    prefix_history=bytes(self._history),
                )

            elif mode == MODE_SPARSE:
                from .sparse import decode_sparse_block

                block = decode_sparse_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_RUNS:
                from .runs import decode_run_block

                block = decode_run_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_PERSISTENT_ADAPTIVE:
                if not payload:
                    raise ValueError("missing persistent adaptive model ID")
                model_id = payload[0]
                if model_id >= len(self._persistent_states):
                    raise ValueError("unknown persistent adaptive model ID")
                block = self._persistent_states[model_id].decode(
                    payload[1:],
                    source_length,
                    bytes(self._history),
                )

            elif mode == MODE_RECORD:
                from .record import decode_record_block

                block = decode_record_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_PERIODIC:
                from .periodic import decode_periodic_block

                block = decode_periodic_block(
                    payload,
                    source_length=source_length,
                )

            elif mode == MODE_PPM:
                from .ppm import decode_ppm

                block = decode_ppm(
                    payload,
                    source_length=source_length,
                    prefix_history=bytes(self._history),
                )

            elif mode == MODE_EXPERT_MIX:
                from .expertmix import decode_expert_mix

                block = decode_expert_mix(
                    payload,
                    source_length=source_length,
                    prefix_history=bytes(self._history),
                )

            elif mode == MODE_WAVELET:
                from .wavelet import decode_wavelet

                block = decode_wavelet(payload, source_length=source_length)

            elif mode == MODE_FIXED_MIX:
                from .fixedmix import decode_fixed_mix

                block = decode_fixed_mix(
                    payload,
                    source_length=source_length,
                    prefix_history=bytes(self._history),
                )

            else:
                raise ValueError(f"unknown CIX block mode {mode}")

            if len(block) != source_length:
                raise ValueError("block source length mismatch")

            prefix_history = bytes(self._history)
            for state in self._persistent_states:
                state.observe(block, prefix_history)

            out += block
            self._decoded_length += len(block)
            self._crc = zlib.crc32(block, self._crc)
            self._history.extend(block)
            assert self.history_bytes is not None
            if len(self._history) > self.history_bytes:
                del self._history[:-self.history_bytes]

            self._recent_blocks.append(block)
            if len(self._recent_blocks) > MAX_DEDUP_BLOCKS:
                del self._recent_blocks[0]

        return bytes(out)

    def finish(self) -> None:
        if not self._finished:
            raise ValueError("CIX stream ended without footer")
        if self._buffer:
            raise ValueError("trailing bytes after CIX stream")

    @property
    def finished(self) -> bool:
        return self._finished


def compress(data: bytes, config: StreamConfig | None = None) -> bytes:
    encoder = StreamEncoder(config or StreamConfig())
    return encoder.feed(data) + encoder.finish()


def decompress(blob: bytes, *, history_bytes: int | None = None) -> bytes:
    decoder = StreamDecoder(history_bytes=history_bytes)
    out = decoder.feed(blob)
    decoder.finish()
    return out
