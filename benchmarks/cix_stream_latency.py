#!/usr/bin/env python3
"""Local CIX streaming-correctness and latency harness.

This is deliberately not a compression benchmark.  It drives real pipes,
holds the producer open after a 2 KiB prefix, and records whether a complete
frame and reconstructed bytes became observable before EOF.  It uses no
Python encoder or decoder.  The caller supplies a pre-frozen source slice and
explicit archive/evidence destinations; this script never acquires data or
dispatches work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import BinaryIO


SOURCE_LIMIT = 1 << 20
PREFIX = 2048
FIRST_SEND = 64 << 10
IDLE_SECONDS = 0.100
EVENT_TIMEOUT = 15.0
COMPLETE_TIMEOUT = 60.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def host_identity() -> dict[str, object]:
    cpu_model = None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model,
        "logical_cpus": os.cpu_count(),
    }


def git_revision(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def read_exact_source(path: Path) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(SOURCE_LIMIT + 1)
    if len(data) != SOURCE_LIMIT:
        raise RuntimeError(
            f"frozen latency source must be exactly {SOURCE_LIMIT} bytes, got {len(data)}"
        )
    return data


def complete_first_frame(buffer: bytearray) -> bool:
    # CIXG frame: 5-byte magic, 8-byte stream header, then route, source
    # length, payload length, SHA-256 and payload.  This recognizes only a
    # complete first frame; pipe reads may split every one of those fields.
    if len(buffer) < 22 or bytes(buffer[:5]) not in (b"CIXG1", b"CIXG2"):
        return False
    payload = int.from_bytes(buffer[18:22], "little")
    return len(buffer) >= 54 + payload


def write_irregular(stream: BinaryIO, data: bytes) -> None:
    chunks = (1, 19, 3, 241, 17, 1021, 11, 509, 4093)
    offset = 0
    index = 0
    while offset < len(data):
        end = min(offset + chunks[index % len(chunks)], len(data))
        stream.write(data[offset:end])
        stream.flush()
        offset = end
        index += 1


@dataclass
class TransferResult:
    archive_bytes: int
    archive_sha256: str
    first_frame_seconds: float | None


def wait_process(process: subprocess.Popen[bytes], label: str, timeout: float) -> int:
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        process.kill()
        process.wait()
        raise RuntimeError(f"{label} did not exit within {timeout}s") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="frozen 1 MiB input slice")
    parser.add_argument("--archive", type=Path, required=True, help="new archive artifact path")
    parser.add_argument("--evidence", type=Path, required=True, help="new JSON evidence path")
    parser.add_argument("--cix", type=Path, required=True, help="frozen release cix binary")
    parser.add_argument("--uncix", type=Path, required=True, help="frozen release uncix binary")
    args = parser.parse_args()

    source = read_exact_source(args.source)
    for path, label in ((args.cix, "cix"), (args.uncix, "uncix")):
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"{label} is not an executable file: {path}")
    for path in (args.archive, args.evidence):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    cix_cmd = [
        str(args.cix),
        "--stream",
        "--fast",
        "--threads",
        "2",
        "--parallelism",
        "blocks",
        "--block-size",
        "64KiB",
        "--flush-interval",
        "100ms",
        "--memory",
        "16MiB",
        "-c",
        "-",
    ]
    uncix_cmd = [str(args.uncix), "--stream", "-c", "-"]
    cix = subprocess.Popen(cix_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    uncix = subprocess.Popen(uncix_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert cix.stdin and cix.stdout and cix.stderr
    assert uncix.stdin and uncix.stdout and uncix.stderr

    events: Queue[tuple[str, float]] = Queue()
    transfer_error: list[BaseException] = []
    decoded_error: list[BaseException] = []
    restored = bytearray()
    started = time.monotonic()

    def transfer() -> None:
        digest = hashlib.sha256()
        first_frame_buffer = bytearray()
        first_frame_seconds: float | None = None
        archive_bytes = 0
        try:
            with args.archive.open("xb") as archive:
                while True:
                    # `read1` returns bytes currently available from the OS
                    # pipe; `read(4096)` is allowed to wait for a full buffer
                    # and would hide the very latency this harness records.
                    chunk = cix.stdout.read1(4096)
                    if not chunk:
                        break
                    archive.write(chunk)
                    archive.flush()
                    digest.update(chunk)
                    archive_bytes += len(chunk)
                    if first_frame_seconds is None:
                        first_frame_buffer.extend(chunk)
                        if complete_first_frame(first_frame_buffer):
                            first_frame_seconds = time.monotonic() - started
                            events.put(("frame", first_frame_seconds))
                    uncix.stdin.write(chunk)
                    uncix.stdin.flush()
            uncix.stdin.close()
            events.put(("transfer_done", 0.0))
            transfer.result = TransferResult(archive_bytes, digest.hexdigest(), first_frame_seconds)
        except BaseException as error:  # relay thread failures to the parent
            transfer_error.append(error)
            try:
                uncix.stdin.close()
            except OSError:
                pass

    transfer.result = None  # type: ignore[attr-defined]

    def collect_decoder() -> None:
        try:
            first = True
            while True:
                chunk = uncix.stdout.read1(4096)
                if not chunk:
                    break
                if first:
                    first = False
                    events.put(("decoded", time.monotonic() - started))
                restored.extend(chunk)
        except BaseException as error:
            decoded_error.append(error)

    transfer_thread = threading.Thread(target=transfer, name="cix-archive-forwarder")
    decoder_thread = threading.Thread(target=collect_decoder, name="uncix-output-reader")
    transfer_thread.start()
    decoder_thread.start()

    try:
        cix.stdin.write(source[:PREFIX])
        cix.stdin.flush()
        seen: dict[str, float] = {}
        deadline = time.monotonic() + EVENT_TIMEOUT
        while {"frame", "decoded"} - seen.keys():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("complete frame and decoded bytes were not both available before EOF")
            try:
                kind, seconds = events.get(timeout=remaining)
            except Empty as error:
                raise RuntimeError("stream availability event timed out") from error
            if kind in ("frame", "decoded"):
                seen[kind] = seconds
        # Complete the promised initial 64 KiB, keep the producer open through
        # an idle interval, then feed the remainder in irregular chunks.
        first_end = min(FIRST_SEND, len(source))
        write_irregular(cix.stdin, source[PREFIX:first_end])
        time.sleep(IDLE_SECONDS)
        write_irregular(cix.stdin, source[first_end:])
        cix.stdin.close()
        cix_status = wait_process(cix, "cix", COMPLETE_TIMEOUT)
        transfer_thread.join(COMPLETE_TIMEOUT)
        decoder_thread.join(COMPLETE_TIMEOUT)
        if transfer_thread.is_alive() or decoder_thread.is_alive():
            raise RuntimeError("stream relay did not terminate")
        uncix_status = wait_process(uncix, "uncix", COMPLETE_TIMEOUT)
    except BaseException:
        for process in (cix, uncix):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        raise

    cix_stderr = cix.stderr.read().decode("utf-8", "replace")
    uncix_stderr = uncix.stderr.read().decode("utf-8", "replace")
    if cix_status != 0:
        raise RuntimeError(f"cix failed ({cix_status}): {cix_stderr}")
    if uncix_status != 0:
        raise RuntimeError(f"uncix failed ({uncix_status}): {uncix_stderr}")
    if transfer_error:
        raise RuntimeError(f"archive forwarder failed: {transfer_error[0]}")
    if decoded_error:
        raise RuntimeError(f"decoder output reader failed: {decoded_error[0]}")
    result: TransferResult | None = transfer.result  # type: ignore[attr-defined]
    if result is None or result.first_frame_seconds is None:
        raise RuntimeError("archive ended without a complete first frame")
    if bytes(restored) != source:
        raise RuntimeError("fresh uncix process did not restore the frozen source exactly")
    if "frame" not in seen or "decoded" not in seen:
        raise RuntimeError("missing pre-EOF stream events")

    root = Path(__file__).resolve().parents[1]
    evidence = {
        "kind": "local_streaming_correctness_latency",
        "not_a_cpu_qualification_or_rank": True,
        "input": {
            "path": str(args.source),
            "bytes": len(source),
            "sha256": hashlib.sha256(source).hexdigest(),
        },
        "binaries": {
            "cix": {"path": str(args.cix), "sha256": sha256_file(args.cix)},
            "uncix": {"path": str(args.uncix), "sha256": sha256_file(args.uncix)},
            "source_revision": git_revision(root),
        },
        "commands": {"cix": cix_cmd, "uncix": uncix_cmd},
        "stream": {
            "prefix_before_idle_bytes": PREFIX,
            "first_send_bytes": FIRST_SEND,
            "idle_flush_seconds": IDLE_SECONDS,
            "first_complete_frame_wall_seconds": seen["frame"],
            "first_decoded_bytes_wall_seconds": seen["decoded"],
            "both_observed_before_input_eof": True,
        },
        "archive": {"bytes": result.archive_bytes, "sha256": result.archive_sha256},
        "verification": {
            "restored_sha256": hashlib.sha256(restored).hexdigest(),
            "exact_restore": True,
            "fresh_decoder_process": True,
        },
        "environment": host_identity(),
    }
    with args.evidence.open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
