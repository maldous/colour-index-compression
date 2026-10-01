#!/usr/bin/env python3
"""Invoke a snapshotted native Rust CIX CLI for local benchmark cells.

Normal profiles deliberately leave container, route, backend, block, memory,
and worker selection to CIX.  Expert arguments are recorded and forwarded only
when a matrix explicitly asks for one; historical fixed-format matrices keep
using those explicit arguments as historical evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ALIASES = {
    "fast": "fast",
    "default": "default",
    "best": "best",
    # These names are retained only to read historical matrix recipes. New
    # records use the normal CIX effort names.
    "current": "default",
    "size": "best",
}
ROUTES = (
    "auto", "raw", "runs", "composition", "lz", "predictor", "bwt",
    "stride", "phrases", "ppm", "mixture", "deflate",
)


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


def normalize_profile(profile: str) -> str:
    """Return the canonical user-facing effort label for a requested profile."""
    try:
        return PROFILE_ALIASES[profile]
    except KeyError as error:
        raise ValueError(f"unsupported Rust CIX profile: {profile}") from error


def build_command(
    operation: str,
    cix: Path,
    uncix: Path,
    source: Path,
    destination: Path,
    profile: str,
    *,
    format_name: str = "auto",
    threads: int | None = None,
    memory: str | None = None,
    block_size: str | None = None,
    route: str | None = None,
    backend: str | None = None,
    stream: bool = False,
) -> list[str]:
    """Build one CLI command without imposing hidden benchmark settings.

    `default` intentionally adds no effort option so the binary's ordinary
    invocation is measured. `fast` and `best` are semantic effort requests,
    not format or codec presets. Every remaining argument is an explicit
    experimental override supplied by the calling matrix.
    """
    if operation not in {"encode", "decode"}:
        raise ValueError(f"unsupported Rust CIX operation: {operation}")
    normalized = normalize_profile(profile)
    if operation == "decode":
        command = [str(uncix)]
    else:
        command = [str(cix)]
        if normalized == "fast":
            command.append("--fast")
        elif normalized == "best":
            command.append("--best")

    # CIX auto format is selected by omission. The remaining options are all
    # expert controls, never profile defaults.
    if operation == "encode" and format_name != "auto":
        command.extend(("--format", format_name))
    if operation == "encode" and route and route != "auto":
        command.extend(("--route", route))
    if operation == "encode" and backend:
        command.extend(("--backend", backend))
    if operation == "encode" and block_size:
        command.extend(("--block-size", block_size))
    if memory:
        command.extend(("--memory", memory))
    if operation == "encode" and threads is not None:
        command.extend(("--threads", str(threads)))
    if stream:
        command.append("--stream")
    command.extend(("-f", "-o", str(destination), str(source)))
    return command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILE_ALIASES), default="default")
    parser.add_argument("--format", choices=("auto", "cixg1", "cixg2", "cixm6", "cixf1"), default="auto")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--memory")
    parser.add_argument("--block-size")
    parser.add_argument("--route", choices=ROUTES)
    parser.add_argument("--backend")
    parser.add_argument("--stream", action="store_true")
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    args.workdir.mkdir(parents=True, exist_ok=True)
    normalized_profile = normalize_profile(args.profile)
    cix, cix_hash = executable("cix", args.workdir)
    uncix, uncix_hash = executable("uncix", args.workdir)
    command = build_command(
        args.operation,
        cix,
        uncix,
        args.source,
        args.destination,
        args.profile,
        format_name=args.format,
        threads=args.threads,
        memory=args.memory,
        block_size=args.block_size,
        route=args.route,
        backend=args.backend,
        stream=args.stream,
    )
    stdout, stderr = invoke(command)
    record = {
        "client": "native Rust CIX CLI",
        "operation": args.operation,
        "requested_profile": args.profile,
        "normalized_profile": normalized_profile,
        "expert_overrides": {
            "format": args.format if args.operation == "encode" and args.format != "auto" else None,
            "threads": args.threads if args.operation == "encode" else None,
            "memory": args.memory,
            "block_size": args.block_size if args.operation == "encode" else None,
            "route": args.route if args.operation == "encode" else None,
            "backend": args.backend if args.operation == "encode" else None,
            "stream": args.stream,
        },
        "binary_stamps": {
            "cix": {"source": str(ROOT / "dist" / "cix"), "sha256": cix_hash},
            "uncix": {"source": str(ROOT / "dist" / "uncix"), "sha256": uncix_hash},
        },
        "command": command,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }
    print(json.dumps(record, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
