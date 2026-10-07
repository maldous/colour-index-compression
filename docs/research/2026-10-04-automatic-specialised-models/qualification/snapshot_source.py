"""Copy only maintained source and required backend source into a fresh snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def ignored(directory, names):
    return {name for name in names if name in {".git", "__pycache__", "target", ".pytest_cache"}
            or name.endswith((".pyc", ".pyo"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        raise SystemExit("refusing to overwrite source snapshot")
    destination.mkdir(parents=True)
    shutil.copytree(args.native, destination / "native", ignore=ignored)
    shutil.copytree(ROOT / "runtime", destination / "runtime", ignore=ignored)
    sources = json.loads((ROOT / "runtime/backend-sources.json").read_text())
    for name, entry in sources["base"].items():
        shutil.copytree(ROOT / entry["source"], destination / "vendor/paq" / name, ignore=ignored)
    shutil.copy2(HERE / "INTEGRATED-SOURCE-README.md", destination / "README.md")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.txt", "THIRD_PARTY_NOTICES_RUST.md"):
        shutil.copy2(args.native / name, destination / name)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (destination / "SOURCE-REVISION.json").write_text(json.dumps({
        "development_revision": revision,
        "native_source": str(args.native.resolve()),
        "scope": "private host-qualified integrated source snapshot; not a portable installer",
        "backend_source_locations": sources["base"],
    }, indent=2) + "\n")
    files = [{"path": str(path.relative_to(destination)), "bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
             for path in sorted(destination.rglob("*")) if path.is_file()]
    args.receipt.write_text(json.dumps({"source_revision": revision,
        "destination": str(destination), "files": files,
        "source_bytes": sum(row["bytes"] for row in files)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
