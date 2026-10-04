"""Freeze a tiny SGCC2 context-3/raw-ID parity vector from the legacy port."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime.legacy import grid_conditional  # noqa: E402

OUT = Path(__file__).parent
SCALES = (float.fromhex("0x1.3856bdf09d18ep-24"), float.fromhex("0x1.a073a7eb7c212p-25"), float.fromhex("0x1.f3bdfcb42e8e1p-28"), float.fromhex("0x1.4d295322c9b40p-28"))


def source() -> bytes:
    n = 6
    data = bytearray(struct.pack("<7i", 0, 0, n, 0, 1, 1, 28))
    coordinates = (0, 1, 0, -2, 1, -2)  # repeated and signed groups
    for row, q in enumerate(coordinates):
        record = bytearray(28)
        struct.pack_into("<d", record, 0, q * SCALES[0])
        struct.pack_into("<d", record, 8, (q + row % 2) * SCALES[1])
        record[16:20] = bytes((row, 255 - row, row * 3, 7))
        struct.pack_into("<f", record, 20, (q - 1) * SCALES[2])
        struct.pack_into("<f", record, 24, (q + 2) * SCALES[3])
        # Preserve nonzero correction events, including a one-ULP variation.
        if row == 4:
            bits = struct.unpack_from("<Q", record, 0)[0] + 1
            struct.pack_into("<Q", record, 0, bits)
        data.extend(record)
    return bytes(data)


data = source()
raw, stats = grid_conditional.transform(data, 3, 0)
assert grid_conditional.inverse(raw) == data
(OUT / "input.bin").write_bytes(data)
(OUT / "context3-coding0.raw").write_bytes(raw)
(OUT / "manifest.json").write_text(json.dumps({
    "generator": "runtime.cix_runtime.legacy.grid_conditional.transform(context=3,coding=0)",
    "input_sha256": hashlib.sha256(data).hexdigest(),
    "raw_sha256": hashlib.sha256(raw).hexdigest(),
    "records": stats["records"],
    "field_groups": [item["groups"] for item in stats["fields"]],
    "field_alphabets": [item["alphabet"] for item in stats["fields"]],
}, indent=2, sort_keys=True) + "\n")
