#!/usr/bin/env python3
"""Generate tiny deterministic reference vectors; never a corpus input."""
import hashlib
import json
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from runtime.cix_runtime.legacy import mysql_fixed_columns, mysql_record_constraints, record_float_grid

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"


def record(key: int, address: bytes) -> bytes:
    day = mysql_record_constraints.datetime.date(2024, 2, 3).toordinal().to_bytes(4, "little")
    row = [
        key.to_bytes(4, "little"), (9).to_bytes(4, "little"), (3).to_bytes(4, "little"),
        (7).to_bytes(4, "little"), b"\0\0\0\0\x031.0", day,
        b"CODE      ", b"NAME                ", address,
    ]
    return mysql_record_constraints.wrap(mysql_record_constraints.join_fields(row))


def grid() -> bytes:
    records = 3
    header = struct.pack("<7i", 0, 0, records, 0, 1, 1, 28)
    rows = []
    for index in range(records):
        rows.append(struct.pack("<ddIf", 1.25 + index / 10, -2.5 + index / 8, 0x7FC00000 + index, 3.5 + index / 16) + bytes([index + 1]) * 4)
    return header + b"".join(rows)


def save(name: str, data: bytes, manifest: dict) -> None:
    path = OUT / name
    path.write_bytes(data)
    manifest[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"generator": "runtime legacy reference modules; tiny deterministic fixtures", "files": {}}
    source = record(5, b"short address") + b"literal tail"
    save("record.input", source, manifest["files"])
    for mode in range(5):
        save(f"record-mycs-mode{mode}.raw", mysql_record_constraints.transform(source, mode)[0], manifest["files"])
    for mode in range(1, 5):
        save(f"record-mycc-mode{mode}.raw", mysql_fixed_columns.transform(source, mode)[0], manifest["files"])
    source = grid()
    save("grid.input", source, manifest["files"])
    for mode in range(4):
        save(f"grid-sagr-mode{mode}.raw", record_float_grid.transform(source, mode)[0], manifest["files"])
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
