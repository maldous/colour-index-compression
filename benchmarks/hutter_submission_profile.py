#!/usr/bin/env python3
"""Build an auditable *draft* offline CIX text-profile bundle for Hutter work.

The bundle is deliberately not a Prize submission: this repository has no
project license or public release.  It makes its exact bytes and dependencies
visible so those gaps cannot be hidden when a real package is eventually made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


PROFILE = {
    "name": "cix-stdlib-text-v1-draft",
    "entrypoint": "hutter_cix.py",
    "compression_command": ["python3", "hutter_cix.py", "encode", "INPUT", "ARCHIVE", "-9", "--no-bwt"],
    "decompression_command": ["python3", "hutter_cix.py", "decode", "ARCHIVE", "RESTORED"],
    "dependency_policy": "Python 3.11+ standard library only; BWT disabled so no optional suffix-array module is required.",
    "submission_status": "DRAFT_NOT_ELIGIBLE_NO_PROJECT_LICENSE_OR_PUBLIC_RELEASE",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profile_files(source_root: Path) -> list[Path]:
    files = sorted((source_root / "cix").glob("*.py"))
    if not files:
        raise ValueError("source root does not contain cix/*.py")
    runner = source_root / "benchmarks" / "hutter_cix.py"
    if not runner.is_file():
        raise ValueError("source root does not contain benchmarks/hutter_cix.py")
    return files + [runner]


def build_draft(source_root: Path, output: Path) -> dict:
    files = profile_files(source_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(source_root).as_posix())
    inventory = [{"path": path.relative_to(source_root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files]
    return {**PROFILE, "source_root": str(source_root), "bundle": {"path": str(output), "bytes": output.stat().st_size,
            "sha256": sha256(output), "files": inventory, "file_count": len(inventory)},
            "hutter_split_accounting_note": "A same source bundle used as compressor and decoder still counts twice in the split formula.",
            "missing": ["project OSI license", "public documented release", "whole-enwik9 archive and receipt", "resource measurement"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = build_draft(args.source_root.resolve(), args.output)
    args.manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
