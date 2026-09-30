#!/usr/bin/env python3
"""Independent-chunk PAQ v216 container for bounded local parallel research.

This deliberately has a different format and compression behaviour from the
serial CIX portfolio.  Chunks have independent PAQ state so that multiple
workers can compress them concurrently.  That loses cross-chunk context and
must never be represented as serial CIX or as a Hutter Prize measurement.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import resource
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path

from benchmarks.competitive_codec import PAQ_BINARIES, paq_binary


MAGIC = b"CIXPARQ1"
VERSION = 1
HEADER = struct.Struct(">8sBBBQQI32s")
ENTRY = struct.Struct(">QQI32s")
COPY = 1024 * 1024
RESERVED_CPUS = frozenset((8, 9))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(COPY), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_limited(source, destination, size: int, digest=None, crc: int = 0) -> tuple[int, int]:
    remaining = size
    while remaining:
        block = source.read(min(COPY, remaining))
        if not block:
            raise ValueError("truncated stream")
        destination.write(block)
        if digest is not None:
            digest.update(block)
        crc = zlib.crc32(block, crc)
        remaining -= len(block)
    return size, crc & 0xffffffff


def _chunk_task(task: dict) -> dict:
    """Copy one source range and run one isolated PAQ process on a pinned CPU."""
    os.sched_setaffinity(0, {task["cpu"]})
    root = Path(task["temporary"])
    root.mkdir(parents=True, exist_ok=False)
    source = root / "source.bin"
    archive = root / "chunk.paq8px"
    digest = hashlib.sha256()
    crc = 0
    with Path(task["input"]).open("rb") as original, source.open("xb") as out:
        original.seek(task["offset"])
        _, crc = _copy_limited(original, out, task["length"], digest, crc)
    command = [task["binary"], task["options"], "-simd", "AVX2", str(source), str(archive)]
    started = time.perf_counter()
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"index": task["index"], "source_bytes": task["length"],
            "source_sha256": digest.hexdigest(), "source_crc32": crc,
            "payload_path": str(archive), "payload_bytes": archive.stat().st_size,
            "seconds": time.perf_counter() - started, "cpu": task["cpu"]}


def _decode_chunk_task(task: dict) -> dict:
    """Recover one independent archive member in an isolated pinned process."""
    os.sched_setaffinity(0, {task["cpu"]})
    root = Path(task["temporary"])
    root.mkdir(parents=True, exist_ok=False)
    payload = root / "chunk.paq8px216"
    decoded = root / "chunk.bin"
    with Path(task["archive"]).open("rb") as archive, payload.open("xb") as out:
        archive.seek(task["payload_offset"])
        _copy_limited(archive, out, task["payload_bytes"])
    with payload.open("rb") as encoded:
        if encoded.read(6) != b"paq8px":
            raise ValueError("invalid PAQ chunk magic")
    started = time.perf_counter()
    # The PAQ archive itself carries its compression level and model flags;
    # unlike encoding, extraction accepts only the -d command.
    subprocess.run([task["binary"], "-d", "-simd", "AVX2",
                    str(payload), str(decoded)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    digest = hashlib.sha256()
    crc = 0
    seen = 0
    with decoded.open("rb") as recovered:
        while block := recovered.read(COPY):
            seen += len(block)
            digest.update(block)
            crc = zlib.crc32(block, crc)
    if seen != task["source_bytes"] or crc & 0xffffffff != task["source_crc32"] or digest.digest() != task["source_sha"]:
        raise ValueError("PAQ chunk checksum mismatch")
    return {"index": task["index"], "decoded_path": str(decoded), "source_bytes": seen,
            "seconds": time.perf_counter() - started, "cpu": task["cpu"]}


def available_cpus() -> tuple[int, ...]:
    return tuple(cpu for cpu in sorted(os.sched_getaffinity(0)) if cpu not in RESERVED_CPUS)


def parse_cpus(value: str | None) -> tuple[int, ...]:
    cpus = available_cpus() if value is None else tuple(int(part) for part in value.split(",") if part)
    allowed = set(os.sched_getaffinity(0))
    if not cpus or len(cpus) != len(set(cpus)):
        raise ValueError("CPUs must be a non-empty unique list")
    if RESERVED_CPUS & set(cpus):
        raise ValueError("CPUs 8 and 9 are reserved for the serial baseline")
    if not set(cpus) <= allowed:
        raise ValueError("requested CPUs are outside caller affinity")
    return cpus


def _chunks(size: int, chunk_bytes: int) -> list[tuple[int, int]]:
    if size < 0 or chunk_bytes < 1:
        raise ValueError("invalid source or chunk size")
    return [(offset, min(chunk_bytes, size - offset)) for offset in range(0, size, chunk_bytes)] or [(0, 0)]


def _option_level(options: str) -> int:
    if len(options) != 2 or options[0] != "-" or options[1] not in "123456789":
        raise ValueError("parallel PAQ format supports exactly one -1 through -9 encoder option")
    return int(options[1])


def encode(source: Path, destination: Path, *, chunk_bytes: int, workers: int,
           cpus: tuple[int, ...], options: str = "-8", temporary: Path | None = None,
           verify: bool = True) -> dict:
    """Encode source without loading it wholesale, then optionally full-decode it."""
    source = Path(source)
    if destination.exists():
        raise FileExistsError(destination)
    if workers < 1 or workers > len(cpus):
        raise ValueError("workers must be positive and no greater than selected CPUs")
    option_level = _option_level(options)
    binary = paq_binary("v216")
    total = source.stat().st_size
    chunks = _chunks(total, chunk_bytes)
    if temporary is not None:
        Path(temporary).mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="cix-parallel-paq-", dir=temporary))
    staged = root / "archive.cixparq"
    started = time.perf_counter()
    try:
        tasks = []
        archive_bytes = source.stat().st_size
        for index, (offset, length) in enumerate(chunks):
            tasks.append({"index": index, "input": str(source), "offset": offset, "length": length,
                          "binary": binary, "options": options, "cpu": cpus[index % workers],
                          "temporary": str(root / ("chunk-%08d" % index))})
        rows: list[dict] = []
        # Submit in waves, rather than handing all work to the executor at once.
        # A long-running first chunk must never share its CPU with a later chunk
        # merely because another worker finished early.
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for start in range(0, len(tasks), workers):
                wave = tasks[start:start + workers]
                futures = []
                for worker_index, task in enumerate(wave):
                    leased = dict(task, cpu=cpus[worker_index])
                    futures.append(pool.submit(_chunk_task, leased))
                for future in futures:
                    rows.append(future.result())
        rows.sort(key=lambda row: row["index"])
        source_sha = _hash_file(source)
        with staged.open("xb") as archive:
            archive.write(HEADER.pack(MAGIC, VERSION, 216, option_level, total, chunk_bytes, len(rows), bytes.fromhex(source_sha)))
            for row in rows:
                payload = Path(row["payload_path"])
                archive.write(ENTRY.pack(row["source_bytes"], row["payload_bytes"], row["source_crc32"],
                                         bytes.fromhex(row["source_sha256"])))
                with payload.open("rb") as encoded:
                    shutil.copyfileobj(encoded, archive, COPY)
        verification = None
        if verify:
            restored = root / "verified-restored.bin"
            verification = decode(staged, restored, workers=workers, cpus=cpus, temporary=root / "decode")
            if verification["output_sha256"] != source_sha or verification["output_bytes"] != total:
                raise ValueError("parallel archive failed complete SHA-256 verification")
        # link gives an exclusive final publication and does not overwrite a late creator.
        os.link(staged, destination)
        return {"policy": "cix-parallel-independent-paq-v216", "operation": "encode",
                "parallel_profile": True, "not_serial_cix": True, "not_hutter_qualified": True,
                "source_bytes": total, "output_bytes": destination.stat().st_size,
                "source_sha256": source_sha, "output_sha256": _hash_file(destination),
                "chunk_bytes": chunk_bytes, "chunks": len(rows), "workers": workers, "cpus": list(cpus[:workers]),
                "paq_version": "v216", "paq_options": options,
                "paq_binary_sha256": PAQ_BINARIES["v216"], "seconds": time.perf_counter() - started,
                "chunk_seconds": [row["seconds"] for row in rows], "round_trip": bool(verify),
                "verification": verification, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _read_header(stream) -> tuple[int, int, int, int, str]:
    raw = stream.read(HEADER.size)
    if len(raw) != HEADER.size:
        raise ValueError("truncated parallel PAQ header")
    magic, version, paq_version, option_level, original_bytes, chunk_bytes, count, original_sha = HEADER.unpack(raw)
    if magic != MAGIC or version != VERSION or paq_version != 216:
        raise ValueError("unsupported parallel PAQ format")
    if not count or not chunk_bytes or option_level > 9:
        raise ValueError("invalid parallel PAQ header")
    return original_bytes, chunk_bytes, count, option_level, original_sha.hex()


def decode(source: Path, destination: Path, *, workers: int = 1, cpus: tuple[int, ...] | None = None,
           temporary: Path | None = None) -> dict:
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if temporary is not None:
        Path(temporary).mkdir(parents=True, exist_ok=True)
    cpus = parse_cpus(None) if cpus is None else tuple(cpus)
    if workers < 1 or workers > len(cpus):
        raise ValueError("workers must be positive and no greater than selected CPUs")
    root = Path(tempfile.mkdtemp(prefix="cix-parallel-paq-decode-", dir=temporary))
    started = time.perf_counter()
    try:
        binary = paq_binary("v216")
        tasks = []
        archive_bytes = source.stat().st_size
        total_declared = 0
        with source.open("rb") as archive:
            original_bytes, _chunk_bytes, count, option_level, expected_sha = _read_header(archive)
            for index in range(count):
                raw = archive.read(ENTRY.size)
                if len(raw) != ENTRY.size:
                    raise ValueError("truncated parallel PAQ chunk table")
                source_bytes, payload_bytes, expected_crc, expected_chunk_sha = ENTRY.unpack(raw)
                if source_bytes > original_bytes - total_declared or payload_bytes < 9:
                    raise ValueError("invalid parallel PAQ chunk lengths")
                payload_offset = archive.tell()
                if payload_offset + payload_bytes > archive_bytes:
                    raise ValueError("truncated parallel PAQ payload")
                archive.seek(payload_bytes, 1)
                total_declared += source_bytes
                tasks.append({"index": index, "archive": str(source), "payload_offset": payload_offset,
                              "payload_bytes": payload_bytes, "source_bytes": source_bytes,
                              "source_crc32": expected_crc, "source_sha": expected_chunk_sha,
                              "binary": binary, "option_level": option_level,
                              "temporary": str(root / ("chunk-%08d" % index))})
            if archive.read(1):
                raise ValueError("trailing parallel PAQ bytes")
        if total_declared != original_bytes:
            raise ValueError("parallel PAQ declared length mismatch")
        rows = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            for start_index in range(0, len(tasks), workers):
                futures = [pool.submit(_decode_chunk_task, dict(task, cpu=cpus[worker_index]))
                           for worker_index, task in enumerate(tasks[start_index:start_index + workers])]
                rows.extend(future.result() for future in futures)
        rows.sort(key=lambda row: row["index"])
        total_written = 0
        output_hash = hashlib.sha256()
        staged_restored = root / "restored.bin"
        with staged_restored.open("xb") as restored:
            for row in rows:
                with Path(row["decoded_path"]).open("rb") as recovered:
                    while block := recovered.read(COPY):
                        restored.write(block)
                        output_hash.update(block)
                        total_written += len(block)
        actual_sha = output_hash.hexdigest()
        if total_written != original_bytes or actual_sha != expected_sha:
            raise ValueError("parallel PAQ whole-stream SHA-256 mismatch")
        # Publish only a verified restoration. link() is exclusive and never
        # overwrites a destination another process created while we decoded.
        os.link(staged_restored, destination)
        return {"policy": "cix-parallel-independent-paq-v216", "operation": "decode",
                "source_bytes": source.stat().st_size, "output_bytes": total_written,
                "source_sha256": _hash_file(source), "output_sha256": actual_sha,
                "chunks": count, "workers": workers, "cpus": list(cpus[:workers]), "round_trip": True, "seconds": time.perf_counter() - started,
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--chunk-mib", type=int, default=32)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cpus", help="comma-separated CPUs; default excludes 8,9")
    parser.add_argument("--options", default="-8", help="PAQ encoder option, e.g. --options=-8")
    parser.add_argument("--temporary", type=Path)
    parser.add_argument("--no-verify", action="store_true", help="skip encode's full independent decode")
    args = parser.parse_args()
    if args.chunk_mib < 1:
        parser.error("--chunk-mib must be positive")
    if args.operation == "encode":
        result = encode(args.source, args.destination, chunk_bytes=args.chunk_mib * 1024 * 1024,
                        workers=args.workers, cpus=parse_cpus(args.cpus), options=args.options,
                        temporary=args.temporary, verify=not args.no_verify)
    else:
        result = decode(args.source, args.destination, workers=args.workers, cpus=parse_cpus(args.cpus), temporary=args.temporary)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
