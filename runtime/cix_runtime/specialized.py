"""Automatic catalogue and exact decode dispatch for specialised CIX frames.

Every admission comes from the supplied bytes.  No paths, corpus names, cached
outputs, hashes, or benchmark records participate in runtime selection.
"""
from __future__ import annotations

import struct
from typing import Callable

from .legacy import executable
from .model import Candidate


def _elf(data: bytes) -> tuple[bool, str]:
    """Validate the ELF identity and declared program/section-table extents."""
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] not in (1, 2) or data[5] not in (1, 2) or data[6] != 1:
        return False, "ident"
    endian = "little" if data[5] == 1 else "big"
    try:
        if data[4] == 1:
            ehsize = int.from_bytes(data[40:42], endian); phoff = int.from_bytes(data[28:32], endian); shoff = int.from_bytes(data[32:36], endian)
            phentsize = int.from_bytes(data[42:44], endian); phnum = int.from_bytes(data[44:46], endian)
            shentsize = int.from_bytes(data[46:48], endian); shnum = int.from_bytes(data[48:50], endian)
        else:
            ehsize = int.from_bytes(data[52:54], endian); phoff = int.from_bytes(data[32:40], endian); shoff = int.from_bytes(data[40:48], endian)
            phentsize = int.from_bytes(data[54:56], endian); phnum = int.from_bytes(data[56:58], endian)
            shentsize = int.from_bytes(data[58:60], endian); shnum = int.from_bytes(data[60:62], endian)
    except IndexError:
        return False, "truncated-header"
    if ehsize > len(data) or (phnum and (not phentsize or phoff + phentsize * phnum > len(data))) or (shnum and (not shentsize or shoff + shentsize * shnum > len(data))):
        return False, "table-extent"
    return True, "elf-header-and-tables"


def _candidate(identifier: str, family: str, encoder: Callable[[bytes], bytes], *, memory: int, magic: bytes, parameters: dict) -> Candidate:
    if magic not in _decoder_maps():
        raise RuntimeError(f"candidate {identifier} has no registered decoder")
    return Candidate(identifier, family, encoder, memory, memory, parameters={**parameters, "magic": magic.hex()})


def _external_catalog(module_name: str, data: bytes) -> tuple[list[Candidate], list[dict]]:
    try:
        module = __import__(f"{__package__}.legacy.{module_name}", fromlist=["catalog"])
        return module.catalog(data)
    except ModuleNotFoundError as error:
        if error.name == f"{__package__}.legacy.{module_name}":
            return [], [{"family": module_name, "eligible": False, "reason": "runtime-closure-unavailable"}]
        raise


def _eligible(name: str, callback: Callable[[], bool]) -> tuple[bool, dict]:
    try:
        eligible = bool(callback())
        return eligible, {"family": name, "eligible": eligible, "reason": "transform-eligible" if eligible else "no-transformable-layout"}
    except (ValueError, struct.error, IndexError, OverflowError) as error:
        return False, {"family": name, "eligible": False, "reason": f"layout-rejected:{type(error).__name__}"}


def catalog(data: bytes) -> tuple[list[Candidate], list[dict]]:
    candidates: list[Candidate] = []
    diagnostics: list[dict] = []
    # These are the native transform predicates.  In particular, objects()
    # scans accepted embedded carriers; no outer-file magic is used to erase
    # opportunities contained at a nonzero byte position.
    got, row = _eligible("executable-got", lambda: bool(executable.ecoff_got.objects(data)))
    diagnostics.append(row)
    pointer, row = _eligible("executable-pointer", lambda: bool(executable.ecoff_pointer_deltas.locator.candidates(data)))
    diagnostics.append(row)
    section, row = _eligible("executable-section", lambda: bool(executable.ecoff_section_pointers.fields(data, 4)))
    diagnostics.append(row)
    filtered, row = _eligible("executable-filter", lambda: bool(executable.ecoff_pdata_symbols.procedure.base.objects(data)))
    diagnostics.append(row)
    elf, elf_reason = _elf(data)
    diagnostics.append({"family": "executable-elf", "eligible": elf, "reason": elf_reason})
    for module_name in ("chemical_db", "image_grid"):
        extra, rows = _external_catalog(module_name, data)
        candidates.extend(extra)
        diagnostics.extend(rows)

    paq_memory = 4_500_000_000 + 8 * len(data)
    filter_memory = 1_000_000_000 + 8 * len(data)
    if got:
        candidates.extend((
            _candidate("ecoff-got-mode3-paq", "executable-got", executable.encode_got, memory=paq_memory, magic=executable.GOT_MAGIC, parameters={"transform": "ecoff-got", "mode": 3, "backend": "paq-v215", "options": "-8"}),
            _candidate("ecoff-got-mode3-brotli", "executable-got", lambda blob: executable.encode_got(blob, "brotli"), memory=filter_memory, magic=executable.GOT_MAGIC, parameters={"transform": "ecoff-got", "mode": 3, "backend": "brotli-11"}),
        ))
    if pointer:
        candidates.extend((
            _candidate("ecoff-pointer-mode5-paq", "executable-pointer", executable.encode_pointer, memory=paq_memory, magic=executable.POINTER_MAGIC, parameters={"transform": "ecoff-pointer-deltas", "mode": 5, "backend": "paq-v215", "options": "-8"}),
            _candidate("ecoff-pointer-mode5-brotli", "executable-pointer", lambda blob: executable.encode_pointer(blob, "brotli"), memory=filter_memory, magic=executable.POINTER_MAGIC, parameters={"transform": "ecoff-pointer-deltas", "mode": 5, "backend": "brotli-11"}),
        ))
    if section:
        candidates.extend((
            _candidate("ecoff-section-mode4-paq", "executable-section", executable.encode_section, memory=paq_memory, magic=executable.SECTION_MAGIC, parameters={"transform": "ecoff-section-pointers", "mode": 4, "backend": "paq-v215", "options": "-8"}),
            _candidate("ecoff-section-mode4-brotli", "executable-section", lambda blob: executable.encode_section(blob, "brotli"), memory=filter_memory, magic=executable.SECTION_MAGIC, parameters={"transform": "ecoff-section-pointers", "mode": 4, "backend": "brotli-11"}),
        ))
    if filtered:
        candidates.append(
            _candidate(
                "ecoff-filter-mode0",
                "executable-filter",
                lambda blob: executable.encode_filtered(blob, 0),
                memory=filter_memory,
                magic=executable.FILTER_MAGIC,
                parameters={"transform": "ecoff-pdata-symbols", "mode": 0, "backend": "brotli-11"},
            )
        )
        for mode in (1, 2):
            candidates.append(
                _candidate(
                    f"ecoff-filter-mode{mode}",
                    "executable-filter",
                    lambda blob, selected=mode: executable.encode_filtered(blob, selected),
                    memory=paq_memory,
                    magic=executable.FILTER_MAGIC,
                    parameters={
                        "transform": "ecoff-pdata-symbols" if mode == 1 else "identity",
                        "mode": mode,
                        "backend": "paq-v216-0+brotli",
                        "decoder_backend": "paq-store-state+brotli",
                    },
                )
            )
    if elf or section:
        candidates.append(_candidate("executable-joint-discount", "executable-joint-discount", executable.encode_joint_discount, memory=paq_memory, magic=executable.JOINT_MAGIC, parameters={"transform": "ecoff-section-pointers", "backend": "paq-joint-discount", "mode": 2, "options": "-8"}))
    return candidates, diagnostics

def _decoder_maps() -> dict[bytes, Callable[[bytes, int, int], bytes]]:
    mapping: dict[bytes, Callable[[bytes, int, int], bytes]] = {
        executable.JOINT_MAGIC: executable.decode_joint_discount,
        executable.FILTER_MAGIC: executable.decode_filtered,
        executable.GOT_MAGIC: executable.decode_got,
        executable.POINTER_MAGIC: executable.decode_pointer,
        executable.SECTION_MAGIC: executable.decode_section,
    }
    for module_name in ("chemical_db", "image_grid"):
        try:
            module = __import__(f"{__package__}.legacy.{module_name}", fromlist=["DECODERS"])
        except ModuleNotFoundError as error:
            if error.name == f"{__package__}.legacy.{module_name}":
                continue
            raise
        for magic, decoder in module.DECODERS.items():
            if magic in mapping and mapping[magic] is not decoder:
                raise RuntimeError(f"duplicate specialised decoder magic: {magic!r}")
            mapping[magic] = decoder
    return mapping


def decode(frame: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    for magic, decoder in _decoder_maps().items():
        if frame.startswith(magic):
            return decoder(frame, max_output_bytes, memory_bytes)
    raise ValueError("unsupported specialised frame magic")


def recognizes_magic(prefix: bytes) -> bool:
    return any(prefix.startswith(magic) for magic in _decoder_maps())
