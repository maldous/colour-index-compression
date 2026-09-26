"""Native LZ match model whose outputs are CIX substreams."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .multinomial import (
    ContextModel,
    _context_bucket,
    decode_type_class_known_n,
    encode_type_class_known_n,
    vdecode,
    vencode,
)
from .substreams import (
    decode_bucketed_type_classes,
    decode_distances,
    decode_uints,
    encode_bucketed_type_classes,
    encode_distances,
    encode_uints,
)

LZ_VERSION = 1
DEFAULT_MIN_MATCH = 4
DEFAULT_MAX_MATCH = 65535


@dataclass
class LZParse:
    tags: bytes
    literals: bytes
    literal_positions: list[int]
    lengths: list[int]
    distances: list[int]


def _context_tail(prefix: bytes, data: bytes | bytearray, pos: int, order: int) -> bytes:
    if order <= 0:
        return b""
    if pos >= order:
        return bytes(data[pos - order : pos])
    missing = order - pos
    return prefix[-missing:] + bytes(data[:pos])


def parse_lz(
    data: bytes,
    *,
    prefix_history: bytes = b"",
    min_match: int = DEFAULT_MIN_MATCH,
    max_match: int = DEFAULT_MAX_MATCH,
    window: int = 1 << 20,
    chain: int = 32,
    key_len: int = 4,
) -> LZParse:
    if key_len < 3:
        raise ValueError("key_len must be at least 3")
    if min_match < key_len:
        min_match = key_len

    history = prefix_history[-window:]
    base = history + data
    history_len = len(history)
    end = len(base)
    table: dict[bytes, list[int]] = defaultdict(list)

    seed_start = max(0, history_len - window)
    seed_end = max(seed_start, history_len - key_len + 1)
    for position in range(seed_start, seed_end):
        key = base[position : position + key_len]
        entries = table[key]
        entries.append(position)
        if len(entries) > chain:
            del entries[0]

    tags = bytearray()
    literals = bytearray()
    literal_positions = []
    lengths = []
    distances = []

    position = history_len
    while position < end:
        best_length = 0
        best_distance = 0

        if position + key_len <= end:
            key = base[position : position + key_len]
            for candidate in reversed(table.get(key, ())[-chain:]):
                distance = position - candidate
                if not 0 < distance <= window:
                    continue

                limit = min(max_match, end - position)
                match_length = key_len
                while (
                    match_length < limit
                    and base[position - distance + match_length]
                    == base[position + match_length]
                ):
                    match_length += 1

                if match_length > best_length:
                    best_length = match_length
                    best_distance = distance
                    if best_length == limit:
                        break

        if best_length >= min_match:
            tags.append(1)
            lengths.append(best_length - min_match)
            distances.append(best_distance)

            stop = min(end, position + best_length)
            for p in range(position, stop):
                if p + key_len <= end:
                    key = base[p : p + key_len]
                    entries = table[key]
                    entries.append(p)
                    if len(entries) > chain:
                        del entries[0]
            position += best_length

        else:
            tags.append(0)
            literals.append(base[position])
            literal_positions.append(position - history_len)

            if position + key_len <= end:
                key = base[position : position + key_len]
                entries = table[key]
                entries.append(position)
                if len(entries) > chain:
                    del entries[0]
            position += 1

    return LZParse(
        bytes(tags),
        bytes(literals),
        literal_positions,
        lengths,
        distances,
    )


def _encode_literals(
    parse: LZParse,
    source: bytes,
    prefix_history: bytes,
    context_models: tuple[ContextModel, ...],
) -> tuple[bytes, str]:
    plain = bytes((0,)) + encode_type_class_known_n(parse.literals)
    candidates = [(plain, "literal-multinomial")]

    for model in context_models:
        bucket_count = 1 << model.bucket_bits
        buckets: dict[int, bytearray] = {}

        for literal, position in zip(parse.literals, parse.literal_positions):
            tail = _context_tail(prefix_history, source, position, model.order)
            bucket = _context_bucket(tail, model.order, model.bucket_bits)
            buckets.setdefault(bucket, bytearray()).append(literal)

        payload = (
            bytes((1, model.order, model.bucket_bits))
            + encode_bucketed_type_classes(
                buckets,
                bucket_count=bucket_count,
                total_items=len(parse.literals),
            )
        )
        candidates.append(
            (
                payload,
                f"literal-context-o{model.order}-b{model.bucket_bits}",
            )
        )

    return min(candidates, key=lambda item: len(item[0]))


@dataclass
class LiteralDecoder:
    mode: int
    plain: bytes | None = None
    streams: dict[int, bytes] | None = None
    cursors: dict[int, int] | None = None
    order: int = 0
    bucket_bits: int = 0
    plain_pos: int = 0

    def next(self, prefix: bytes, produced: bytearray) -> int:
        if self.mode == 0:
            assert self.plain is not None
            if self.plain_pos >= len(self.plain):
                raise ValueError("literal stream exhausted")
            value = self.plain[self.plain_pos]
            self.plain_pos += 1
            return value

        assert self.streams is not None and self.cursors is not None
        tail = _context_tail(prefix, produced, len(produced), self.order)
        bucket = _context_bucket(tail, self.order, self.bucket_bits)
        stream = self.streams.get(bucket)
        if stream is None:
            raise ValueError("literal context selected absent bucket")
        cursor = self.cursors[bucket]
        if cursor >= len(stream):
            raise ValueError("literal context bucket exhausted")
        self.cursors[bucket] = cursor + 1
        return stream[cursor]


def _decode_literals(blob: bytes, count: int) -> LiteralDecoder:
    if not blob:
        raise ValueError("empty literal stream")
    mode = blob[0]

    if mode == 0:
        plain, pos = decode_type_class_known_n(blob, 1, count)
        if pos != len(blob):
            raise ValueError("unused literal bytes")
        return LiteralDecoder(mode=0, plain=plain)

    if mode == 1:
        if len(blob) < 3:
            raise ValueError("truncated literal context parameters")
        order = blob[1]
        bucket_bits = blob[2]
        streams, pos = decode_bucketed_type_classes(
            blob,
            3,
            bucket_count=1 << bucket_bits,
            total_items=count,
        )
        if pos != len(blob):
            raise ValueError("unused literal-context bytes")
        return LiteralDecoder(
            mode=1,
            streams=streams,
            cursors={bucket: 0 for bucket in streams},
            order=order,
            bucket_bits=bucket_bits,
        )

    raise ValueError(f"unknown literal mode {mode}")


def encode_lz_block(
    data: bytes,
    *,
    prefix_history: bytes = b"",
    context_models: tuple[ContextModel, ...] = (),
    window: int = 1 << 20,
    chain: int = 32,
    min_match: int = DEFAULT_MIN_MATCH,
) -> tuple[bytes, str]:
    parse = parse_lz(
        data,
        prefix_history=prefix_history,
        min_match=min_match,
        window=window,
        chain=chain,
    )

    tags = encode_type_class_known_n(parse.tags)
    literals, literal_name = _encode_literals(
        parse, data, prefix_history, context_models
    )
    lengths = encode_uints(parse.lengths)
    distances = encode_distances(parse.distances)

    out = bytearray((LZ_VERSION, min_match))
    out += vencode(len(parse.tags))
    out += vencode(len(parse.literals))
    out += vencode(len(parse.lengths))

    for stream in (tags, literals, lengths, distances):
        out += vencode(len(stream))
        out += stream

    return (
        bytes(out),
        f"lz-{literal_name}-m{min_match}-w{window}-c{chain}",
    )


def decode_lz_block(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 2 or blob[0] != LZ_VERSION:
        raise ValueError("unknown LZ block version")

    min_match = blob[1]
    pos = 2
    token_count, pos = vdecode(blob, pos)
    literal_count, pos = vdecode(blob, pos)
    match_count, pos = vdecode(blob, pos)

    streams = []
    for _ in range(4):
        length, pos = vdecode(blob, pos)
        end = pos + length
        if end > len(blob):
            raise ValueError("truncated LZ substream")
        streams.append(blob[pos:end])
        pos = end
    if pos != len(blob):
        raise ValueError("trailing LZ block bytes")

    tags, consumed = decode_type_class_known_n(streams[0], 0, token_count)
    if consumed != len(streams[0]):
        raise ValueError("unused LZ tag bytes")

    literals = _decode_literals(streams[1], literal_count)
    lengths = decode_uints(streams[2], match_count)
    distances = decode_distances(streams[3], match_count)

    produced = bytearray()
    literal_used = 0
    match_used = 0

    for tag in tags:
        if tag == 0:
            produced.append(literals.next(prefix_history, produced))
            literal_used += 1
        elif tag == 1:
            if match_used >= match_count:
                raise ValueError("LZ match stream exhausted")
            length = lengths[match_used] + min_match
            distance = distances[match_used]
            match_used += 1

            for _ in range(length):
                available = len(prefix_history) + len(produced)
                source = available - distance
                if source < 0:
                    raise ValueError("LZ distance before available history")
                if source < len(prefix_history):
                    value = prefix_history[source]
                else:
                    value = produced[source - len(prefix_history)]
                produced.append(value)
                if len(produced) > source_length:
                    raise ValueError("LZ block expands beyond source length")
        else:
            raise ValueError("invalid LZ tag")

    if len(produced) != source_length:
        raise ValueError("LZ decoded length mismatch")
    if literal_used != literal_count or match_used != match_count:
        raise ValueError("unused LZ tokens")

    if literals.mode == 0:
        if literals.plain_pos != literal_count:
            raise ValueError("unused literal symbols")
    else:
        assert literals.streams is not None and literals.cursors is not None
        if any(
            literals.cursors[bucket] != len(stream)
            for bucket, stream in literals.streams.items()
        ):
            raise ValueError("unused literal-context symbols")

    return bytes(produced)
