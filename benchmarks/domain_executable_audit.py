#!/usr/bin/env python3
"""Freeze a whole installed ELF and emit provenance plus adapter coverage.

This command never invokes PAQ.  A scheduler-owned comparison may later feed
the original bytes and the complete adapter frame to the same PAQ configuration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmarks import domain_executable_adapter as adapter


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(source: Path, freeze_to: Path | None = None) -> dict:
    source = source.resolve()
    data = source.read_bytes()
    if freeze_to is not None:
        freeze_to = freeze_to.resolve()
        freeze_to.parent.mkdir(parents=True, exist_ok=True)
        if freeze_to.exists() and sha(freeze_to) != hashlib.sha256(data).hexdigest():
            raise ValueError("refuse to overwrite a different frozen input")
        if not freeze_to.exists():
            shutil.copyfile(source, freeze_to)
        frozen = {"path": str(freeze_to), "sha256": sha(freeze_to), "bytes": freeze_to.stat().st_size}
    else:
        frozen = None
    raw, address, packed = (adapter.encode(data, variant) for variant in ("raw", "address", "address-packed"))
    if any(adapter.decode(frame) != data for frame in (raw, address, packed)):
        raise AssertionError("adapter round trip failed")
    return {"schema": "cix-domain-executable-audit-v1", "status": "READ_ONLY_TRANSFORM_PROFILE",
            "source": {"path": str(source), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            "frozen_copy": frozen, "coverage": adapter.inspect(data),
            "frames": {"raw_bytes": len(raw), "address_bytes": len(address), "address_packed_bytes": len(packed),
                       "raw_overhead_bytes": len(raw) - len(data),
                       "address_overhead_bytes": len(address) - len(data),
                       "address_packed_overhead_bytes": len(packed) - len(data),
                       "address_packed_saved_vs_address_bytes": len(address) - len(packed)},
            "backend": "NOT_RUN", "comparison_contract":
            "Run original bytes and each complete archive-only frame through identical scheduler-owned PAQ settings; include all frame bytes and report PAQ capacity-sharing limits."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--freeze-to", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    row = audit(args.input, args.freeze_to)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
