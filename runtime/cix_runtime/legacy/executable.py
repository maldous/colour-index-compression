"""Extracted executable transforms and their complete historic frames.

No source path, corpus name, cached stream, or benchmark wrapper is consulted.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

import brotli

from ..backends import PAQ_DECODE_MINIMUM_MEMORY, _resource_policy, decode_paq, encode_paq, paq_binary
from . import ecoff_got, ecoff_pdata_symbols, ecoff_pointer_deltas, ecoff_section_pointers
from .framing import checked_frame, parse_checked_frame, verify

JOINT_MAGIC = b"CIXB\x1d"
FILTER_MAGIC = b"CIXB\x13"
LEGACY_OUTPUT_EXCEEDS_MEMORY = "legacy output exceeds memory limit"
GOT_MAGIC = b"CIXB\x03"
POINTER_MAGIC = b"CIXB\x0b"
SECTION_MAGIC = b"CIXB\x0c"


def _environment(mode: int) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("CIX_")}
    if mode < 4:
        env["CIX_JOINT_DISCOUNT"] = str(mode)
    return env


def _validate_paq_decode(decode: bool, max_output_bytes: int | None, memory_bytes: int | None) -> None:
    if not decode:
        return
    if max_output_bytes is None or memory_bytes is None:
        raise ValueError("legacy PAQ decode requires output and memory bounds")
    if max_output_bytes < 0 or memory_bytes < PAQ_DECODE_MINIMUM_MEMORY:
        raise ValueError("legacy PAQ decode memory limit is below the conservative 4.5 GB admission")


def _paq_command(source: Path, output: Path, version: str, options: str, decode: bool) -> list[str]:
    command = [paq_binary(version)]
    command.append("-d" if decode else options)
    return command + ["-simd", "AVX2", str(source), str(output)]


def _run_paq(source: bytes, version: str, options: str, *, decode: bool = False, env: dict[str, str] | None = None, timeout_seconds: int = 43_200, max_output_bytes: int | None = None, memory_bytes: int | None = None) -> bytes:
    """Run one installed PAQ fork over a temporary byte stream.

    A decoder must be admitted before launch: PAQ has no independently verified
    allocation field in these historic streams, so every fork uses the same
    conservative address-space floor as the CIXP adapter.
    """
    _validate_paq_decode(decode, max_output_bytes, memory_bytes)
    with tempfile.TemporaryDirectory(prefix="cix-legacy-exec-") as folder:
        root = Path(folder)
        suffix = "216" if version in {"v216", "store-state"} else "215"
        incoming = root / (f"stream.paq8px{suffix}" if decode else "source.bin")
        outgoing = root / ("decoded.bin" if decode else f"stream.paq8px{suffix}")
        incoming.write_bytes(source)
        command = _paq_command(incoming, outgoing, version, options, decode)
        proc_env = os.environ.copy()
        if env:
            proc_env.update(env)
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=proc_env,
                timeout=timeout_seconds,
                preexec_fn=(
                    _resource_policy(memory_bytes, max_output_bytes)
                    if decode else None
                ),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("legacy PAQ backend timed out; outer candidate process group remains responsible for descendants") from error
        if completed.returncode:
            detail = completed.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"legacy PAQ backend failed ({completed.returncode}): {detail or 'no diagnostic'}")
        if not outgoing.is_file():
            raise RuntimeError("legacy PAQ backend produced no output")
        if max_output_bytes is not None and outgoing.stat().st_size > max_output_bytes:
            raise ValueError("legacy PAQ output exceeds intermediate limit")
        return outgoing.read_bytes()



def _encode_transform(magic: bytes, data: bytes, transform, mode: int, backend: str = "paq") -> bytes:
    raw, _ = transform.transform(data, mode)
    if backend not in {"paq", "brotli"}:
        raise ValueError("invalid executable transform backend")
    payload = encode_paq(raw, "v215", "-8") if backend == "paq" else brotli.compress(raw, quality=11, lgwin=24)
    # CIXB 0b/0c historical layout: magic, backend selector, length, CRC, payload.
    return magic + bytes([backend == "paq"]) + checked_frame(b"", 0, data)[1:] + payload


def _decode_paq_transform(magic: bytes, frame: bytes, inverse, max_output_bytes: int, memory_bytes: int) -> bytes:
    if memory_bytes <= 0 or not frame.startswith(magic) or len(frame) < len(magic) + 7 or frame[len(magic)] not in (0, 1):
        raise ValueError("invalid transformed executable frame")
    from .framing import vdecode
    size, position = vdecode(frame, len(magic) + 1)
    if size > max_output_bytes or position + 4 > len(frame):
        raise ValueError("transformed executable output exceeds limit")
    checksum = int.from_bytes(frame[position:position + 4], "big")
    payload = frame[position + 4:]
    raw = decode_paq(payload, memory_bytes, memory_bytes) if frame[len(magic)] else _brotli_decompress_limited(payload, memory_bytes)
    data = inverse(raw)
    if len(data) > memory_bytes:
        raise ValueError(LEGACY_OUTPUT_EXCEEDS_MEMORY)
    return verify(data, size, checksum)


def encode_got(data: bytes, backend: str = "paq") -> bytes:
    # CIXB03 historical layout carries mode+2 followed by backend selector.
    mode = 3
    if backend not in {"paq", "brotli"}:
        raise ValueError("invalid GOT backend")
    raw, _ = ecoff_got.transform(data, mode, True)
    payload = encode_paq(raw, "v215", "-8") if backend == "paq" else brotli.compress(raw, quality=11, lgwin=24)
    return GOT_MAGIC + bytes([mode + 2, backend == "paq"]) + checked_frame(b"", 0, data)[1:] + payload


def decode_got(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    if memory_bytes <= 0 or not frame.startswith(GOT_MAGIC) or len(frame) < 8 or frame[5] > 6 or frame[6] not in (0, 1):
        raise ValueError("invalid CIXB03 GOT frame")
    from .framing import vdecode
    size, position = vdecode(frame, 7)
    if size > max_output_bytes or position + 4 > len(frame):
        raise ValueError("GOT output exceeds limit")
    checksum = int.from_bytes(frame[position:position + 4], "big")
    payload = frame[position + 4:]
    raw = decode_paq(payload, memory_bytes, memory_bytes) if frame[6] else _brotli_decompress_limited(payload, memory_bytes)
    mode = frame[5] - 2
    if mode == -2:
        data = ecoff_got.parent.inverse(raw)
    elif mode == -1:
        data = raw
    else:
        data = ecoff_got.inverse(raw)
    if len(data) > memory_bytes:
        raise ValueError(LEGACY_OUTPUT_EXCEEDS_MEMORY)
    return verify(data, size, checksum)


def encode_pointer(data: bytes, backend: str = "paq") -> bytes:
    return _encode_transform(POINTER_MAGIC, data, ecoff_pointer_deltas, 5, backend)


def decode_pointer(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    return _decode_paq_transform(POINTER_MAGIC, frame, ecoff_pointer_deltas.inverse, max_output_bytes, memory_bytes)


def encode_section(data: bytes, backend: str = "paq") -> bytes:
    return _encode_transform(SECTION_MAGIC, data, ecoff_section_pointers, 4, backend)


def decode_section(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    return _decode_paq_transform(SECTION_MAGIC, frame, ecoff_section_pointers.inverse, max_output_bytes, memory_bytes)

def encode_joint_discount(data: bytes, mode: int = 2, options: str = "-8", *, timeout_seconds: int = 43_200) -> bytes:
    if mode not in range(5):
        raise ValueError("invalid joint feedback mode")
    raw, _ = ecoff_section_pointers.transform(data, 4)
    version = "v215" if mode == 4 else "joint-discount"
    payload = _run_paq(raw, version, options, env=_environment(mode), timeout_seconds=timeout_seconds)
    return checked_frame(JOINT_MAGIC, mode, data) + payload


def decode_joint_discount(frame: bytes, max_output_bytes: int, memory_bytes: int, *, timeout_seconds: int = 43_200) -> bytes:
    if memory_bytes <= 0:
        raise ValueError("invalid decode memory limit")
    mode, size, checksum = parse_checked_frame(frame, JOINT_MAGIC, range(5), max_output_bytes)
    version = "v215" if mode == 4 else "joint-discount"
    raw = _run_paq(frame[_payload_start(frame, JOINT_MAGIC):], version, "", decode=True, env=_environment(mode), timeout_seconds=timeout_seconds, max_output_bytes=memory_bytes, memory_bytes=memory_bytes)
    data = ecoff_section_pointers.inverse(raw)
    if len(data) > memory_bytes:
        raise ValueError(LEGACY_OUTPUT_EXCEEDS_MEMORY)
    return verify(data, size, checksum)


def encode_filtered(data: bytes, mode: int = 1, *, timeout_seconds: int = 43_200) -> bytes:
    if mode not in range(3):
        raise ValueError("invalid filter combination")
    raw, _ = ecoff_pdata_symbols.transform(data, 1) if mode != 2 else (data, {})
    if mode:
        raw = _run_paq(raw, "v216", "-0", timeout_seconds=timeout_seconds)
    return checked_frame(FILTER_MAGIC, mode, data) + brotli.compress(raw, quality=11, lgwin=24)


def decode_filtered(frame: bytes, max_output_bytes: int, memory_bytes: int, *, timeout_seconds: int = 43_200) -> bytes:
    if memory_bytes <= 0:
        raise ValueError("invalid decode memory limit")
    mode, size, checksum = parse_checked_frame(frame, FILTER_MAGIC, range(3), max_output_bytes)
    raw = _brotli_decompress_limited(frame[_payload_start(frame, FILTER_MAGIC):], memory_bytes)
    if mode:
        raw = _run_paq(raw, "store-state", "", decode=True, timeout_seconds=timeout_seconds, max_output_bytes=memory_bytes, memory_bytes=memory_bytes)
    data = ecoff_pdata_symbols.inverse(raw) if mode != 2 else raw
    if len(data) > memory_bytes:
        raise ValueError(LEGACY_OUTPUT_EXCEEDS_MEMORY)
    return verify(data, size, checksum)


def _brotli_decompress_limited(payload: bytes, limit: int) -> bytes:
    """Decode incrementally so a corrupt nested stream cannot allocate freely."""
    decoder = brotli.Decompressor()
    output = bytearray()
    for start in range(0, len(payload), 64 * 1024):
        output.extend(decoder.process(payload[start:start + 64 * 1024]))
        if len(output) > limit:
            raise ValueError("Brotli intermediate exceeds memory limit")
    if not decoder.is_finished():
        raise ValueError("truncated Brotli payload")
    return bytes(output)


def _payload_start(frame: bytes, magic: bytes) -> int:
    # Reparse to find the byte immediately after the fixed checksum.
    from .framing import vdecode
    _, pos = vdecode(frame, len(magic) + 1)
    return pos + 4


def recognizes_magic(prefix: bytes) -> bool:
    return prefix.startswith((JOINT_MAGIC, FILTER_MAGIC, GOT_MAGIC, POINTER_MAGIC, SECTION_MAGIC))


def decode(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    if frame.startswith(JOINT_MAGIC):
        return decode_joint_discount(frame, max_output_bytes, memory_bytes)
    if frame.startswith(FILTER_MAGIC):
        return decode_filtered(frame, max_output_bytes, memory_bytes)
    if frame.startswith(GOT_MAGIC):
        return decode_got(frame, max_output_bytes, memory_bytes)
    if frame.startswith(POINTER_MAGIC):
        return decode_pointer(frame, max_output_bytes, memory_bytes)
    if frame.startswith(SECTION_MAGIC):
        return decode_section(frame, max_output_bytes, memory_bytes)
    raise ValueError("unsupported executable legacy magic")
