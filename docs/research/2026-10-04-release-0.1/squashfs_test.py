#!/usr/bin/env python3
"""Private release evidence: CIX archive transport through standard SquashFS.

This deliberately does *not* test or claim a native CIX SquashFS compressor.
It verifies a CIX archive as an opaque regular file in a standard, Zstd-labelled
SquashFS image, then performs a fresh CIX decode after `unsquashfs -cat`.

Do not run this before the release-binary freeze.  It creates the supplied
work directory only when it does not already exist, so evidence cannot replace
an earlier run by accident.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import BinaryIO


CHUNK = 1024 * 1024


def digest_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while chunk := source.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def digest_stream(stream: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(CHUNK):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def tool_version(command: str) -> str:
    result = subprocess.run([command, "-version"], text=True, capture_output=True, check=False)
    output = (result.stdout + result.stderr).strip()
    # squashfs-tools 4.6.1 unsquashfs prints its version with exit status 1.
    if not output.startswith(Path(command).name + " version "):
        raise RuntimeError(f"{command} -version did not identify the tool: {output}")
    return output


def require_executable(value: str, label: str) -> str:
    candidate = Path(value)
    resolved = str(candidate.resolve()) if candidate.is_file() else shutil.which(value)
    if not resolved or not Path(resolved).is_file():
        raise RuntimeError(f"{label} executable is unavailable: {value}")
    return resolved


def checked(command: list[str], *, stdout=None) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(command, stdout=stdout, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        rendered = " ".join(command)
        raise RuntimeError(f"command failed ({result.returncode}): {rendered}\n{result.stderr.decode(errors='replace')}")
    return result


def encode(cix: str, source: Path, archive: Path) -> None:
    with archive.open("wb") as destination:
        checked([cix, "-c", str(source)], stdout=destination)


def extract_opaque_payload(unsquashfs: str, image: Path, payload: Path) -> None:
    with payload.open("wb") as destination:
        checked([unsquashfs, "-no-progress", "-cat", str(image), "payload.cix"], stdout=destination)


def fresh_decode_hash(cixcat: str, archive: Path) -> tuple[str, int]:
    process = subprocess.Popen([cixcat, str(archive)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None
    digest, size = digest_stream(process.stdout)
    stderr = process.stderr.read() if process.stderr is not None else b""
    if process.wait() != 0:
        raise RuntimeError(f"cixcat failed for {archive}: {stderr.decode(errors='replace')}")
    return digest, size


def malformed_rejections(cixcat: str, archive: Path, work: Path) -> dict[str, dict[str, int | bool]]:
    encoded = archive.read_bytes()
    if len(encoded) < 2:
        raise RuntimeError("encoded CIX archive is too short for malformed-input checks")
    variants = {
        "truncated-final-byte": encoded[:-1],
        "corrupted-first-byte": bytes([encoded[0] ^ 1]) + encoded[1:],
    }
    results: dict[str, dict[str, int | bool]] = {}
    for name, payload in variants.items():
        path = work / f"invalid-{name}.cix"
        path.write_bytes(payload)
        process = subprocess.run([cixcat, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode == 0:
            raise RuntimeError(f"cixcat accepted malformed archive: {name}")
        results[name] = {
            "rejected": True,
            "returncode": process.returncode,
            "stdout_bytes_before_rejection": len(process.stdout),
        }
    return results


def squashfs_summary(unsquashfs: str, image: Path) -> str:
    result = checked([unsquashfs, "-s", str(image)], stdout=subprocess.PIPE)
    return result.stdout.decode(errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path, help="existing small, real input file")
    parser.add_argument("--work-dir", required=True, type=Path, help="new directory for this immutable evidence run")
    parser.add_argument("--cix", required=True, help="frozen release cix executable")
    parser.add_argument("--cixcat", required=True, help="frozen release cixcat executable")
    parser.add_argument("--mksquashfs", default="mksquashfs")
    parser.add_argument("--unsquashfs", default="unsquashfs")
    parser.add_argument("--max-fixture-bytes", type=int, default=16 * 1024 * 1024)
    parser.add_argument(
        "--squashfs-data-compression",
        choices=("off", "on"),
        default="off",
        help="off uses -noD so the already-compressed CIX payload remains opaque",
    )
    args = parser.parse_args()

    fixture = args.fixture.resolve()
    if not fixture.is_file():
        raise RuntimeError(f"fixture is not a regular file: {fixture}")
    source_sha256, source_bytes = digest_file(fixture)
    if source_bytes > args.max_fixture_bytes:
        raise RuntimeError(f"fixture is {source_bytes} bytes; limit is {args.max_fixture_bytes}")
    work = args.work_dir.resolve()
    if work.exists():
        raise RuntimeError(f"work directory already exists; refusing to overwrite evidence: {work}")
    work.mkdir(parents=True)

    cix = require_executable(args.cix, "cix")
    cixcat = require_executable(args.cixcat, "cixcat")
    mksquashfs = require_executable(args.mksquashfs, "mksquashfs")
    unsquashfs = require_executable(args.unsquashfs, "unsquashfs")
    payload = work / "payload.cix"
    staging = work / "staging"
    staging.mkdir()
    image = work / "payload.sqfs"

    encode(cix, fixture, payload)
    payload_sha256, payload_bytes = digest_file(payload)
    shutil.copy2(payload, staging / "payload.cix")
    build_command = [
        mksquashfs, str(staging), str(image), "-noappend", "-comp", "zstd",
        "-processors", "1", "-all-time", "0", "-mkfs-time", "0", "-no-xattrs", "-no-progress",
    ]
    if args.squashfs_data_compression == "off":
        build_command.append("-noD")
    checked(build_command)
    summary = squashfs_summary(unsquashfs, image)
    if "Compression zstd" not in summary:
        raise RuntimeError("image summary did not identify standard Zstd SquashFS compression")

    extracted = work / "extracted-payload.cix"
    extract_opaque_payload(unsquashfs, image, extracted)
    extracted_sha256, extracted_bytes = digest_file(extracted)
    if (extracted_sha256, extracted_bytes) != (payload_sha256, payload_bytes):
        raise RuntimeError("SquashFS transport changed the opaque CIX archive")
    restored_sha256, restored_bytes = fresh_decode_hash(cixcat, extracted)
    if (restored_sha256, restored_bytes) != (source_sha256, source_bytes):
        raise RuntimeError("fresh CIX decode does not restore the source hash")

    evidence = {
        "purpose": "CIX archive transport through standard SquashFS; not native CIX filesystem compression",
        "fixture": {"path": str(fixture), "bytes": source_bytes, "sha256": source_sha256},
        "cix_archive": {"bytes": payload_bytes, "sha256": payload_sha256},
        "squashfs": {
            "image": str(image),
            "bytes": image.stat().st_size,
            "compressor": "zstd",
            "data_compression": args.squashfs_data_compression,
            "build_command": build_command,
            "summary": summary,
        },
        "opaque_payload_round_trip": {"bytes": extracted_bytes, "sha256": extracted_sha256},
        "fresh_cixcat_restore": {"bytes": restored_bytes, "sha256": restored_sha256},
        "malformed_cix_archive_rejections": malformed_rejections(cixcat, payload, work),
        "tools": {
            "cix": cix,
            "cixcat": cixcat,
            "mksquashfs": tool_version(mksquashfs),
            "unsquashfs": tool_version(unsquashfs),
        },
    }
    (work / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "evidence": str(work / "evidence.json")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"squashfs interoperability evidence failed: {error}", file=sys.stderr)
        raise SystemExit(1)
