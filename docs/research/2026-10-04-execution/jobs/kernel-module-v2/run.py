"""Leased v2 build derived from the reviewed v1 dispatcher with fresh paths."""
import os
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE") == "1"
root = Path(__file__).resolve().parents[5]
v1 = root / "docs/research/2026-10-04-execution/jobs/kernel-module-v1/run.py"
source = v1.read_text(encoding="utf-8").replace("kernel-module-v1", "kernel-module-v2")
exec(compile(source, str(__file__), "exec"), {"__file__": str(__file__), "__name__": "__main__"})
