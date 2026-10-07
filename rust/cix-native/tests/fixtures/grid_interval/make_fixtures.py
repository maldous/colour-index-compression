"""Freeze tiny and 256-boundary SGBI1 policy streams from the Python reference."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime.legacy import grid_interval  # noqa: E402

OUT = Path(__file__).parent
TINY_SOURCE = struct.pack("<7i", 17, -9, 3, 0, 1, -1, 28) + bytes(
    (index * 37 + 11) & 0xFF for index in range(3 * 28)
)


def boundary_source() -> bytes:
    """Make 300 records with varied quantized coordinates in all four fields."""
    scales = (
        float.fromhex("0x1.3856bdf09d18ep-24"),
        float.fromhex("0x1.a073a7eb7c212p-25"),
        float.fromhex("0x1.f3bdfcb42e8e1p-28"),
        float.fromhex("0x1.4d295322c9b40p-28"),
    )
    records = 300
    data = bytearray(struct.pack("<7i", 17, -9, records, 0, 1, -1, 28))
    for index in range(records):
        row = bytearray(28)
        struct.pack_into("<d", row, 0, (((index * 17) % 29) - 14) * scales[0])
        struct.pack_into("<d", row, 8, ((index % 2) - 1) * scales[1])
        row[16:20] = bytes((index * 13 + lane * 41) & 0xFF for lane in range(4))
        struct.pack_into("<f", row, 20, (((index * 3) % 7) - 3) * scales[2])
        struct.pack_into("<f", row, 24, (((index * index) % 11) - 5) * scales[3])
        data.extend(row)
    return bytes(data)


CASES = {"tiny": TINY_SOURCE, "boundary256": boundary_source()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases: dict[str, dict[str, object]] = {}
    for case, source in CASES.items():
        input_name = f"{case}-input.bin"
        (OUT / input_name).write_bytes(source)
        raws: dict[str, dict[str, str]] = {}
        for policy in (1, 2, 3):
            raw, _ = grid_interval.transform(source, policy=policy, block=256)
            assert grid_interval.inverse(raw) == source
            name = f"{case}-policy{policy}.raw"
            (OUT / name).write_bytes(raw)
            raws[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "hex": raw.hex()}
        cases[case] = {
            "input": input_name,
            "input_sha256": hashlib.sha256(source).hexdigest(),
            "input_hex": source.hex(),
            "records": (len(source) - 28) // 28,
            "raw": raws,
        }
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "generator": "runtime.cix_runtime.legacy.grid_interval.transform",
                "block": 256,
                "cases": cases,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
