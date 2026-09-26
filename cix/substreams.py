"""Native CIX substream coders.

Small integer streams, bucketed literal streams, match distances and other metadata are
kept separate so each can use a model matching its own distribution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .multinomial import (
    _fixed_bytes,
    _read_fixed,
    _composition_rank,
    _composition_unrank,
    combination_rank_colex,
    combination_unrank_colex,
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)


class BitWriter:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.current = 0
        self.used = 0

    def bit(self, value: int) -> None:
        self.current = (self.current << 1) | (1 if value else 0)
        self.used += 1
        if self.used == 8:
            self.buf.append(self.current)
            self.current = 0
            self.used = 0

    def bits(self, value: int, width: int) -> None:
        for shift in range(width - 1, -1, -1):
            self.bit((value >> shift) & 1)

    def finish(self) -> bytes:
        if self.used:
            self.buf.append(self.current << (8 - self.used))
        return bytes(self.buf)


class BitReader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def bit(self) -> int:
        if self.pos >= len(self.data) * 8:
            raise ValueError("truncated bitstream")
        result = (self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1
        self.pos += 1
        return result

    def bits(self, width: int) -> int:
        value = 0
        for _ in range(width):
            value = (value << 1) | self.bit()
        return value


BYTE_STREAM_STATIC = 0
BYTE_STREAM_CHUNKED = 1
BYTE_STREAM_ADAPTIVE = 2


def encode_bytes(values: bytes) -> bytes:
    """Encode a byte substream with the cheapest universal local model."""
    if not values:
        return bytes((BYTE_STREAM_STATIC,)) + encode_type_class_known_n(b"")

    candidates = [
        bytes((BYTE_STREAM_STATIC,)) + encode_type_class_known_n(values)
    ]

    # Deterministic local multinomial windows capture nonstationarity without
    # transmitting per-window lengths: count and chunk size imply every boundary.
    for chunk_size in (128, 256, 512, 1024, 2048, 4096):
        if len(values) < chunk_size * 2:
            continue
        out = bytearray((BYTE_STREAM_CHUNKED,))
        out += vencode(chunk_size)
        for start in range(0, len(values), chunk_size):
            chunk = values[start : start + chunk_size]
            out += encode_type_class_known_n(chunk)
        candidates.append(bytes(out))

    # Adaptive order-0 arithmetic is a useful competitor when the distribution
    # evolves smoothly instead of changing in sharp windows.
    if len(values) >= 256:
        try:
            from .adaptive import encode_adaptive

            payload = encode_adaptive(values, order=0, bucket_bits=8)
            candidates.append(bytes((BYTE_STREAM_ADAPTIVE,)) + payload)
        except Exception:
            pass

    return min(candidates, key=len)


def decode_bytes(blob: bytes, count: int) -> bytes:
    if not blob:
        raise ValueError("empty byte substream")
    mode = blob[0]

    if mode == BYTE_STREAM_STATIC:
        values, used = decode_type_class_known_n(blob, 1, count)
        if used != len(blob):
            raise ValueError("unused static byte-substream bytes")
        return values

    if mode == BYTE_STREAM_CHUNKED:
        chunk_size, pos = vdecode(blob, 1)
        if chunk_size <= 0:
            raise ValueError("invalid byte-substream chunk size")
        out = bytearray()
        remaining = count
        while remaining:
            n = min(chunk_size, remaining)
            chunk, pos = decode_type_class_known_n(blob, pos, n)
            out += chunk
            remaining -= n
        if pos != len(blob):
            raise ValueError("unused chunked byte-substream bytes")
        return bytes(out)

    if mode == BYTE_STREAM_ADAPTIVE:
        from .adaptive import decode_adaptive

        values = decode_adaptive(blob[1:], source_length=count)
        if len(values) != count:
            raise ValueError("adaptive byte-substream length mismatch")
        return values

    raise ValueError("unknown byte-substream mode")


UINT_VARINT = 0
UINT_RICE = 1
UINT_LOGCLASS = 2
UINT_LOGCLASS_LOCAL = 3


def encode_uints(values: list[int]) -> bytes:
    """Choose the smallest physical representation for a non-negative integer stream."""
    if any(v < 0 for v in values):
        raise ValueError("integer stream must be non-negative")
    if not values:
        return bytes((UINT_VARINT,))

    candidates: list[bytes] = []

    raw = bytearray((UINT_VARINT,))
    for value in values:
        raw += vencode(value)
    candidates.append(bytes(raw))

    best_len = len(candidates[0])
    for k in range(17):
        # Rice has q unary one-bits, one stop bit, and k low bits per value.
        # Cost it first so absurd q values under a bad numeric interpretation never
        # allocate or iterate over a catastrophically large unary stream.
        payload_limit_bits = max(0, (best_len - 2) * 8)
        bit_cost = 0
        viable = True
        for value in values:
            bit_cost += (value >> k) + 1 + k
            if bit_cost >= payload_limit_bits:
                viable = False
                break
        if not viable:
            continue

        writer = BitWriter()
        for value in values:
            quotient = value >> k
            for _ in range(quotient):
                writer.bit(1)
            writer.bit(0)
            if k:
                writer.bits(value & ((1 << k) - 1), k)
        candidate = bytes((UINT_RICE, k)) + writer.finish()
        candidates.append(candidate)
        best_len = min(best_len, len(candidate))

    classes = []
    lows = []
    widths = []
    for value in values:
        x = value + 1
        width = x.bit_length() - 1
        if width > 255:
            break
        classes.append(width)
        lows.append(x - (1 << width))
        widths.append(width)
    else:
        class_blob = encode_type_class_known_n(bytes(classes))
        writer = BitWriter()
        for low, width in zip(lows, widths):
            if width:
                writer.bits(low, width)
        candidates.append(
            bytes((UINT_LOGCLASS,))
            + vencode(len(class_blob))
            + class_blob
            + writer.finish()
        )

        local_class_blob = encode_bytes(bytes(classes))
        candidates.append(
            bytes((UINT_LOGCLASS_LOCAL,))
            + vencode(len(local_class_blob))
            + local_class_blob
            + writer.finish()
        )

    return min(candidates, key=len)


def decode_uints(blob: bytes, count: int) -> list[int]:
    if count == 0:
        return []
    if not blob:
        raise ValueError("empty integer stream")

    mode = blob[0]
    pos = 1

    if mode == UINT_VARINT:
        out = []
        for _ in range(count):
            value, pos = vdecode(blob, pos)
            out.append(value)
        if pos != len(blob):
            raise ValueError("trailing varint bytes")
        return out

    if mode == UINT_RICE:
        if pos >= len(blob):
            raise ValueError("missing Rice parameter")
        k = blob[pos]
        pos += 1
        reader = BitReader(blob[pos:])
        out = []
        for _ in range(count):
            quotient = 0
            while reader.bit():
                quotient += 1
            low = reader.bits(k) if k else 0
            out.append((quotient << k) | low)
        return out

    if mode in (UINT_LOGCLASS, UINT_LOGCLASS_LOCAL):
        class_len, pos = vdecode(blob, pos)
        end = pos + class_len
        if end > len(blob):
            raise ValueError("truncated integer class stream")
        if mode == UINT_LOGCLASS:
            classes, consumed = decode_type_class_known_n(blob[pos:end], 0, count)
            if consumed != class_len:
                raise ValueError("unused integer class bytes")
        else:
            classes = decode_bytes(blob[pos:end], count)
        reader = BitReader(blob[end:])
        out = []
        for width in classes:
            low = reader.bits(width) if width else 0
            out.append((1 << width) + low - 1)
        return out

    raise ValueError(f"unknown integer stream mode {mode}")


def encode_distances(distances: list[int], cache_size: int = 4) -> bytes:
    """Encode LZ distances using a tiny move-to-front cache plus log2 classes."""
    if any(distance <= 0 for distance in distances):
        raise ValueError("distances must be positive")
    if not distances:
        return b""

    cache: list[int] = []
    symbols = []
    lows = []
    widths = []

    for distance in distances:
        if distance in cache:
            index = cache.index(distance)
            symbols.append(index)
            lows.append(0)
            widths.append(0)
            cache.pop(index)
            cache.insert(0, distance)
        else:
            width = distance.bit_length() - 1
            symbol = cache_size + width
            if symbol > 255:
                raise ValueError("distance class too large")
            symbols.append(symbol)
            lows.append(distance - (1 << width))
            widths.append(width)
            cache.insert(0, distance)
            del cache[cache_size:]

    symbol_blob = encode_type_class_known_n(bytes(symbols))
    writer = BitWriter()
    for low, width in zip(lows, widths):
        if width:
            writer.bits(low, width)

    return vencode(len(symbol_blob)) + symbol_blob + writer.finish()


def decode_distances(blob: bytes, count: int, cache_size: int = 4) -> list[int]:
    if count == 0:
        return []

    symbol_len, pos = vdecode(blob, 0)
    end = pos + symbol_len
    if end > len(blob):
        raise ValueError("truncated distance classes")
    symbols, consumed = decode_type_class_known_n(blob[pos:end], 0, count)
    if consumed != symbol_len:
        raise ValueError("unused distance class bytes")

    reader = BitReader(blob[end:])
    cache: list[int] = []
    out = []

    for symbol in symbols:
        if symbol < cache_size:
            if symbol >= len(cache):
                raise ValueError("invalid distance cache reference")
            distance = cache.pop(symbol)
            cache.insert(0, distance)
        else:
            width = symbol - cache_size
            low = reader.bits(width) if width else 0
            distance = (1 << width) + low
            cache.insert(0, distance)
            del cache[cache_size:]
        out.append(distance)

    return out


def encode_distances_best(distances: list[int]) -> bytes:
    """Choose distance-cache size and local symbol model jointly."""
    if not distances:
        return bytes((0,))

    candidates = []
    for cache_size in (0, 1, 2, 4, 8, 16):
        cache: list[int] = []
        symbols = []
        lows = []
        widths = []

        for distance in distances:
            if distance <= 0:
                raise ValueError("distances must be positive")
            if distance in cache:
                index = cache.index(distance)
                symbols.append(index)
                lows.append(0)
                widths.append(0)
                cache.pop(index)
                cache.insert(0, distance)
            else:
                width = distance.bit_length() - 1
                symbol = cache_size + width
                if symbol > 255:
                    raise ValueError("distance class too large")
                symbols.append(symbol)
                lows.append(distance - (1 << width))
                widths.append(width)
                if cache_size:
                    cache.insert(0, distance)
                    del cache[cache_size:]

        symbol_blob = encode_bytes(bytes(symbols))
        writer = BitWriter()
        for low, width in zip(lows, widths):
            if width:
                writer.bits(low, width)

        candidate = (
            bytes((cache_size,))
            + vencode(len(symbol_blob))
            + symbol_blob
            + writer.finish()
        )
        candidates.append(candidate)

    return min(candidates, key=len)


def decode_distances_best(blob: bytes, count: int) -> list[int]:
    if count == 0:
        return []
    if not blob:
        raise ValueError("empty adaptive distance stream")

    cache_size = blob[0]
    symbol_len, pos = vdecode(blob, 1)
    end = pos + symbol_len
    if end > len(blob):
        raise ValueError("truncated adaptive distance classes")

    symbols = decode_bytes(blob[pos:end], count)
    reader = BitReader(blob[end:])
    cache: list[int] = []
    out = []

    for symbol in symbols:
        if symbol < cache_size:
            if symbol >= len(cache):
                raise ValueError("invalid adaptive distance cache reference")
            distance = cache.pop(symbol)
            cache.insert(0, distance)
        else:
            width = symbol - cache_size
            low = reader.bits(width) if width else 0
            distance = (1 << width) + low
            if cache_size:
                cache.insert(0, distance)
                del cache[cache_size:]
        out.append(distance)

    return out


def encode_bucketed_type_classes(
    buckets: dict[int, bytes | bytearray],
    *,
    bucket_count: int,
    total_items: int,
) -> bytes:
    """Encode sparse bucket IDs, their lengths, then each bucket's type class."""
    ids = sorted(bucket for bucket, values in buckets.items() if values)
    q = len(ids)
    if sum(len(buckets[bucket]) for bucket in ids) != total_items:
        raise ValueError("bucket lengths do not sum to total")
    if q > min(bucket_count, total_items):
        raise ValueError("too many active buckets")

    out = bytearray(vencode(q))
    if q and q < bucket_count:
        width = (math.comb(bucket_count, q) - 1).bit_length()
        out += _fixed_bytes(combination_rank_colex(ids), width)

    lengths = [len(buckets[bucket]) for bucket in ids]
    if q > 1:
        width = (math.comb(total_items - 1, q - 1) - 1).bit_length()
        out += _fixed_bytes(_composition_rank(lengths), width)

    for bucket in ids:
        out += encode_type_class_known_n(bytes(buckets[bucket]))
    return bytes(out)


def decode_bucketed_type_classes(
    blob: bytes,
    pos: int,
    *,
    bucket_count: int,
    total_items: int,
) -> tuple[dict[int, bytes], int]:
    q, pos = vdecode(blob, pos)
    if q > min(bucket_count, total_items):
        raise ValueError("invalid active bucket count")

    if q == 0:
        if total_items:
            raise ValueError("non-empty stream has no active buckets")
        return {}, pos

    if q == bucket_count:
        ids = list(range(bucket_count))
    else:
        width = (math.comb(bucket_count, q) - 1).bit_length()
        rank, pos = _read_fixed(blob, pos, width)
        ids = combination_unrank_colex(rank, q, bucket_count)

    if q == 1:
        lengths = [total_items]
    else:
        width = (math.comb(total_items - 1, q - 1) - 1).bit_length()
        rank, pos = _read_fixed(blob, pos, width)
        lengths = _composition_unrank(rank, total_items, q)

    streams: dict[int, bytes] = {}
    for bucket, length in zip(ids, lengths):
        stream, pos = decode_type_class_known_n(blob, pos, length)
        streams[bucket] = stream

    return streams, pos
