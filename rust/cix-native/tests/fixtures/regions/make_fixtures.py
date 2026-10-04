"""Generate tiny, synthetic reference spans from runtime.cix_runtime.regions.

This is fixture provenance only.  The generated members exercise supported
format syntax and mixed/late placement; they are not benchmark assets.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime import regions  # noqa: E402

OUT = Path(__file__).parent


def dicom_tag(group: int, element: int, value: bytes) -> bytes:
    return struct.pack("<HHI", group, element, len(value)) + value


def sdf() -> bytes:
    return (
        b"prelude\nfixture\nsource\ncomment\n"
        b"  1  0  0  0  0  0            999 V2000\n"
        b"    0.0    0.0    0.0 C   0  0\nM  END\n$$$$\n"
    )


def grid() -> bytes:
    header = struct.pack("<7i", 0, 0, 1, 0, 1, 1, 28)
    return header + bytes(range(28))


def dicom() -> bytes:
    return b"".join((
        dicom_tag(0x28, 0x10, struct.pack("<H", 1)),
        dicom_tag(0x28, 0x11, struct.pack("<H", 2)),
        dicom_tag(0x28, 0x100, struct.pack("<H", 16)),
        dicom_tag(0x7FE0, 0x10, b"\x01\x00\x02\x00"),
    ))


def elf() -> bytes:
    value = bytearray(120)
    value[:4] = b"\x7fELF"
    value[4:7] = b"\x02\x01\x01"
    struct.pack_into("<QQ", value, 32, 64, 0)
    struct.pack_into("<HHHHH", value, 52, 64, 56, 1, 64, 0)
    # The retained scanner reads its six-field `IIQQQQ` prefix and uses the
    # last field as PT_LOAD file size.
    struct.pack_into("<IIQQQQ", value, 64, 1, 0, 0, 0, 0, 120)
    return bytes(value)


CASES = {
    "sdf.bin": sdf(),
    "grid.bin": grid(),
    "dicom.bin": dicom(),
    "elf.bin": elf(),
    "mixed.bin": b"prefix?" + sdf() + b"gap" + grid() + b"late" + dicom() + b"tail" + elf() + b"!",
}

manifest: dict[str, object] = {"generator": "runtime.cix_runtime.regions", "cases": {}}
for name, data in CASES.items():
    (OUT / name).write_bytes(data)
    manifest["cases"][name] = [
        {"start": item.start, "end": item.end, "kind": item.kind}
        for item in regions.regions(data)
    ]
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
