#!/usr/bin/env python3
"""Focused staged-runtime specialist smoke qualification.

This script is inert unless ``--execute`` is supplied by the root scheduler.
It generates tiny schema fixtures locally, uses only the staged Python package
and staged libexec backends, then decodes every saved archive in a fresh Python
process through ``cix_runtime.engine.decode``.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tarfile

MEMORY_BYTES = 5_500_000_000


def _sdf() -> bytes:
    return (b"CIX\n  smoke\n\n"
            b"  1  0  0  0  0  0            999 V2000\n"
            b"    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
            b"M  END\n$$$$\n")


def _myisam_record(seed: int) -> bytes:
    """Reproduce the supported canonical MyISAM field and wrapper layout."""
    date = datetime.date(2020, 1, 1 + seed)
    money = b"\0\0\0\0\x031.0"
    address = b"address".ljust(80)
    body = (b"\x60\0" + (seed + 1).to_bytes(4, "little")
            + (seed + 10).to_bytes(4, "little") + seed.to_bytes(4, "little")
            + (seed * 100).to_bytes(4, "little") + money
            + bytes([len(f"{date.month}/{date.day}/{date.year}")])
            + f"{date.month}/{date.day}/{date.year}".encode()
            + b"CODE".ljust(10) + b"name".ljust(20) + address)
    if len(body) % 4 == 1:
        return b"\x01" + len(body).to_bytes(2, "big") + body
    padding = (-len(body)) % 4
    return b"\x03" + len(body).to_bytes(2, "big") + bytes([padding]) + body + bytes(padding)


def _grid() -> bytes:
    count = 32
    header = struct.pack("<7i", 0, 1, count, 0, 1, 1, 28)
    rows = b"".join(struct.pack("<dd2shff", i / 100.0, i / 200.0, b"A0", i,
                                 i / 1000.0, -i / 2000.0) for i in range(count))
    return header + rows


def _elf() -> bytes:
    header = bytearray(64)
    header[:7] = b"\x7fELF\x02\x01\x01"
    header[52:54] = (64).to_bytes(2, "little")
    return bytes(header)


def _ecoff_got_tar() -> bytes:
    """A self-contained GOT fixture with no corpus-specific positions."""
    names = b"\0alpha\0beta\0"
    symbols = b"".join(struct.pack("<IIQIBBH", offset, 0, value, 0, 0x12, 0, 0xff01)
                       for offset, value in zip((0, 1, 7), (0, 99, 42)))
    dynamic = b"".join(struct.pack("<IIQ", tag, 0, value | (0xdeadbeef << 32))
                        for tag, value in ((0x7000000a, 0), (0x70000013, 0),
                                           (0x70000011, 3), (0, 0)))
    parts = ((b".dynstr", names), (b".dynsym", symbols),
             (b".hash", struct.pack("<7I", 2, 3, 0, 0, 0, 0, 0)),
             (b".dynamic", dynamic), (b".got", struct.pack("<3Q", 0, 99, 42)))
    obj = bytearray(104 + 64 * len(parts))
    struct.pack_into("<HHIQIHH", obj, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for index, (name, raw) in enumerate(parts):
        offset = len(obj)
        obj.extend(raw)
        struct.pack_into("<8sQQQQQQHHI", obj, 104 + 64 * index, name, 0, 0,
                         len(raw), offset, 0, 0, 0, 0, 0)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo("embedded-alpha-ecoff-got")
        entry.size = len(obj)
        archive.addfile(entry, io.BytesIO(obj))
    return stream.getvalue() + b"smoke trailer"


def _ecoff_section() -> bytes:
    """Minimal validated section/function pointer fixture."""
    text = 0x120000000
    rdata = 0x200000000
    names = b"\0.text\0.rdata\0funcA\0funcB\0"
    symbols = b"".join(struct.pack("<IIQIBBH", offset, 0, value, 0, 0x12, 0, 0xff01)
                       for offset, value in ((0, 0), (1, text + 4), (7, rdata), (14, text + 8), (20, text + 16)))
    targets = (text + 8, text + 12, text + 3, (1 << 64) - 1, rdata + 16, rdata + 8)
    relocs = b"".join(struct.pack("<QII", rdata + index * 8, (symbol << 8) | 2, 0)
                       for index, symbol in enumerate((1, 1, 1, 1, 2, 2)))
    parts = ((b".dynstr", 0, names), (b".dynsym", 0, symbols),
             (b".hash", 0, struct.pack("<9I", 2, 5, 0, 0, 0, 0, 0, 0, 0)),
             (b".pdata", text - 1024, struct.pack("<6i", 1024, 0, 1032, 0, 1040, 0)),
             (b".text", text, bytes(32)), (b".rdata", rdata, struct.pack("<6Q", *targets)),
             (b".rel.dyn", 0, relocs))
    obj = bytearray(104 + 64 * len(parts))
    struct.pack_into("<HHIQIHH", obj, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for index, (name, address, raw) in enumerate(parts):
        offset = len(obj)
        obj.extend(raw)
        struct.pack_into("<8sQQQQQQHHI", obj, 104 + 64 * index, name, 0, address,
                         len(raw), offset, 0, 0, 0, 0, 0)
    return bytes(obj)


def _ecoff_tar() -> bytes:
    """A valid Alpha ECOFF object inside a TAR member at nonzero offset."""
    names = b"\0alpha\0beta\0"
    virtual = 0x120002000
    symbols = b"".join(struct.pack("<IIQIBBH", offset, 0, value, 0, 0x12, 0, 0xff01)
                       for offset, value in zip((0, 1, 7), (0, 99, 42)))
    relocs = b"".join(struct.pack("<QII", virtual + 8 * index, (symbol << 8) | 2, 0)
                      for index, symbol in enumerate((1, 2)))
    parts = ((b".dynstr", 0, names), (b".dynsym", 0, symbols),
             (b".hash", 0, struct.pack("<7I", 2, 3, 0, 0, 0, 0, 0)),
             (b".rdata", virtual, struct.pack("<2Q", 99, 42)), (b".rel.dyn", 0, relocs))
    obj = bytearray(104 + 64 * len(parts))
    struct.pack_into("<HHIQIHH", obj, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for index, (name, address, raw) in enumerate(parts):
        offset = len(obj)
        obj.extend(raw)
        struct.pack_into("<8sQQQQQQHHI", obj, 104 + 64 * index, name, address, address,
                         len(raw), offset, 0, 0, 0, 0, 0)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo("embedded-alpha-ecoff")
        entry.size = len(obj)
        archive.addfile(entry, io.BytesIO(obj))
    return stream.getvalue() + b"smoke trailer"


def _section_tar() -> bytes:
    member = _ecoff_section()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo("section-object")
        entry.size = len(member)
        archive.addfile(entry, io.BytesIO(member))
    return stream.getvalue()


ENCODE_PROGRAM = r'''
import hashlib, json, sys
from pathlib import Path
from cix_runtime import backends, specialized
from cix_runtime.legacy import chemical_db, executable, grid_grouped, mysql_fixed_columns, mysql_record_constraints
source = Path(sys.argv[1]).read_bytes(); target = Path(sys.argv[2]); op = sys.argv[3]
try:
    if op == "chemical-geometry": frame = chemical_db.encode_geometry(source, 2)
    elif op == "chemical-hydrogen": frame = chemical_db.encode_hydrogen(source)
    elif op == "database-constraints": frame = mysql_record_constraints.encode(source, 3, 0)[0]
    elif op == "database-remaining": frame = mysql_record_constraints.encode(source, 3, 1, "-8")[0]
    elif op == "database-fixed": frame = mysql_fixed_columns.encode(source, 1)[0]
    elif op == "grid-grouped": frame = grid_grouped.encode(source, 3, "-8")[0]
    elif op in {"ecoff-got", "ecoff-pointer", "ecoff-section"}:
        required = {"ecoff-got": "ecoff-got-mode3-paq", "ecoff-pointer": "ecoff-pointer-mode5-paq", "ecoff-section": "ecoff-section-mode4-paq"}[op]
        admitted = {candidate.id for candidate in specialized.catalog(source)[0]}
        if required not in admitted: raise ValueError("fixture does not admit " + required)
        frame = {"ecoff-got": executable.encode_got, "ecoff-pointer": executable.encode_pointer, "ecoff-section": executable.encode_section}[op](source)
    elif op == "joint-discount": frame = executable.encode_joint_discount(source, 2, "-8")
    elif op == "joint-discount-carrier":
        candidate = next(item for item in specialized.catalog(source)[0] if item.id == "executable-joint-discount")
        frame = candidate.encode(source)
    elif op == "filtered-1": frame = executable.encode_filtered(source, 1)
    elif op == "filtered-2": frame = executable.encode_filtered(source, 2)
    elif op.startswith("paq:"):
        version, options = op.split(":", 1)[1].split(",", 1)
        frame = backends.encode_paq(source, version, options)
    else: raise ValueError("unknown smoke operation: " + op)
    target.write_bytes(frame)
    print(json.dumps({"status":"encoded", "bytes":len(frame), "sha256":hashlib.sha256(frame).hexdigest()}))
except Exception as error:
    print(json.dumps({"status":"gap", "error_type":type(error).__name__, "error":str(error)}))
    raise
'''

DECODE_PROGRAM = r'''
import hashlib, json, sys
from pathlib import Path
from cix_runtime import engine
frame = Path(sys.argv[1]).read_bytes(); expected = sys.argv[2]; maximum = int(sys.argv[3]); memory = int(sys.argv[4])
try:
    restored = engine.decode(frame, max_output_bytes=maximum, memory_bytes=memory)
    digest = hashlib.sha256(restored).hexdigest()
    if digest != expected: raise ValueError("restored digest mismatch")
    print(json.dumps({"status":"decoded", "bytes":len(restored), "sha256":digest}))
except Exception as error:
    print(json.dumps({"status":"gap", "error_type":type(error).__name__, "error":str(error)}))
    raise
'''


def _environment(stage: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(stage / "python" / "site-packages"),
        "LD_LIBRARY_PATH": str(stage / "python" / "site-packages" / "imagecodecs.libs"),
        "CIX_BACKEND_ROOT": str(stage / "libexec" / "cix"),
        "PYTHONHOME": "",
    }


def _run(python: Path, environment: dict[str, str], program: str, *args: str) -> dict:
    completed = subprocess.run([str(python), "-c", program, *args], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    row = json.loads(lines[-1]) if lines else {"status": "gap", "error": "no child receipt"}
    row["exit_code"] = completed.returncode
    if completed.returncode and completed.stderr:
        row["stderr"] = completed.stderr[-4000:]
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--only", help="Run one named operation for a focused regression check")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("plan: pass --execute only from the root scheduler")
        return
    stage = args.stage.resolve()
    python = stage / "python" / "bin" / "python3"
    if not python.is_file() or not (stage / "libexec" / "cix").is_dir():
        raise SystemExit("stage must contain python/bin/python3 and libexec/cix")
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = _environment(stage)
    fixtures = {"sdf": _sdf(), "myisam": b"".join(_myisam_record(i) for i in range(4)),
                "grid": _grid(), "elf": _elf(), "ecoff": _ecoff_tar(), "ecoff-got": _ecoff_got_tar(),
                "ecoff-section": _ecoff_section(), "section-tar": _section_tar()}
    operations = [
        ("chemical-geometry", "sdf"), ("chemical-hydrogen", "sdf"),
        ("database-constraints", "myisam"), ("database-remaining", "myisam"),
        ("database-fixed", "myisam"), ("grid-grouped", "grid"), ("ecoff-got", "ecoff-got"), ("ecoff-pointer", "ecoff"),
        ("ecoff-section", "ecoff-section"), ("joint-discount", "elf"),
        ("joint-discount-carrier", "section-tar"),
        ("filtered-1", "ecoff"), ("filtered-2", "ecoff"),
        ("paq:v215,-8", "elf"), ("paq:v216,-8", "elf"), ("paq:v215,-9L", "elf"),
    ]
    if args.only:
        operations = [item for item in operations if item[0] == args.only]
        if not operations:
            parser.error("--only must name an existing operation")
    report = {"schema": "cix-specialist-smoke-v1", "stage": str(stage), "memory_bytes": MEMORY_BYTES, "rows": []}
    for ordinal, (operation, fixture_name) in enumerate(operations):
        source = work / f"{ordinal:02d}-{fixture_name}.bin"
        archive = work / f"{ordinal:02d}-{operation.replace(':', '-').replace(',', '-')}.cix"
        source.write_bytes(fixtures[fixture_name])
        source_hash = hashlib.sha256(fixtures[fixture_name]).hexdigest()
        encoded = _run(python, env, ENCODE_PROGRAM, str(source), str(archive), operation)
        row = {"operation": operation, "fixture": fixture_name, "input_sha256": source_hash, "encode": encoded}
        if encoded.get("status") == "encoded" and archive.is_file():
            row["decode"] = _run(python, env, DECODE_PROGRAM, str(archive), source_hash,
                                  str(len(fixtures[fixture_name])), str(MEMORY_BYTES))
        else:
            row["decode"] = {"status": "gap", "reason": "encode did not produce an archive"}
        report["rows"].append(row)
    verified = all(row["encode"].get("status") == "encoded" and row["encode"].get("exit_code") == 0
                   and row["decode"].get("status") == "decoded" and row["decode"].get("exit_code") == 0
                   for row in report["rows"])
    report["status"] = "VERIFIED" if verified else "FAILED"
    receipt = work / "smoke-specialists.json"
    receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "rows": len(report["rows"]), "receipt": str(receipt)}))
    if not verified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
