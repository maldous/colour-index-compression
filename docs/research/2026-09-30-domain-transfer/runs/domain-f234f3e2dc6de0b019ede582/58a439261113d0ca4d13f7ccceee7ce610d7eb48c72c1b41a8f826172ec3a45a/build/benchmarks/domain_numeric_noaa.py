"""Strict reversible NOAA water-level numerical packing experiment.

This intentionally handles one declared CSV schema.  It does not identify a
file by name: callers must select the variant explicitly and unsupported bytes
are rejected rather than silently transformed.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re

from cix.multinomial import vdecode, vencode


MAGIC = b"DNM1"
RULES = b"noaa-water-level-csv-v1;canonical-lf-decimal;timestamp-delta;decimal-delta;five-digit-flags;quality-byte;meta-base160000"
HEADER = b"Date Time, Water Level, Sigma, O or I (for verified), F, R, L, Quality \n"
VARIANTS = {"numeric-delta-columns-v1": 1, "numeric-delta-rows-v1": 2,
            "numeric-delta-columns-packed-meta-v1": 3}
NAMES = {value: key for key, value in VARIANTS.items()}
ROW = re.compile(br"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}),(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(\d),(\d),(\d),(\d),([^,\r\n])\n")
META_BASE = 160000


def _pack(value: bytes) -> bytes:
    return vencode(len(value)) + value


def _read(blob: bytes, pos: int) -> tuple[bytes, int]:
    size, pos = vdecode(blob, pos)
    if size > len(blob) or pos + size > len(blob):
        raise ValueError("truncated numerical frame")
    return blob[pos:pos + size], pos + size


def _fold(value: int) -> int:
    return value * 2 if value >= 0 else -value * 2 - 1


def _unfold(value: int) -> int:
    return value // 2 if value % 2 == 0 else -(value // 2) - 1


def _decimal(token: bytes) -> tuple[int, int]:
    sign = -1 if token.startswith(b"-") else 1
    raw = token[1:] if token[:1] in (b"-", b"+") else token
    whole, dot, fraction = raw.partition(b".")
    places = len(fraction) if dot else 0
    if places > 3 or not whole.isdigit() or (fraction and not fraction.isdigit()):
        raise ValueError("unsupported decimal token")
    if len(whole) > 1 and whole.startswith(b"0"):
        raise ValueError("noncanonical decimal leading zero")
    value = int((whole + fraction.ljust(3, b"0")) or b"0")
    if sign < 0 and value == 0:
        raise ValueError("noncanonical negative zero")
    return sign * value, places


def _format_decimal(value: int, places: int) -> bytes:
    if not 0 <= places <= 3:
        raise ValueError("invalid decimal precision")
    sign = b"-" if value < 0 else b""
    value = abs(value); whole, fraction = divmod(value, 1000)
    if places == 0:
        if fraction:
            raise ValueError("nonintegral zero-place decimal")
        return sign + str(whole).encode()
    return sign + str(whole).encode() + b"." + f"{fraction:03d}".encode()[:places]


def _parse(data: bytes) -> list[tuple[datetime, int, int, int, int, int, int, int, bytes]]:
    if not data.startswith(HEADER):
        raise ValueError("unsupported NOAA header")
    rows = []
    for raw in data[len(HEADER):].splitlines(keepends=True):
        match = ROW.fullmatch(raw)
        if match is None:
            raise ValueError("unsupported NOAA row")
        timestamp = datetime.strptime(match.group(1).decode(), "%Y-%m-%d %H:%M")
        water, water_places = _decimal(match.group(2)); sigma, sigma_places = _decimal(match.group(3))
        flags = tuple(int(match.group(index)) for index in range(4, 8))
        quality = match.group(8)
        rows.append((timestamp, water, sigma, water_places, sigma_places, *flags, quality))
    if not rows:
        raise ValueError("empty NOAA input")
    return rows


def inspect(data: bytes) -> dict:
    rows = _parse(data)
    minutes = [int((row[0] - rows[0][0]).total_seconds() // 60) for row in rows]
    water = [row[1] for row in rows]
    sigma = [row[2] for row in rows]
    return {"rules": RULES.decode(), "records": len(rows), "header_bytes": len(HEADER),
            "timestamp_delta_min": min(b - a for a, b in zip(minutes, minutes[1:])) if len(rows) > 1 else None,
            "timestamp_delta_max": max(b - a for a, b in zip(minutes, minutes[1:])) if len(rows) > 1 else None,
            "water_delta_distinct": len({b - a for a, b in zip(water, water[1:])}),
            "sigma_delta_distinct": len({b - a for a, b in zip(sigma, sigma[1:])}),
            "water_precision_values": sorted({row[3] for row in rows}),
            "sigma_precision_values": sorted({row[4] for row in rows}),
            "quality_values": sorted({row[-1].decode('ascii') for row in rows}),
            "raw_precision_and_flag_bytes": len(rows) * 6,
            "packed_precision_and_flag_bytes": ((META_BASE ** len(rows) - 1).bit_length() + 7) // 8,
            "fixed_width_metadata_recovery_bytes": len(rows) * 6 - ((META_BASE ** len(rows) - 1).bit_length() + 7) // 8}


def _numbers(values: list[int], places: list[int]) -> bytes:
    out = bytearray()
    previous = 0
    for value, place in zip(values, places):
        out.append(place); out.extend(vencode(_fold(value - previous))); previous = value
    return bytes(out)


def _read_numbers(blob: bytes, count: int) -> tuple[list[int], list[int]]:
    values = []; places = []; pos = previous = 0
    for _ in range(count):
        if pos >= len(blob) or blob[pos] > 3:
            raise ValueError("invalid numerical precision")
        place = blob[pos]; pos += 1
        delta, pos = vdecode(blob, pos); previous += _unfold(delta)
        values.append(previous); places.append(place)
    if pos != len(blob):
        raise ValueError("trailing numerical values")
    return values, places


def _number_deltas(values: list[int]) -> bytes:
    out = bytearray(); previous = 0
    for value in values:
        out.extend(vencode(_fold(value - previous))); previous = value
    return bytes(out)


def _read_number_deltas(blob: bytes, count: int) -> list[int]:
    out = []; previous = pos = 0
    for _ in range(count):
        delta, pos = vdecode(blob, pos); previous += _unfold(delta); out.append(previous)
    if pos != len(blob):
        raise ValueError("trailing numerical deltas")
    return out


def _timestamps(rows) -> bytes:
    out = bytearray(rows[0][0].strftime("%Y-%m-%d %H:%M").encode())
    previous = rows[0][0]
    for row in rows[1:]:
        delta = int((row[0] - previous).total_seconds() // 60)
        out.extend(vencode(_fold(delta))); previous = row[0]
    return bytes(out)


def _read_timestamps(blob: bytes, count: int) -> list[datetime]:
    if len(blob) < 16:
        raise ValueError("truncated initial timestamp")
    current = datetime.strptime(blob[:16].decode(), "%Y-%m-%d %H:%M"); pos = 16; out = [current]
    for _ in range(count - 1):
        delta, pos = vdecode(blob, pos); current += timedelta(minutes=_unfold(delta)); out.append(current)
    if pos != len(blob):
        raise ValueError("trailing timestamp values")
    return out


def _flags(rows) -> bytes:
    return bytes(value for row in rows for value in row[5:9]) + b"".join(row[9] for row in rows)


def _read_flags(blob: bytes, count: int):
    if len(blob) != count * 5:
        raise ValueError("invalid flag stream")
    return [(*blob[4 * index:4 * index + 4], blob[4 * count + index:4 * count + index + 1])
            for index in range(count)]


def _pack_metadata(rows) -> bytes:
    rank = 0
    for row in rows:
        digit = (((((row[3] * 4 + row[4]) * 10 + row[5]) * 10 + row[6]) * 10 + row[7]) * 10 + row[8])
        rank = rank * META_BASE + digit
    width = ((META_BASE ** len(rows) - 1).bit_length() + 7) // 8
    return rank.to_bytes(width, "big")


def _read_metadata(blob: bytes, count: int):
    width = ((META_BASE ** count - 1).bit_length() + 7) // 8
    if len(blob) != width:
        raise ValueError("invalid packed metadata length")
    rank = int.from_bytes(blob, "big")
    if rank >= META_BASE ** count:
        raise ValueError("packed metadata rank outside range")
    result = [None] * count
    for index in range(count - 1, -1, -1):
        rank, digit = divmod(rank, META_BASE)
        flags = [0] * 4
        for slot in range(3, -1, -1):
            digit, flags[slot] = divmod(digit, 10)
        water_places, sigma_places = divmod(digit, 4)
        result[index] = (water_places, sigma_places, *flags)
    return result


def encode(data: bytes, variant: str) -> bytes:
    if variant not in VARIANTS:
        raise ValueError("unsupported numerical variant")
    rows = _parse(data); count = len(rows)
    times = _timestamps(rows)
    if variant == "numeric-delta-columns-v1":
        # This is the structural candidate: values and their lexical decimal
        # precision stay in their respective causal delta streams.
        water = _numbers([row[1] for row in rows], [row[3] for row in rows])
        sigma = _numbers([row[2] for row in rows], [row[4] for row in rows])
        flags = _flags(rows)
        streams = (times, water, sigma, flags)
        payload = b"".join(_pack(value) for value in streams)
    elif variant == "numeric-delta-columns-packed-meta-v1":
        # Same column/delta representation, with only the six bounded
        # metadata digits per row packed together.  Numerical values remain
        # ordinary delta streams; this is not a rank coder for their values.
        water = _number_deltas([row[1] for row in rows])
        sigma = _number_deltas([row[2] for row in rows])
        metadata = _pack_metadata(rows)
        quality = b"".join(row[9] for row in rows)
        payload = b"".join(_pack(value) for value in (times, water, sigma, metadata, quality))
    else:
        # Preserved layout ablation.  Its per-record framing deliberately
        # changes PAQ adjacency and cannot establish recovered packing gain.
        records = bytearray(); prior_time = rows[0][0]; prior_water = prior_sigma = 0
        for index, row in enumerate(rows):
            record = bytearray()
            if index == 0:
                record.extend(row[0].strftime("%Y-%m-%d %H:%M").encode())
            else:
                record.extend(vencode(_fold(int((row[0] - prior_time).total_seconds() // 60))))
            record.append(row[3]); record.extend(vencode(_fold(row[1] - prior_water)))
            record.append(row[4]); record.extend(vencode(_fold(row[2] - prior_sigma)))
            record.extend(bytes(row[5:9]) + row[9])
            records.extend(_pack(bytes(record)))
            prior_time, prior_water, prior_sigma = row[0], row[1], row[2]
        payload = bytes(records)
    return MAGIC + bytes((VARIANTS[variant],)) + vencode(len(data)) + _pack(RULES) + _pack(HEADER) + vencode(count) + payload


def decode(frame: bytes) -> bytes:
    if not frame.startswith(MAGIC) or len(frame) <= len(MAGIC):
        raise ValueError("invalid numerical frame")
    variant = NAMES.get(frame[len(MAGIC)])
    if variant is None:
        raise ValueError("unsupported numerical variant")
    original, pos = vdecode(frame, len(MAGIC) + 1)
    rules, pos = _read(frame, pos)
    header, pos = _read(frame, pos)
    if rules != RULES or header != HEADER:
        raise ValueError("unsupported numerical rules")
    count, pos = vdecode(frame, pos)
    if not count:
        raise ValueError("trailing numerical frame")
    if variant == "numeric-delta-columns-v1":
        streams = []
        for _ in range(4):
            value, pos = _read(frame, pos); streams.append(value)
        times = _read_timestamps(streams[0], count)
        water, water_places = _read_numbers(streams[1], count)
        sigma, sigma_places = _read_numbers(streams[2], count)
        flags = _read_flags(streams[3], count)
    elif variant == "numeric-delta-columns-packed-meta-v1":
        streams = []
        for _ in range(5):
            value, pos = _read(frame, pos); streams.append(value)
        times = _read_timestamps(streams[0], count)
        water = _read_number_deltas(streams[1], count)
        sigma = _read_number_deltas(streams[2], count)
        metadata = _read_metadata(streams[3], count)
        quality = streams[4]
        if len(quality) != count:
            raise ValueError("invalid packed quality stream")
        water_places = [value[0] for value in metadata]
        sigma_places = [value[1] for value in metadata]
        flags = [(*value[2:6], quality[index:index + 1]) for index, value in enumerate(metadata)]
    else:
        times = []; water = []; sigma = []; water_places = []; sigma_places = []; flags = []
        prior_time = prior_water = prior_sigma = None
        for index in range(count):
            record, pos = _read(frame, pos)
            if index == 0:
                if len(record) < 16:
                    raise ValueError("truncated initial row timestamp")
                timestamp = datetime.strptime(record[:16].decode(), "%Y-%m-%d %H:%M"); at = 16
            else:
                delta, at = vdecode(record, 0); timestamp = prior_time + timedelta(minutes=_unfold(delta))
            if at + 2 > len(record):
                raise ValueError("truncated numerical row")
            wp = record[at]; at += 1; delta, at = vdecode(record, at); value = (prior_water or 0) + _unfold(delta)
            sp = record[at]; at += 1; delta, at = vdecode(record, at); deviation = (prior_sigma or 0) + _unfold(delta)
            if wp > 3 or sp > 3 or at + 5 != len(record):
                raise ValueError("invalid numerical row")
            flag = (*record[at:at + 4], record[at + 4:at + 5])
            times.append(timestamp); water.append(value); sigma.append(deviation); water_places.append(wp); sigma_places.append(sp); flags.append(flag)
            prior_time, prior_water, prior_sigma = timestamp, value, deviation
    if pos != len(frame):
        raise ValueError("trailing numerical frame")
    out = bytearray(HEADER)
    for row in zip(times, water, sigma, water_places, sigma_places, flags):
        timestamp, w, s, wp, sp, flag = row
        out.extend(timestamp.strftime("%Y-%m-%d %H:%M").encode() + b"," + _format_decimal(w, wp) + b"," + _format_decimal(s, sp)
                   + b"," + b",".join(str(value).encode() for value in flag[:4]) + b"," + flag[4] + b"\n")
    if len(out) != original:
        raise ValueError("numerical restored size mismatch")
    return bytes(out)
