"""CIXH1 bounded heterogeneous region candidate and decoder."""
from __future__ import annotations

import hashlib
import lzma
import struct
import zlib
from dataclasses import dataclass
from .model import Candidate
from .regions import regions

MAGIC = b"CIXH1"
VERSION = 1
HEADER = struct.Struct("<5sBQI32s")
FRAME = struct.Struct("<BIIH32s")
RAW, ZLIB, LZMA = 0, 1, 2
SPECIALIST = 128
MAX_REGIONS = 65536
MAX_NESTED_SPECIALISTS = 8
MAX_CIXH_MEMORY = 5 << 30
MAX_NESTED_TOTAL_MEMORY = 10 << 30

@dataclass(frozen=True)
class RegionChoice:
    backend: int
    parameters: bytes
    payload: bytes
    source: bytes

def recognizes_magic(prefix: bytes) -> bool:
    return prefix.startswith(MAGIC)

def _generic_choices(source: bytes) -> list[RegionChoice]:
    choices = [RegionChoice(RAW, b"", source, source)]
    for backend, params, encoder in ((ZLIB, b"level=6", lambda: zlib.compress(source, 6)),
                                     (LZMA, b"preset=3", lambda: lzma.compress(source, preset=3))):
        try:
            payload = encoder()
        except (MemoryError, lzma.LZMAError, zlib.error):
            continue
        choices.append(RegionChoice(backend, params, payload, source))
    return choices

def _uses_paq(item: Candidate) -> bool:
    """Classify from declared candidate metadata, never from input content."""
    fields = (item.id, item.family, str(item.parameters.get("backend", "")),
              str(item.parameters.get("options", "")))
    return any("paq" in field.lower() for field in fields)


def _round_robin(candidates: list[Candidate]) -> list[Candidate]:
    pending: dict[str, list[Candidate]] = {}
    for item in candidates: pending.setdefault(item.family, []).append(item)
    ordered: list[Candidate] = []
    while pending:
        for family in tuple(pending):
            ordered.append(pending[family].pop(0))
            if not pending[family]: del pending[family]
    return ordered


def _omission(item: Candidate, profile: str, source_bytes: int, parent_bytes: int,
              retained_bytes: int, accepted: int) -> dict | None:
    if profile == "fast": return {"kind": "specialist", "id": item.id, "status": "omitted", "reason": "fast profile uses generic region backends"}
    if profile == "default" and _uses_paq(item): return {"kind": "specialist", "id": item.id, "status": "omitted", "reason": "default profile omits nested PAQ"}
    memory = max(item.memory_bytes, item.decode_memory_bytes)
    if memory > MAX_CIXH_MEMORY or item.threads != 1: return {"kind": "specialist", "id": item.id, "status": "omitted", "reason": "nested resource policy", "declared_memory_bytes": memory, "declared_threads": item.threads}
    if parent_bytes + source_bytes + retained_bytes + memory > MAX_NESTED_TOTAL_MEMORY: return {"kind": "specialist", "id": item.id, "status": "omitted", "reason": "nested aggregate memory policy", "parent_archive_bytes": parent_bytes, "source_bytes": source_bytes, "retained_payload_bytes": retained_bytes, "declared_memory_bytes": memory, "aggregate_limit_bytes": MAX_NESTED_TOTAL_MEMORY}
    if accepted >= MAX_NESTED_SPECIALISTS: return {"kind": "specialist", "id": item.id, "status": "omitted", "reason": "nested candidate count bound"}
    return None


def _encode_specialist(item: Candidate, source: bytes) -> tuple[RegionChoice, dict]:
    report_encoder = getattr(item, "encode_with_report", None)
    payload, details = (item.encode(source), None) if report_encoder is None else report_encoder(source)
    choice = RegionChoice(SPECIALIST, item.id.encode("utf-8"), payload, source)
    row = {"kind": "specialist", "id": item.id, "status": "considered", "payload_bytes": len(payload), "frame_bytes": FRAME.size + len(choice.parameters) + len(choice.payload)}
    if details is not None: row["model_details"] = details
    return choice, row


def _best_specialist_choice(source: bytes, profile: str,
                            incumbent_cost: int, parent_bytes: int) -> tuple[RegionChoice | None, list[dict]]:
    """Optional registry bridge. Missing/failed specialists never lose bytes."""
    try:
        from . import specialized  # supplied independently when admitted
    except ImportError:
        return None, [{"kind": "specialist", "status": "unavailable", "reason": "registry not installed"}]
    diagnostics: list[dict] = []
    try:
        candidates, registry_diagnostics = specialized.catalog(source)
    except Exception as error:
        return None, [{"kind": "specialist", "status": "unavailable",
                     "reason": f"registry-error:{type(error).__name__}"}]
    diagnostics.extend(registry_diagnostics)
    accepted = 0
    best: RegionChoice | None = None
    best_cost = incumbent_cost
    for item in _round_robin(candidates):
        retained_payload = len(best.payload) if best is not None else 0
        omitted = _omission(item, profile, len(source), parent_bytes, retained_payload, accepted)
        if omitted is not None: diagnostics.append(omitted); continue
        try:
            choice, row = _encode_specialist(item, source)
            cost = FRAME.size + len(choice.parameters) + len(choice.payload)
            diagnostics.append(row)
            if cost < best_cost:
                best, best_cost = choice, cost
            accepted += 1
        except Exception as error:  # candidate omission is observable, never fallback loss
            diagnostics.append({"kind": "specialist", "id": getattr(item, "id", "unknown"), "status": "omitted", "reason": str(error)})
    return best, diagnostics

def _choose(source: bytes, *, allow_specialists: bool, profile: str,
            parent_bytes: int) -> tuple[RegionChoice, list[dict]]:
    choices = _generic_choices(source)
    diagnostics: list[dict] = []
    chosen = min(choices, key=lambda choice: (FRAME.size + len(choice.parameters) + len(choice.payload), choice.backend))
    if allow_specialists:
        specialist, diagnostics = _best_specialist_choice(
            source, profile, FRAME.size + len(chosen.parameters) + len(chosen.payload), parent_bytes)
        if specialist is not None:
            specialist_cost = FRAME.size + len(specialist.parameters) + len(specialist.payload)
            chosen_cost = FRAME.size + len(chosen.parameters) + len(chosen.payload)
            if specialist_cost < chosen_cost:
                chosen = specialist
    else:
        diagnostics.append({"kind": "specialist", "status": "not-applicable",
                            "reason": "unknown generic region"})
    # Frame cost is part of competition. Stable tuple ordering retains raw on ties.
    diagnostics.append({"kind": "region", "status": "selected", "backend": chosen.backend,
                        "source_bytes": len(source), "payload_bytes": len(chosen.payload), "parameters_bytes": len(chosen.parameters)})
    return chosen, diagnostics

def encode_with_report(data: bytes, profile: str = "best") -> tuple[bytes, list[dict]]:
    """Make one complete CIXH1 archive and preserve paid-choice evidence."""
    if profile not in {"fast", "default", "best"}:
        raise ValueError("unsupported heterogeneous profile")
    partitions = regions(data)
    if len(partitions) > MAX_REGIONS:
        raise ValueError("too many heterogeneous regions")
    output = bytearray(HEADER.pack(MAGIC, VERSION, len(data), len(partitions), hashlib.sha256(data).digest()))
    diagnostics: list[dict] = []
    for number, region in enumerate(partitions):
        choice, selection = _choose(data[region.start:region.end],
                                    allow_specialists=region.kind != "generic", profile=profile,
                                    parent_bytes=len(output))
        if len(choice.parameters) > 65535 or len(choice.payload) > 0xFFFFFFFF:
            raise ValueError("heterogeneous region frame limit")
        output.extend(FRAME.pack(choice.backend, len(choice.source), len(choice.payload), len(choice.parameters), hashlib.sha256(choice.source).digest()))
        output.extend(choice.parameters)
        output.extend(choice.payload)
        diagnostics.extend({**entry, "region": number, "region_kind": region.kind} for entry in selection)
    return bytes(output), diagnostics


def _encode(data: bytes, profile: str = "best") -> bytes:
    return encode_with_report(data, profile)[0]

def catalog(data: bytes, profile: str = "best") -> tuple[list[Candidate], list[dict]]:
    if profile not in {"fast", "default", "best"}:
        raise ValueError("unsupported heterogeneous profile")
    diagnostics: list[dict] = []
    # Cataloguing does no backend work and does not invoke specialist parsers.
    # Full qualification and its evidence are kept with the one candidate
    # worker in encode_with_report.
    for region in regions(data):
        diagnostics.append({"kind": "region", "status": "admitted",
                            "region_kind": region.kind,
                            "source_bytes": region.end - region.start})
    candidate = Candidate(id="heterogeneous-cixh1-v1", family="heterogeneous",
                          encode=lambda blob: _encode(blob, profile),
                          # The candidate may select any admitted nested legacy
                          # frame, so its declared peak must cover that policy,
                          # rather than only the input size seen at catalog time.
                          memory_bytes=MAX_CIXH_MEMORY,
                          decode_memory_bytes=MAX_CIXH_MEMORY,
                          timeout_seconds=43200, threads=1,
                          encode_with_report=lambda blob: encode_with_report(blob, profile),
                          parameters={"magic": MAGIC.decode(), "boundary": "input-derived-boundaries+64KiB",
                                      "generic_backends": ["raw", "zlib", "lzma"],
                                      "nested_policy": {"max_candidates": MAX_NESTED_SPECIALISTS,
                                                        "max_memory_bytes": MAX_CIXH_MEMORY,
                                                        "max_aggregate_memory_bytes": MAX_NESTED_TOTAL_MEMORY,
                                                        "threads": 1,
                                                        "selection": "family-round-robin"},
                                      "total_time_bound_seconds": 43200,
                                      "profile": profile})
    return [candidate], diagnostics

def _decode_zlib(payload: bytes, parameters: bytes, source_len: int) -> bytes:
    if parameters != b"level=6": raise ValueError("unsupported zlib parameters")
    decoder = zlib.decompressobj(); source = decoder.decompress(payload, source_len + 1)
    if decoder.unconsumed_tail or decoder.unused_data or not decoder.eof: raise ValueError("invalid or oversized zlib region")
    return source


def _decode_lzma(payload: bytes, parameters: bytes, source_len: int, memory_bytes: int) -> bytes:
    if parameters != b"preset=3": raise ValueError("unsupported lzma parameters")
    decoder = lzma.LZMADecompressor(memlimit=memory_bytes); source = decoder.decompress(payload, max_length=source_len + 1)
    if decoder.unused_data or not decoder.eof: raise ValueError("invalid or oversized lzma region")
    return source


def _decode_specialist(payload: bytes, source_len: int, memory_bytes: int) -> bytes:
    try: from . import specialized
    except ImportError as error: raise ValueError("specialist decoder unavailable") from error
    return specialized.decode(payload, max_output_bytes=source_len, memory_bytes=memory_bytes)


def _decode_payload(backend: int, payload: bytes, parameters: bytes, source_len: int,
                    memory_bytes: int) -> bytes:
    if backend == RAW:
        if parameters: raise ValueError("raw region has parameters")
        return payload
    if backend == ZLIB: return _decode_zlib(payload, parameters, source_len)
    if backend == LZMA: return _decode_lzma(payload, parameters, source_len, memory_bytes)
    if backend == SPECIALIST:
        return _decode_specialist(payload, source_len, memory_bytes)
    raise ValueError("unknown heterogeneous region backend")

def _header(frame: bytes, max_output_bytes: int, memory_bytes: int) -> tuple[int, int, bytes]:
    if max_output_bytes < 0 or memory_bytes < 0 or len(frame) < HEADER.size:
        raise ValueError("truncated CIXH1 header")
    magic, version, expected, count, digest = HEADER.unpack_from(frame)
    if magic != MAGIC or version != VERSION or count > MAX_REGIONS or expected > max_output_bytes or expected > memory_bytes:
        raise ValueError("invalid CIXH1 header or resource limit")
    return expected, count, digest


def _decode_region(frame: bytes, position: int, output: bytearray,
                   max_output_bytes: int, memory_bytes: int) -> tuple[int, bytes]:
    if position + FRAME.size > len(frame): raise ValueError("truncated CIXH1 frame")
    backend, source_len, payload_len, parameter_len, source_digest = FRAME.unpack_from(frame, position)
    position += FRAME.size
    end = position + parameter_len + payload_len
    if end > len(frame) or source_len > max_output_bytes - len(output): raise ValueError("invalid CIXH1 frame length")
    available_memory = memory_bytes - len(output)
    if source_len > available_memory: raise ValueError("CIXH1 region exceeds remaining decode memory")
    if backend == RAW and payload_len != source_len: raise ValueError("invalid raw CIXH1 frame length")
    try:
        source = _decode_payload(backend, frame[position + parameter_len:end],
                                 frame[position:position + parameter_len], source_len, available_memory)
    except (lzma.LZMAError, zlib.error, EOFError) as error:
        raise ValueError("invalid compressed CIXH1 region") from error
    if len(source) != source_len or hashlib.sha256(source).digest() != source_digest:
        raise ValueError("CIXH1 region checksum mismatch")
    return end, source


def decode(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    expected, count, digest = _header(frame, max_output_bytes, memory_bytes)
    position, output = HEADER.size, bytearray()
    for _ in range(count):
        position, source = _decode_region(frame, position, output, max_output_bytes, memory_bytes)
        output.extend(source)
    if position != len(frame) or len(output) != expected or hashlib.sha256(output).digest() != digest: raise ValueError("CIXH1 archive mismatch")
    return bytes(output)
