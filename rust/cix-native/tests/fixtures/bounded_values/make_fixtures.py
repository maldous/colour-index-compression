"""Freeze tiny retained CIXB1E raw parents from the legacy implementation."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from runtime.cix_runtime.legacy import grid_backend  # noqa: E402
INPUT = ROOT / "rust/cix-native/tests/fixtures/conditional_values/input.bin"
OUT = Path(__file__).parent
data = INPUT.read_bytes()
rows = {}
for mode in (1, 2, 3, 4):
    raw, _ = grid_backend.transform(data, mode)
    assert grid_backend.inverse(raw, mode) == data
    name = f"mode{mode}.raw"
    (OUT / name).write_bytes(raw)
    rows[name] = hashlib.sha256(raw).hexdigest()
(OUT / "input.bin").write_bytes(data)
(OUT / "manifest.json").write_text(json.dumps({"generator": "runtime.cix_runtime.legacy.grid_backend.transform", "input_sha256": hashlib.sha256(data).hexdigest(), "raw_sha256": rows}, indent=2, sort_keys=True)+"\n")
