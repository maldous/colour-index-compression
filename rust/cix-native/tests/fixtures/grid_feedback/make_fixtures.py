"""Freeze the six legacy SGFB1 feedback-policy raw streams.

Run this deliberately only under the repository's scheduled focused-fixture
job.  The manifest carries full hexadecimal raw identities as well as hashes,
so a Rust compatibility test can distinguish an algorithmic round-trip from
the retained Python wire format.
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime.legacy import grid_feedback  # noqa: E402

OUT = Path(__file__).parent
# Seven little-endian header integers followed by three fixed-width records.
# The unusual row bytes exercise signed residues and non-identical coordinates.
SOURCE = struct.pack("<7i", 17, -9, 3, 0, 1, -1, 28) + bytes(
    (index * 37 + 11) & 0xFF for index in range(3 * 28)
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "input.bin").write_bytes(SOURCE)
    raws: dict[str, dict[str, str]] = {}
    for mode in (1, 2, 3):
        for model in (0, 1):
            raw, _ = grid_feedback.transform(SOURCE, mode, model)
            assert grid_feedback.inverse(raw) == SOURCE
            name = f"mode{mode}-model{model}.raw"
            (OUT / name).write_bytes(raw)
            raws[name] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "hex": raw.hex(),
            }
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "generator": "runtime.cix_runtime.legacy.grid_feedback.transform",
                "input_sha256": hashlib.sha256(SOURCE).hexdigest(),
                "input_hex": SOURCE.hex(),
                "raw": raws,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
