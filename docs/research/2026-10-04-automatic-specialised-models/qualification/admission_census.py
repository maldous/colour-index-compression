"""Read-only candidate admission census; no candidate encoder is invoked."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from cix_runtime import engine


def main() -> None:
    repository, destination = map(Path, sys.argv[1:])
    plan = json.loads((repository / "docs/research/2026-10-01-rust-native/silesia-plan.json").read_text())
    expected = {"mozilla": "executable-joint-discount", "mr": "volume-mode3-effort10-shared-cixi2",
                "nci": "chemical-hydrogen-paq-v215-8", "osdb": "database-remaining-count-paq-v215-8",
                "sao": "grouped-prediction-context3-paq-v215-8", "webster": "paq-v215-9L"}
    rows = []
    for item in plan["inputs"]:
        data = Path(item["path"]).read_bytes()
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise RuntimeError("canonical input identity mismatch")
        candidates, diagnostics = engine.catalog(data, "best", 4, engine.DEFAULT_MEMORY)
        admitted = [candidate.id for candidate in candidates
                    if engine._admitted(candidate, memory_bytes=engine.DEFAULT_MEMORY, threads=4)[0]]
        target = expected.get(item["name"], "paq-v216-8")
        rows.append({"member": item["name"], "bytes": len(data), "sha256": item["sha256"],
                     "expected_historical_family": target, "covered": target in admitted,
                     "admitted": admitted, "recognition": diagnostics})
        destination.write_text(json.dumps({"status": "RUNNING", "rows": rows}, indent=2) + "\n")
    status = "PASS" if all(row["covered"] for row in rows) else "FAIL"
    destination.write_text(json.dumps({"status": status, "scope": "read-only admission; no encoding or quality result",
                                      "rows": rows}, indent=2) + "\n")
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
