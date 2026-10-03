#!/usr/bin/env python3
"""Private T1 archive-parity probe for a frozen CIXM6 idle-flush stream.

This compares archive bytes, not speed.  It writes two known 256-byte chunks
to an open stdin pipe, waits by parser-observed output for the first complete
CIXM6 frame before the second write and EOF, then requires the before/after
archives to have exactly the same SHA-256.  No fixed delay is used as proof of
flushing; the 5-second deadline only bounds a missing output event.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import subprocess
import sys
import time
from pathlib import Path


FRAME_WAIT_SECONDS = 5.0


def read_varint(buffer: bytes, position: int) -> tuple[int, int] | None:
    value = 0
    shift = 0
    for _ in range(10):
        if position >= len(buffer):
            return None
        byte = buffer[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7
    raise RuntimeError("oversized CIXM6 varint in live output")


def first_complete_m6_frame_end(buffer: bytes) -> tuple[int, int] | None:
    if len(buffer) < 5:
        return None
    if buffer[:5] != b"CIXM6":
        raise RuntimeError("live output is not a CIXM6 stream")
    history = read_varint(buffer, 5)
    if history is None:
        return None
    _, position = history
    if position >= len(buffer):
        return None
    mode = buffer[position]
    if mode == 255:
        raise RuntimeError("CIXM6 footer arrived before a data frame")
    position += 1
    source = read_varint(buffer, position)
    if source is None:
        return None
    source_bytes, position = source
    payload = read_varint(buffer, position)
    if payload is None:
        return None
    payload_bytes, position = payload
    end = position + payload_bytes
    return (end, source_bytes) if len(buffer) >= end else None


def require_executable(value: str, label: str) -> str:
    path = Path(value).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise RuntimeError(f"{label} is not an executable file: {path}")
    return str(path)


def encode_two_writes(binary: str, first: bytes, second: bytes) -> tuple[bytes, dict[str, int]]:
    command = [
        binary, "--format", "cixm6", "--fast", "--threads", "1", "--block-size", "4096",
        "--memory", "16MiB", "--flush-interval", "50ms", "-c", "-",
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    process.stdin.write(first)
    process.stdin.flush()
    os.set_blocking(process.stdout.fileno(), False)
    os.set_blocking(process.stderr.fileno(), False)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    archive = bytearray()
    stderr = bytearray()
    deadline = time.monotonic() + FRAME_WAIT_SECONDS
    frame = None
    while time.monotonic() < deadline:
        ready = selector.select(timeout=max(0.0, deadline - time.monotonic()))
        for key, _ in ready:
            chunk = os.read(key.fd, 65536)
            if not chunk:
                selector.unregister(key.fileobj)
            elif key.data == "stdout":
                archive.extend(chunk)
            else:
                stderr.extend(chunk)
        frame = first_complete_m6_frame_end(bytes(archive))
        if frame is not None:
            break
    if frame is None:
        process.kill()
        process.wait()
        raise RuntimeError(f"no complete CIXM6 data frame before second write: {stderr.decode(errors='replace')}")
    frame_end, first_frame_source_bytes = frame
    if first_frame_source_bytes != len(first):
        process.kill()
        process.wait()
        raise RuntimeError(f"first CIXM6 frame contains {first_frame_source_bytes} bytes, expected {len(first)}")

    process.stdin.write(second)
    process.stdin.close()
    completion_deadline = time.monotonic() + FRAME_WAIT_SECONDS
    while selector.get_map():
        remaining = completion_deadline - time.monotonic()
        if remaining <= 0:
            process.kill()
            process.wait()
            raise RuntimeError("CIXM6 encoder did not close output after second write")
        for key, _ in selector.select(timeout=remaining):
            chunk = os.read(key.fd, 65536)
            if not chunk:
                selector.unregister(key.fileobj)
            elif key.data == "stdout":
                archive.extend(chunk)
            else:
                stderr.extend(chunk)
    status = process.wait(timeout=FRAME_WAIT_SECONDS)
    if status != 0:
        raise RuntimeError(f"CIXM6 encode failed ({status}): {stderr.decode(errors='replace')}")
    return bytes(archive), {"first_frame_end": frame_end, "first_frame_source_bytes": first_frame_source_bytes}


def decode_exact(binary: str, archive: bytes, expected: bytes) -> None:
    result = subprocess.run([binary, "-c", "-"], input=archive, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0 or result.stdout != expected:
        raise RuntimeError(f"fresh candidate decode failed: {result.stderr.decode(errors='replace')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-cix", required=True)
    parser.add_argument("--after-cix", required=True)
    parser.add_argument("--after-uncix", required=True, help="selected candidate uncix for fresh decoding")
    parser.add_argument("--work-dir", required=True, type=Path)
    args = parser.parse_args()
    before_cix = require_executable(args.before_cix, "before cix")
    after_cix = require_executable(args.after_cix, "after cix")
    after_uncix = require_executable(args.after_uncix, "after uncix")
    work = args.work_dir.resolve()
    if work.exists():
        raise RuntimeError(f"work directory already exists; refusing to overwrite evidence: {work}")
    work.mkdir(parents=True)

    first = bytes((index * 37 + 11) & 0xFF for index in range(256))
    second = bytes((index * 53 + 7) & 0xFF for index in range(256))
    source = first + second
    before, before_frame = encode_two_writes(before_cix, first, second)
    after, after_frame = encode_two_writes(after_cix, first, second)
    if hashlib.sha256(before).digest() != hashlib.sha256(after).digest():
        raise RuntimeError("before and after CIXM6 archives differ; T1 archive parity failed")
    decode_exact(after_uncix, before, source)
    decode_exact(after_uncix, after, source)
    evidence = {
        "purpose": "T1 CIXM6 archive-parity and pre-EOF frame check; not a speed result",
        "command_shape": "--format cixm6 --fast --threads 1 --block-size 4096 --memory 16MiB --flush-interval 50ms -c -",
        "source": {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest(), "writes": [len(first), len(second)]},
        "before": {"cix": before_cix, "archive_bytes": len(before), "archive_sha256": hashlib.sha256(before).hexdigest(), "first_complete_frame": before_frame},
        "after": {"cix": after_cix, "uncix": after_uncix, "archive_bytes": len(after), "archive_sha256": hashlib.sha256(after).hexdigest(), "first_complete_frame": after_frame, "fresh_exact_decode": True},
        "archive_parity": True,
    }
    path = work / "evidence.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "evidence": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as error:
        print(f"T1 parity test failed: {error}", file=sys.stderr)
        raise SystemExit(1)
