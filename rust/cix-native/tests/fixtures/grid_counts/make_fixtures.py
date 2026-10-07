"""Scheduled Python-reference fixtures for SGCC1 and SGCC2 historical grids."""
from __future__ import annotations
import hashlib, json, struct, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime.legacy import grid_context, grid_conditional  # noqa: E402
OUT = Path(__file__).parent


def _bits_for_quantized(q: int, scale: float, width: int, residue: int) -> bytes:
    """Make one finite grid value whose signed bit-pattern residue is tiny."""
    if width == 8:
        predicted = int(np.asarray([float(q) * scale], dtype="<f8").view("<u8")[0])
        return ((predicted + residue) & ((1 << 64) - 1)).to_bytes(8, "little")
    predicted = int(np.asarray([float(q) * scale], dtype="<f4").view("<u4")[0])
    return ((predicted + residue) & ((1 << 32) - 1)).to_bytes(4, "little")


def _mixed_q(index: int) -> int:
    """Exercise signs, bit lengths and all modulo-sixteen partition keys."""
    magnitude = (1 << (index % 11)) + (index % 16)
    return -magnitude if index & 1 else magnitude


def branch_source(records: int = 1100) -> bytes:
    """A valid SAO grid with tag-one corrections and a 1024-ID group boundary.

    Field 0 has varied negative/positive coordinates; field 8 is a single
    1,100-record coordinate group.  All four fields use only {-1, 0, 1}
    bit-pattern corrections, preventing the ordinary tag-zero fallback.
    """
    # WCSTools declares its row count in header field three; the surrounding
    # values match the legacy recognizer's admitted seven-int subset.
    header = struct.pack("<7i", 17, -9, records, 0, 1, 1, 28)
    scales = [float.fromhex(scale) for _, _, scale in grid_conditional.grid.FIELDS]
    out = bytearray(header)
    for index in range(records):
        row = bytearray(28)
        row[16:20] = ((index * 0x9e3779b1) & 0xffffffff).to_bytes(4, "little")
        coordinates = (
            _mixed_q(index), 7, _mixed_q(index * 13 + 5), _mixed_q(index * 29 + 3)
        )
        for (offset, width, _), scale, q in zip(
            grid_conditional.grid.FIELDS, scales, coordinates
        ):
            row[offset : offset + width] = _bits_for_quantized(
                q, scale, width, (-1, 0, 1)[index % 3]
            )
        out.extend(row)
    return bytes(out)


SOURCE = branch_source()


def main() -> None:
    if not grid_conditional.grid.recognizes(SOURCE):
        raise AssertionError("branch fixture must remain a valid SAO grid")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "input.bin").write_bytes(SOURCE)
    rows = {}
    for mode in range(5):
        raw, stats = grid_context.transform(SOURCE, mode)
        assert grid_context.inverse(raw) == SOURCE
        name = f"sgcc1-mode{mode}.raw"
        (OUT / name).write_bytes(raw)
        rows[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "transform_stats": stats,
        }
    for context in range(4):
        for coding in range(3):
            raw, stats = grid_conditional.transform(SOURCE, context, coding)
            assert grid_conditional.inverse(raw) == SOURCE
            if any(field["raw_fallback"] for field in stats["fields"]):
                raise AssertionError("branch fixture must retain tag-one corrections")
            name = f"sgcc2-context{context}-coding{coding}.raw"
            (OUT / name).write_bytes(raw)
            rows[name] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "transform_stats": stats,
            }
    coverage = {
        "records": 1100,
        "coordinate_partition_coverage": "mixed signs, bit lengths and modulo-16 values",
        "constant_coordinate_field": {"offset": 8, "coordinate": 7, "symbols": 1100, "type_class_blocks": [1024, 76]},
        "correction_palette": [-1, 0, 1],
        "tag_zero_fallback": False,
    }
    manifest = {
        "generator": "legacy.grid_context/grid_conditional.transform",
        "input_sha256": hashlib.sha256(SOURCE).hexdigest(),
        "input_bytes": len(SOURCE),
        "coverage": coverage,
        "raw": rows,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
if __name__ == "__main__": main()
