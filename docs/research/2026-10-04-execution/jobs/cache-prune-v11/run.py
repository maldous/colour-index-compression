"""Reclaim reproducible compiler caches; retain source and compiler metadata."""
import hashlib
import json
import os
from pathlib import Path

if os.environ.get("CIX_RELEASE_LEASE") != "1":
    raise RuntimeError("root scheduler lease required")
root = Path(__file__).resolve().parents[5]
target = root / "benchmark-work/native-rc-check-v1/target/debug"
paths = list((target / "deps").glob("*.rmeta"))
paths += [path for path in (target / "build").rglob("*") if path.suffix in {".o", ".a"}]
removed = []
for path in sorted(paths):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open("rb") as stream:
        identity = hashlib.file_digest(stream, "sha256").hexdigest()
    stat = path.stat()
    removed.append({"path": str(path), "bytes": stat.st_size,
                    "allocated_bytes": stat.st_blocks * 512, "sha256": identity})
    path.unlink()
receipt = {"reason": "Sonar probe-v10 refused the aggregate temporary reservation before launch",
           "removed_reproducible_cache": removed,
           "preserved": "All source snapshots, depfiles, compiler databases, installed SDK/provider artifacts, CLI binaries, test results and raw evidence",
           "status": "pass"}
Path(__file__).with_name("receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
