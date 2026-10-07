#!/usr/bin/env python3
"""Private frozen-release ABI check for `cix_squash_splice`.

This is a C ABI test, not a SquashFS test and not a QuixDB Squash plugin-load
test.  It directly exercises the exported shared-library entry point with real
short-read and short-write callbacks.  A separate SDK-equipped host is needed
to qualify dynamic plugin discovery/loading.

Run only after selecting the frozen shared library.  The required work
directory must not exist, preventing an evidence run from being overwritten.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


STATUS_OK = 1
STATUS_EOF = 3
CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_int32,
    ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_void_p,
)


@dataclass
class Reader:
    source: bytes
    limit: int = 29
    offset: int = 0
    calls: int = 0
    max_requested: int = 0

    def callback(self, size, buffer, _user) -> int:
        self.calls += 1
        requested = size[0]
        self.max_requested = max(self.max_requested, requested)
        count = min(requested, self.limit, len(self.source) - self.offset)
        if count == 0:
            size[0] = 0
            return STATUS_EOF
        ctypes.memmove(buffer, self.source[self.offset : self.offset + count], count)
        self.offset += count
        size[0] = count
        return STATUS_OK


@dataclass
class Writer:
    limit: int = 31
    output: bytearray = field(default_factory=bytearray)
    calls: int = 0
    max_requested: int = 0

    def callback(self, size, buffer, _user) -> int:
        self.calls += 1
        requested = size[0]
        self.max_requested = max(self.max_requested, requested)
        count = min(requested, self.limit)
        if requested and count == 0:
            return -1
        self.output.extend(ctypes.string_at(buffer, count))
        size[0] = count
        return STATUS_OK


def bind(path: Path):
    library = ctypes.CDLL(str(path))
    function = library.cix_squash_splice
    function.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    function.restype = ctypes.c_int32
    return function


def invoke(function, direction: int, level: int, source: bytes | None, *, read_limit=29, write_limit=31, null_read=False, null_write=False):
    reader = Reader(source or b"", read_limit)
    writer = Writer(write_limit)
    read_callback = CALLBACK(reader.callback)
    write_callback = CALLBACK(writer.callback)
    read_pointer = None if null_read else ctypes.cast(read_callback, ctypes.c_void_p)
    write_pointer = None if null_write else ctypes.cast(write_callback, ctypes.c_void_p)
    result = function(direction, level, read_pointer, write_pointer, None)
    return result, reader, writer


def assert_rejected(function, label: str, direction: int, level: int, source: bytes | None, **kwargs) -> dict[str, int | bool]:
    result, reader, writer = invoke(function, direction, level, source, **kwargs)
    if result == STATUS_OK:
        raise RuntimeError(f"ABI accepted invalid case: {label}")
    return {"rejected": True, "status": result, "read_calls": reader.calls, "write_calls": writer.calls}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path, help="frozen libcix_native shared library")
    parser.add_argument("--work-dir", required=True, type=Path, help="new immutable evidence directory")
    args = parser.parse_args()

    library_path = args.library.resolve()
    if not library_path.is_file():
        raise RuntimeError(f"library is not a regular file: {library_path}")
    work = args.work_dir.resolve()
    if work.exists():
        raise RuntimeError(f"work directory already exists; refusing to overwrite evidence: {work}")
    work.mkdir(parents=True)
    splice = bind(library_path)
    source = (b"CIX ABI callback fixture: short reads and short writes.\n" * 23) + bytes(range(64))
    results: dict[str, object] = {
        "purpose": "frozen cix_squash_splice ABI callback validation; not SquashFS or plugin-load validation",
        "library": str(library_path),
        "source": {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()},
        "valid_levels": {},
        "invalid_calls": {},
        "sdk_plugin_load": "not tested: Squash 0.8 SDK/plugin loader is a separate qualification",
    }

    archives: list[bytes] = []
    for level in (1, 6):
        status, reader, writer = invoke(splice, 1, level, source)
        if status != STATUS_OK:
            raise RuntimeError(f"ABI encode failed at level {level}: status {status}")
        archive = bytes(writer.output)
        if not archive:
            raise RuntimeError(f"ABI encode returned an empty archive at level {level}")
        decode_status, decode_reader, decode_writer = invoke(splice, 2, 0, archive)
        if decode_status != STATUS_OK or bytes(decode_writer.output) != source:
            raise RuntimeError(f"ABI decode failed to restore level-{level} data")
        results["valid_levels"][str(level)] = {
            "archive_bytes": len(archive),
            "archive_sha256": hashlib.sha256(archive).hexdigest(),
            "encode_callbacks": {"read_calls": reader.calls, "write_calls": writer.calls, "max_read_request": reader.max_requested, "max_write_request": writer.max_requested},
            "decode_callbacks": {"read_calls": decode_reader.calls, "write_calls": decode_writer.calls, "max_read_request": decode_reader.max_requested, "max_write_request": decode_writer.max_requested},
            "exact_restore": True,
        }
        archives.append(archive)

    representative = archives[-1]
    results["invalid_calls"] = {
        "invalid_direction": assert_rejected(splice, "invalid_direction", 0, 1, source),
        "invalid_level_low": assert_rejected(splice, "invalid_level_low", 1, 0, source),
        "invalid_level_high": assert_rejected(splice, "invalid_level_high", 1, 10, source),
        "null_read_callback": assert_rejected(splice, "null_read_callback", 1, 1, source, null_read=True),
        "null_write_callback": assert_rejected(splice, "null_write_callback", 1, 1, source, null_write=True),
        "truncated_archive": assert_rejected(splice, "truncated_archive", 2, 0, representative[:-1]),
        "corrupted_archive": assert_rejected(splice, "corrupted_archive", 2, 0, bytes([representative[0] ^ 1]) + representative[1:]),
    }
    evidence = work / "evidence.json"
    evidence.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "evidence": str(evidence)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ctypes.ArgumentError) as error:
        print(f"cix_squash_splice ABI test failed: {error}", file=sys.stderr)
        raise SystemExit(1)
