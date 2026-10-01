#!/usr/bin/env python3
"""Invoke the pinned native Rust CIX CLI for bounded Silesia benchmark cells."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "fast": {"level": 1, "block_bytes": 32768, "memory_mib": 256},
    "current": {"level": 6, "block_bytes": 32768, "memory_mib": 384},
    "size": {"level": 9, "block_bytes": 65536, "memory_mib": 512},
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def executable(name: str, workdir: Path) -> tuple[Path, str]:
    source = ROOT / "dist" / name
    if not source.is_file():
        raise FileNotFoundError(f"pinned Rust CIX binary is missing: {source}")
    source_hash = sha(source)
    # The decoder selects its operation from argv[0], so keep the canonical
    # binary basename after copying out of the read-only experiment snapshot.
    destination = workdir / name
    if not destination.exists():
        shutil.copyfile(source, destination)
        destination.chmod(0o555)
    if sha(destination) != source_hash:
        raise RuntimeError(f"copied Rust binary hash mismatch: {name}")
    return destination, source_hash


def invoke(args: list[str]) -> tuple[str, str]:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        detail = result.stderr.decode(errors="replace")[-4000:]
        raise RuntimeError(f"Rust CIX exited {result.returncode}: {detail}")
    return result.stdout.decode(errors="replace"), result.stderr.decode(errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILES), required=True)
    parser.add_argument("--format", choices=("cixg1", "cixm6"), required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    setting = PROFILES[args.profile]
    cix, cix_hash = executable("cix", args.workdir)
    uncix, uncix_hash = executable("uncix", args.workdir)
    memory = f"{setting['memory_mib']}MiB"

    if args.operation == "encode":
        command = [
            str(cix),
            f"-{setting['level']}",
            "--format",
            args.format,
            "--stream",
            "--block-size",
            f"{setting['block_bytes']}B",
            "--memory",
            memory,
            "--threads",
            "1",
            "-f",
            "-o",
            str(args.destination),
            str(args.source),
        ]
    else:
        command = [
            str(uncix),
            "--stream",
            "--memory",
            memory,
            "-f",
            "-o",
            str(args.destination),
            str(args.source),
        ]
    stdout, stderr = invoke(command)
    record = {
        "client": "native Rust CIX CLI",
        "operation": args.operation,
        "format": args.format,
        "profile": args.profile,
        "level": setting["level"],
        "block_bytes": setting["block_bytes"],
        "memory_mib": setting["memory_mib"],
        "cix_binary_sha256": cix_hash,
        "uncix_binary_sha256": uncix_hash,
        "command": command,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }
    print(json.dumps(record, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
