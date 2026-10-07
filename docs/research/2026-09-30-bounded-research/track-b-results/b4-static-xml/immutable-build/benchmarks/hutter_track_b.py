#!/usr/bin/env python3
"""Bounded Hutter-specific representation experiments.

This module deliberately keeps its two representation candidates separate from
generic CIX.  Both write a self-contained ``HTB1`` archive and can restore it
in a fresh process using only that archive.  The matched control is the same
pinned zstandard backend applied directly to the input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import zstandard as zstd
import zstandard.backend_c as zstd_backend_c


MAGIC = b"HTB1"
DIRECT, SPACE_MASK, LINE_PREFIX, COPY_DELTA, STATIC_XML = 0, 1, 2, 3, 4
MODES = {"control": DIRECT, "space-mask": SPACE_MASK, "line-prefix": LINE_PREFIX, "copy-delta": COPY_DELTA, "static-xml": STATIC_XML}
XML_TOKENS = tuple(sorted((
    b'<text xml:space="preserve">', b'</contributor>', b'<contributor>', b'</revision>',
    b'<timestamp>', b'</timestamp>', b'</username>', b'<username>', b'</comment>',
    b'<revision>', b'</title>', b'<title>', b'</page>', b'<page>', b'<comment>',
    b'<minor />', b'&quot;', b'&amp;', b'&lt;', b'&gt;',
), key=lambda token: (-len(token), token)))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative varint")
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def decode_varint(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while position < len(data) and shift < 70:
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, position
        shift += 7
    raise ValueError("invalid/truncated varint")


def split_space_mask(data: bytes) -> tuple[bytes, bytes]:
    """Separate the fixed, decoder-known ASCII-space membership predicate."""
    mask = bytearray((len(data) + 7) // 8)
    literals = bytearray()
    for index, byte in enumerate(data):
        if byte == 0x20:
            mask[index >> 3] |= 1 << (index & 7)
        else:
            literals.append(byte)
    return bytes(mask), bytes(literals)


def join_space_mask(mask: bytes, literals: bytes, original_bytes: int) -> bytes:
    if len(mask) != (original_bytes + 7) // 8:
        raise ValueError("mask length does not match original length")
    output = bytearray()
    literal_position = 0
    for index in range(original_bytes):
        if mask[index >> 3] & (1 << (index & 7)):
            output.append(0x20)
        else:
            if literal_position == len(literals):
                raise ValueError("truncated literal stream")
            output.append(literals[literal_position])
            literal_position += 1
    if literal_position != len(literals):
        raise ValueError("trailing literal stream")
    return bytes(output)


def common_prefix(left: bytes, right: bytes) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


def line_prefix_transform(data: bytes) -> bytes:
    """Encode each newline-delimited record as prefix length plus changed suffix.

    This is a fixed reversible edit model: it supplies no dictionary and charges
    every prefix length and suffix length in the transformed byte stream.
    """
    previous = b""
    output = bytearray()
    for line in data.split(b"\n"):
        prefix = common_prefix(previous, line)
        suffix = line[prefix:]
        output += encode_varint(prefix)
        output += encode_varint(len(suffix))
        output += suffix
        previous = line
    return bytes(output)


def inverse_line_prefix(transformed: bytes) -> bytes:
    position = 0
    previous = b""
    lines: list[bytes] = []
    while position < len(transformed):
        prefix, position = decode_varint(transformed, position)
        suffix_bytes, position = decode_varint(transformed, position)
        if prefix > len(previous) or position + suffix_bytes > len(transformed):
            raise ValueError("invalid line-prefix stream")
        line = previous[:prefix] + transformed[position : position + suffix_bytes]
        position += suffix_bytes
        lines.append(line)
        previous = line
    if not lines:
        raise ValueError("line-prefix stream lacks an initial record")
    return b"\n".join(lines)


def copy_delta_transform(data: bytes, block_bytes: int = 1024, window_bytes: int = 65536) -> tuple[bytes, dict[str, int]]:
    """Causal bounded near-match references, expressed as fully charged XOR edits.

    A block may refer only to bytes before its start.  A 64-byte-spaced 8-byte
    anchor table picks one causal candidate; the record stores its distance,
    complete block length and every XOR edit byte.  This deliberately avoids
    hidden match state: the decoder can recreate the reference from output
    already restored from the archive.
    """
    output = bytearray()
    anchors: dict[bytes, int] = {}
    copied_blocks = 0
    raw_blocks = 0
    equal_bytes = 0
    for start in range(0, len(data), block_bytes):
        block = data[start : start + block_bytes]
        candidate_start = None
        candidate_equal = 0
        for relative in range(0, max(0, len(block) - 7), 64):
            anchor = block[relative : relative + 8]
            anchor_position = anchors.get(anchor)
            if anchor_position is None:
                continue
            reference_start = anchor_position - relative
            if reference_start < max(0, start - window_bytes) or reference_start + len(block) > start:
                continue
            reference = data[reference_start : reference_start + len(block)]
            matches = sum(left == right for left, right in zip(block, reference))
            if matches > candidate_equal:
                candidate_start, candidate_equal = reference_start, matches
        if candidate_start is not None and candidate_equal * 8 >= len(block):
            reference = data[candidate_start : candidate_start + len(block)]
            output.append(1)
            output += encode_varint(len(block))
            output += encode_varint(start - candidate_start)
            output += bytes(left ^ right for left, right in zip(block, reference))
            copied_blocks += 1
            equal_bytes += candidate_equal
        else:
            output.append(0)
            output += encode_varint(len(block))
            output += block
            raw_blocks += 1
        for relative in range(0, max(0, len(block) - 7), 64):
            anchors[block[relative : relative + 8]] = start + relative
        # Keep the bounded table causal and compact.  Stale anchors are harmless
        # but must never be selected outside the explicit window.
    return bytes(output), {"copy_delta_block_bytes": block_bytes, "copy_delta_window_bytes": window_bytes,
                            "copy_delta_copied_blocks": copied_blocks, "copy_delta_raw_blocks": raw_blocks,
                            "copy_delta_equal_bytes": equal_bytes}


def inverse_copy_delta(transformed: bytes) -> bytes:
    position = 0
    output = bytearray()
    while position < len(transformed):
        marker = transformed[position]
        position += 1
        block_bytes, position = decode_varint(transformed, position)
        if marker == 0:
            if position + block_bytes > len(transformed):
                raise ValueError("truncated copy-delta raw record")
            output += transformed[position : position + block_bytes]
            position += block_bytes
        elif marker == 1:
            distance, position = decode_varint(transformed, position)
            if not distance or distance > len(output) or position + block_bytes > len(transformed):
                raise ValueError("invalid copy-delta reference")
            reference_start = len(output) - distance
            if reference_start + block_bytes > len(output):
                raise ValueError("non-causal copy-delta reference")
            edits = transformed[position : position + block_bytes]
            position += block_bytes
            output += bytes(left ^ right for left, right in zip(output[reference_start : reference_start + block_bytes], edits))
        else:
            raise ValueError("unknown copy-delta record")
    return bytes(output)


def static_xml_transform(data: bytes) -> tuple[bytes, dict[str, int]]:
    """Replace a fixed XML grammar vocabulary with self-delimiting byte tokens.

    This is intentionally not a learnt dictionary: the ordered vocabulary is
    part of the named Hutter-specific decoder configuration.  ``0xff`` escapes
    raw occurrences of itself; every recognized construct is two bytes (escape
    plus stable vocabulary index), so all representation costs are in the
    backend input and no side stream is hidden.
    """
    output = bytearray()
    position = 0
    replacements = 0
    while position < len(data):
        matched = next((index for index, token in enumerate(XML_TOKENS, 1) if data.startswith(token, position)), None)
        if matched is not None:
            output.extend((0xff, matched))
            position += len(XML_TOKENS[matched - 1])
            replacements += 1
        elif data[position] == 0xff:
            output.extend((0xff, 0xff))
            position += 1
        else:
            output.append(data[position])
            position += 1
    return bytes(output), {"static_xml_vocabulary_entries": len(XML_TOKENS), "static_xml_replacements": replacements}


def inverse_static_xml(transformed: bytes) -> bytes:
    output = bytearray()
    position = 0
    while position < len(transformed):
        byte = transformed[position]
        position += 1
        if byte != 0xff:
            output.append(byte)
            continue
        if position == len(transformed):
            raise ValueError("truncated static-xml escape")
        code = transformed[position]
        position += 1
        if code == 0xff:
            output.append(0xff)
        elif 1 <= code <= len(XML_TOKENS):
            output += XML_TOKENS[code - 1]
        else:
            raise ValueError("invalid static-xml token")
    return bytes(output)


def encode_archive(data: bytes, mode: str, level: int = 19) -> tuple[bytes, dict[str, int]]:
    compressor = zstd.ZstdCompressor(level=level)
    original_header = MAGIC + bytes((MODES[mode],)) + encode_varint(len(data))
    if mode == "control":
        payload = compressor.compress(data)
        archive = original_header + encode_varint(len(payload)) + payload
        return archive, {"payload_bytes": len(payload), "metadata_bytes": 0,
                         "framing_bytes": len(archive) - len(payload), "transformed_bytes": len(data)}
    if mode == "space-mask":
        mask, literals = split_space_mask(data)
        packed_mask = compressor.compress(mask)
        packed_literals = compressor.compress(literals)
        archive = original_header + encode_varint(len(packed_mask)) + encode_varint(len(packed_literals)) + packed_mask + packed_literals
        return archive, {"payload_bytes": len(packed_mask) + len(packed_literals), "metadata_bytes": 0,
                         "framing_bytes": len(archive) - len(packed_mask) - len(packed_literals),
                         "transformed_bytes": len(mask) + len(literals), "mask_bytes": len(mask),
                         "literal_bytes": len(literals)}
    if mode == "line-prefix":
        transformed = line_prefix_transform(data)
        transform_costs: dict[str, int] = {}
    elif mode == "copy-delta":
        transformed, transform_costs = copy_delta_transform(data)
    else:
        transformed, transform_costs = static_xml_transform(data)
    payload = compressor.compress(transformed)
    archive = original_header + encode_varint(len(payload)) + payload
    return archive, {"payload_bytes": len(payload), "metadata_bytes": 0,
                     "framing_bytes": len(archive) - len(payload), "transformed_bytes": len(transformed), **transform_costs}


def decode_archive(archive: bytes) -> bytes:
    if len(archive) < 5 or archive[:4] != MAGIC:
        raise ValueError("not an HTB1 archive")
    mode = archive[4]
    original_bytes, position = decode_varint(archive, 5)
    decompressor = zstd.ZstdDecompressor()
    if mode in (DIRECT, LINE_PREFIX, COPY_DELTA, STATIC_XML):
        payload_bytes, position = decode_varint(archive, position)
        if position + payload_bytes != len(archive):
            raise ValueError("invalid payload boundary")
        restored = decompressor.decompress(archive[position:])
        if mode == LINE_PREFIX:
            restored = inverse_line_prefix(restored)
        elif mode == COPY_DELTA:
            restored = inverse_copy_delta(restored)
        elif mode == STATIC_XML:
            restored = inverse_static_xml(restored)
    elif mode == SPACE_MASK:
        mask_bytes, position = decode_varint(archive, position)
        literals_bytes, position = decode_varint(archive, position)
        if position + mask_bytes + literals_bytes != len(archive):
            raise ValueError("invalid split payload boundaries")
        mask = decompressor.decompress(archive[position : position + mask_bytes])
        literals = decompressor.decompress(archive[position + mask_bytes :])
        restored = join_space_mask(mask, literals, original_bytes)
    else:
        raise ValueError("unknown HTB1 mode")
    if len(restored) != original_bytes:
        raise ValueError("decoded length mismatch")
    return restored


def input_bytes(args: argparse.Namespace) -> tuple[bytes, dict[str, object]]:
    if args.synthetic:
        if args.synthetic not in ("repeated-records", "xml-records"):
            raise ValueError("unknown synthetic input")
        seed = 7302026
        if args.synthetic == "xml-records":
            unit = (b'<page><title>Example %06d</title><id>%06d</id><revision><id>%06d</id>'
                    b'<timestamp>2026-09-30T00:00:00Z</timestamp><contributor><username>Editor</username>'
                    b'</contributor><comment>Text &amp; markup</comment><text xml:space="preserve">'
                    b'content &lt;example&gt; &quot;quoted&quot;</text></revision></page>\n')
            data = b"".join(unit % (index % 997, index % 997, index % 997) for index in range(1200))
            return data, {"kind": "synthetic", "generator": "xml-records-v1", "seed": seed}
        unit = (b'{"article":"CIX experimental record","id":%06d,"kind":"revision",'
                b'"comment":"small deterministic mutation"}\n')
        data = b"".join(unit % (index % 997) for index in range(2800))
        return data, {"kind": "synthetic", "generator": "repeated-records-v1", "seed": seed}
    if not args.input:
        raise ValueError("--input is required when --synthetic is absent")
    with Path(args.input).open("rb") as handle:
        handle.seek(args.offset)
        data = handle.read(args.length)
    if len(data) != args.length:
        raise ValueError("requested range is outside input")
    return data, {"kind": "file-range", "path": str(Path(args.input).resolve()), "offset": args.offset, "length": args.length}


def immutable_identity() -> dict[str, str]:
    this_file = Path(__file__).resolve()
    module = Path(zstd.__file__).resolve()
    backend = Path(zstd_backend_c.__file__).resolve()
    python = Path(sys.executable).resolve()
    return {"script_sha256": sha256(this_file.read_bytes()), "script_path": str(this_file),
            "python_binary_sha256": sha256(python.read_bytes()), "python_version": sys.version,
            "zstandard_module_sha256": sha256(module.read_bytes()), "zstandard_backend_sha256": sha256(backend.read_bytes()),
            "zstandard_backend_path": str(backend), "zstandard_version": zstd.__version__}


def encode_command(args: argparse.Namespace) -> None:
    started = time.monotonic()
    data, input_description = input_bytes(args)
    archive, costs = encode_archive(data, args.mode, args.level)
    Path(args.archive).write_bytes(archive)
    encode_seconds = time.monotonic() - started
    command = [sys.executable, "-m", "benchmarks.hutter_track_b", "decode", "--archive", str(Path(args.archive).resolve()), "--output", str(Path(args.restored).resolve())]
    decoded = subprocess.run(command, check=False, capture_output=True, text=True, timeout=args.budget_seconds)
    restored = Path(args.restored).read_bytes() if decoded.returncode == 0 and Path(args.restored).exists() else b""
    verified = decoded.returncode == 0 and sha256(restored) == sha256(data)
    receipt = {
        "schema": "cix-hutter-track-b-v1", "completed_at": datetime.now(UTC).isoformat(),
        "trial_id": args.trial_id, "track": "B", "hutter_specific": True,
        "hypothesis": args.hypothesis, "expected_mechanism": args.expected_mechanism,
        "promotion_criteria": args.promotion_criteria, "resource_budget": {"wall_seconds": args.budget_seconds, "cpu_cores": 4, "rss_bytes": 3 * 1024**3, "temporary_disk_bytes": 1024**3},
        "matched_control": "HTB1 control: same zstandard 0.25.0 level and self-contained framing, direct input",
        "mode": args.mode, "backend": "zstandard", "backend_level": args.level,
        "input": {**input_description, "bytes": len(data), "sha256": sha256(data)},
        "output": {"archive": str(Path(args.archive).resolve()), "archive_bytes": len(archive), "archive_sha256": sha256(archive),
                   "restored": str(Path(args.restored).resolve()), "restored_sha256": sha256(restored), "round_trip_verified": verified,
                   "independent_decoder_command": command, "decoder_returncode": decoded.returncode, "decoder_stderr": decoded.stderr[-1000:]},
        "accounting": costs, "encode_seconds": encode_seconds,
        "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "immutable_build": immutable_identity(), "status": "COMPLETE" if verified else "FAILED_VERIFICATION",
    }
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if not verified:
        raise SystemExit("independent decode verification failed")


def decode_command(args: argparse.Namespace) -> None:
    Path(args.output).write_bytes(decode_archive(Path(args.archive).read_bytes()))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    enc = sub.add_parser("encode")
    enc.add_argument("--mode", choices=MODES, required=True)
    enc.add_argument("--archive", required=True); enc.add_argument("--restored", required=True); enc.add_argument("--receipt", required=True)
    enc.add_argument("--trial-id", required=True); enc.add_argument("--hypothesis", required=True); enc.add_argument("--expected-mechanism", required=True); enc.add_argument("--promotion-criteria", required=True)
    enc.add_argument("--input"); enc.add_argument("--offset", type=int, default=0); enc.add_argument("--length", type=int, default=0); enc.add_argument("--synthetic", choices=["repeated-records", "xml-records"])
    enc.add_argument("--level", type=int, default=19); enc.add_argument("--budget-seconds", type=int, default=300)
    dec = sub.add_parser("decode")
    dec.add_argument("--archive", required=True); dec.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "encode": encode_command(args)
    else: decode_command(args)


if __name__ == "__main__":
    main()
