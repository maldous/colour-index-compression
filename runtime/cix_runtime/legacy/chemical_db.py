"""Retained chemical and MyISAM archive specialists.

These are exact historical transforms and frame layouts, isolated from research
runners.  They are offered only after a complete causal parse of the input.
"""
from __future__ import annotations

import zlib
from typing import Callable

from .. import backends
from ..model import Candidate
from . import mysql_fixed_columns as fixed_columns
from . import mysql_record_constraints as records
from . import sdf_geometry as geometry
from . import sdf_hydrogen as hydrogen
from .multinomial import vdecode, vencode

_GEOMETRY_MAGIC = b"CIXG\x01"
_HYDROGEN_MAGIC = b"CIXQ\x01"
_PAQ_VERSION = "v215"
_PAQ_OPTIONS = "-8"
_PAQ_BASE_MEMORY = 4_500_000_000
_BROTLI_MEMORY = 256 * 1024 * 1024


def _paq_memory(data_size: int) -> int:
    """Conservative PAQ -8 working-set declaration: base plus source copies."""
    if data_size < 0:
        raise ValueError("negative source size")
    return _PAQ_BASE_MEMORY + 8 * data_size


def _require_paq_memory(data_size: int, memory_bytes: int) -> None:
    if memory_bytes < _paq_memory(data_size):
        raise ValueError("PAQ -8 decode memory admission limit")


def _legacy_raw_paq(transformed: bytes) -> bytes:
    """Return the historic raw paq8px member from the runtime CIXP adapter."""
    wrapped = backends.encode_paq(transformed, _PAQ_VERSION, _PAQ_OPTIONS)
    prefix = len(backends.CIXP)
    if (len(wrapped) < prefix + 1 or wrapped[:prefix] != backends.CIXP
            or wrapped[prefix] != backends.PAQ_IDS[_PAQ_VERSION]):
        raise ValueError("runtime PAQ adapter returned an incompatible frame")
    return backends.PAQ_MAGIC + wrapped[prefix + 1:]


def _decode_legacy_raw_paq(payload: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    if not payload.startswith(backends.PAQ_MAGIC):
        raise ValueError("invalid historic PAQ payload")
    wrapped = (backends.CIXP + bytes([backends.PAQ_IDS[_PAQ_VERSION]])
               + payload[len(backends.PAQ_MAGIC):])
    return backends.decode_paq(wrapped, max_output_bytes, memory_bytes)


def _pack_legacy(magic: bytes, data: bytes, transformed: bytes) -> bytes:
    return magic + vencode(len(data)) + zlib.crc32(data).to_bytes(4, "big") + _legacy_raw_paq(transformed)


def _decode_legacy(magic: bytes, inverse: Callable[[bytes], bytes], frame: bytes,
                   max_output_bytes: int, memory_bytes: int) -> bytes:
    if max_output_bytes < 0 or memory_bytes <= 0 or not frame.startswith(magic):
        raise ValueError("invalid legacy specialist frame")
    size, position = vdecode(frame, len(magic))
    if size > max_output_bytes or size > memory_bytes:
        raise ValueError("legacy specialist output exceeds admission limit")
    _require_paq_memory(size, memory_bytes)
    if position + 4 >= len(frame):
        raise ValueError("truncated legacy specialist frame")
    crc = int.from_bytes(frame[position:position + 4], "big")
    transformed = _decode_legacy_raw_paq(frame[position + 4:], memory_bytes, memory_bytes)
    restored = inverse(transformed)
    if len(restored) != size or zlib.crc32(restored) != crc:
        raise ValueError("legacy specialist checksum mismatch")
    return restored


def encode_geometry(data: bytes, representation: int = 2) -> bytes:
    transformed, _ = geometry.encode(data, 2, representation)
    return _pack_legacy(_GEOMETRY_MAGIC, data, transformed)


def decode_geometry(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    return _decode_legacy(_GEOMETRY_MAGIC, geometry.decode, frame, max_output_bytes, memory_bytes)


def encode_hydrogen(data: bytes) -> bytes:
    transformed, _ = hydrogen.encode(data, 2, 0)
    return _pack_legacy(_HYDROGEN_MAGIC, data, transformed)


def decode_hydrogen(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    return _decode_legacy(_HYDROGEN_MAGIC, hydrogen.decode, frame, max_output_bytes, memory_bytes)


def _recognizes_geometry(data: bytes) -> bool:
    """Cheap SDF preflight; encode performs the complete exact member parse.

    The retained geometry and hydrogen transforms preserve every unsupported
    member as raw bytes, so a marker is sufficient for candidate admission.
    """
    return b"V2000" in data and b"M  END" in data


def _recognizes_records(data: bytes) -> bool:
    """Cheap MyISAM preflight; transform validates each record when trialled."""
    return len(data) >= 3 and data[0] in (1, 3) and int.from_bytes(data[1:3], "big") > 0


def recognizes_chemical(data: bytes) -> bool:
    return _recognizes_geometry(data)


def recognizes_database(data: bytes) -> bool:
    return _recognizes_records(data)


def recognizes_frame(frame: bytes) -> bool:
    return any(frame.startswith(magic) for magic in DECODERS)


def _candidate(identifier: str, family: str, encode: Callable[[bytes], bytes], memory: int,
               **parameters: object) -> Candidate:
    return Candidate(identifier, family, encode, memory, memory, parameters=parameters)


def catalog(data: bytes) -> tuple[list[Candidate], list[dict]]:
    """Return parsed, exact legacy candidates and the evidence for each admission."""
    candidates: list[Candidate] = []
    evidence: list[dict] = []
    if _recognizes_geometry(data):
        candidates.extend((
            _candidate("bonded-coordinate-palette-paq-v215-8", "chemical-geometry",
                       lambda blob: encode_geometry(blob, 2), _paq_memory(len(data)),
                       magic="CIXG01", mode=2, representation=2, backend="paq-v215", options="-8"),
            _candidate("bonded-coordinate-text-paq-v215-8", "chemical-geometry",
                       lambda blob: encode_geometry(blob, 1), _paq_memory(len(data)),
                       magic="CIXG01", mode=2, representation=1, backend="paq-v215", options="-8"),
            _candidate("chemical-hydrogen-paq-v215-8", "chemical-hydrogen",
                       encode_hydrogen, _paq_memory(len(data)),
                       magic="CIXQ01", mode=2, representation=0, backend="paq-v215", options="-8"),
        ))
        evidence.append({"family": "chemical", "recognizer": "sdf-v2000-marker; exact transform preserves unsupported members raw", "admitted": len(candidates)})
    if _recognizes_records(data):
        for mode in range(5):
            candidates.append(_candidate(
                f"database-constraints-{mode}", "database-constraints",
                lambda blob, selected=mode: records.encode(blob, selected, 0)[0], _BROTLI_MEMORY,
                magic="CIXD01", mode=mode, backend="brotli-11"))
        candidates.extend((
            _candidate("database-remaining-count-paq-v215-8", "database-remaining-count",
                       lambda blob: records.encode(blob, 3, 1, _PAQ_OPTIONS)[0], _paq_memory(len(data)),
                       magic="CIXD01", mode=3, backend="paq-v215", options="-8"),
            _candidate("database-implied-width", "database-fixed-columns",
                       lambda blob: fixed_columns.encode(blob, 1)[0], _BROTLI_MEMORY,
                       magic="CIXD02", mode=1, backend="brotli-11"),
        ))
        evidence.append({"family": "database", "recognizer": "myisam-header-marker; exact transform validates records during trial", "admitted": 7})
    return candidates, evidence


DECODERS: dict[bytes, Callable[[bytes, int, int], bytes]] = {
    _GEOMETRY_MAGIC: decode_geometry,
    _HYDROGEN_MAGIC: decode_hydrogen,
    records.MAGIC: records.decode,
    fixed_columns.MAGIC: fixed_columns.decode,
}
