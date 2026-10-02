#!/usr/bin/env python3
"""Bounded local receipts for native CIXG1 pipe streaming.

This focused correctness/latency probe is not an isolated-host corpus
qualification or compression ranking.  It creates a deterministic 64 KiB
input locally, attaches the frozen cix and uncix binaries with real anonymous
pipes, and produces an evidence JSON only after every check completes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import platform
import resource
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


FIRST = 32_768
TOTAL = 65_536
IDLE_SECONDS = 1.0
PROBE_SECONDS = 0.450
CASE_TIMEOUT_SECONDS = 30.0
RELAY_LIMIT = 65_536
TEMP_LIMIT = 32 << 20
MEMORY_LIMIT = 128 << 20
CPU = 16
CIX = Path("/tmp/cix-main-decode-candidate-target/release/cix")
UNCIX = Path("/tmp/cix-main-decode-candidate-target/release/uncix")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolved_libraries(binary: Path) -> list[Path]:
    """Return absolute DSOs resolved by the current loader, sorted uniquely."""
    output = subprocess.check_output(["ldd", str(binary)], text=True, stderr=subprocess.STDOUT)
    paths: set[Path] = set()
    for line in output.splitlines():
        for token in line.replace("=>", " ").split():
            candidate = Path(token)
            if candidate.is_absolute() and candidate.is_file():
                paths.add(candidate.resolve())
    return sorted(paths)


def binary_identity(binary: Path) -> dict[str, Any]:
    libs = resolved_libraries(binary)
    return {
        "path": str(binary),
        "sha256": sha256_file(binary),
        "resolved_shared_libraries": [
            {"path": str(path), "sha256": sha256_file(path)} for path in libs
        ],
    }


def deterministic_input() -> bytes:
    parts: list[bytes] = []
    counter = 0
    while sum(map(len, parts)) < TOTAL:
        parts.append(hashlib.sha256(f"cix-stream-latency-probe-v1:{counter}".encode()).digest())
        counter += 1
    return b"".join(parts)[:TOTAL]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def preexec() -> None:
    os.sched_setaffinity(0, {CPU})
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_FSIZE, (TEMP_LIMIT, TEMP_LIMIT))


def set_nonblocking(stream: Any) -> int:
    assert stream is not None
    fd = stream.fileno()
    os.set_blocking(fd, False)
    return fd


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def close_stream(stream: Any) -> None:
    if stream is not None and not stream.closed:
        try:
            stream.close()
        except OSError:
            pass


def pipe_size(fd: int) -> int | None:
    try:
        return fcntl.fcntl(fd, fcntl.F_GETPIPE_SZ)
    except OSError:
        return None


def set_pipe_size(fd: int, size: int) -> int | None:
    try:
        return fcntl.fcntl(fd, fcntl.F_SETPIPE_SZ, size)
    except OSError:
        return None


def process_rejection(archive: bytes, label: str) -> dict[str, Any]:
    command = [str(UNCIX), "--stream", "-c", "-"]
    completed = subprocess.run(command, input=archive, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=10, preexec_fn=preexec)
    return {
        "case": label,
        "command": command,
        "input_bytes": len(archive),
        "exit_code": completed.returncode,
        "rejected": completed.returncode != 0,
        "stdout_bytes": len(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
    }


def run_case(source: bytes, slow_consumer: bool) -> tuple[dict[str, Any], bytes]:
    cix_command = [str(CIX), "--fast", "--stream", "--format", "cixg1", "--block-size",
                   "64KiB", "--flush-interval", "100ms", "--threads", "1", "--memory",
                   "32MiB", "-c", "-"]
    uncix_command = [str(UNCIX), "--stream", "-c", "-"]
    cix = subprocess.Popen(cix_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, preexec_fn=preexec)
    try:
        uncix = subprocess.Popen(uncix_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, preexec_fn=preexec)
    except BaseException:
        terminate(cix)
        for stream in (cix.stdin, cix.stdout, cix.stderr):
            close_stream(stream)
        raise
    assert cix.stdin and cix.stdout and cix.stderr and uncix.stdin and uncix.stdout and uncix.stderr
    in_fd, cix_out, uncix_in, uncix_out = (set_nonblocking(cix.stdin), set_nonblocking(cix.stdout),
                                           set_nonblocking(uncix.stdin), set_nonblocking(uncix.stdout))
    # A small kernel pipe makes the slow-consumer case demonstrate bounded
    # backpressure instead of hiding a whole archive in a default-sized pipe.
    initial_pipe = pipe_size(cix_out)
    constrained_pipe = set_pipe_size(cix_out, 4096) if slow_consumer else initial_pipe
    pending_input = bytearray(source[:FIRST])
    pending_relay = bytearray()
    archive = bytearray()
    decoded = bytearray()
    cix_input_closed = False
    cix_stdout_eof = False
    uncix_stdout_eof = False
    input_eof_at: float | None = None
    first_output_at: float | None = None
    first_decoded_at: float | None = None
    probe: dict[str, Any] | None = None
    start_utc = utc_now()
    start = time.monotonic()
    phase_two_at = start + IDLE_SECONDS
    second_segment_queued = False
    # The slow case deliberately stops consuming cix stdout for 700 ms.  The
    # relay remains capped and then resumes through the real decoder pipe.
    pause_until = start + 0.700 if slow_consumer else start
    try:
        while True:
            now = time.monotonic()
            elapsed = now - start
            if elapsed > CASE_TIMEOUT_SECONDS:
                raise RuntimeError("case timeout exceeded 30 seconds")
            if (not second_segment_queued and now >= phase_two_at and not cix_input_closed):
                pending_input.extend(source[FIRST:])
                second_segment_queued = True
            if (second_segment_queued and not cix_input_closed and not pending_input):
                close_stream(cix.stdin)
                cix_input_closed = True
                input_eof_at = time.monotonic() - start
            if probe is None and elapsed >= PROBE_SECONDS:
                probe = {
                    "at_seconds": elapsed,
                    "cix_alive": cix.poll() is None,
                    "uncix_alive": uncix.poll() is None,
                    "compressed_bytes_before_eof": len(archive),
                    "decoded_bytes_before_eof": len(decoded),
                    "input_eof_sent": cix_input_closed,
                }
                if not (probe["cix_alive"] and probe["uncix_alive"]):
                    raise RuntimeError("cix and uncix must remain alive at the 450 ms probe")
            read_fds = [uncix_out]
            if not cix_stdout_eof and now >= pause_until and len(pending_relay) < RELAY_LIMIT:
                read_fds.append(cix_out)
            write_fds: list[int] = []
            if pending_input and not cix_input_closed:
                write_fds.append(in_fd)
            if pending_relay and uncix_in >= 0:
                write_fds.append(uncix_in)
            readable, writable, _ = select.select(read_fds, write_fds, [], 0.020)
            if in_fd in writable:
                sent = os.write(in_fd, pending_input)
                del pending_input[:sent]
            if cix_out in readable:
                chunk = os.read(cix_out, min(4096, RELAY_LIMIT - len(pending_relay)))
                if chunk:
                    archive.extend(chunk)
                    pending_relay.extend(chunk)
                    if first_output_at is None:
                        first_output_at = time.monotonic() - start
                else:
                    cix_stdout_eof = True
            if uncix_in in writable and pending_relay:
                sent = os.write(uncix_in, pending_relay)
                del pending_relay[:sent]
            if len(archive) > TEMP_LIMIT or len(decoded) > TEMP_LIMIT:
                raise RuntimeError("local temporary aggregate cap exceeded")
            # A terminated encoder can still have a final archive tail in its
            # kernel stdout pipe.  Relay through observed EOF before closing
            # the decoder input.
            if cix_stdout_eof and not pending_relay and uncix_in >= 0:
                close_stream(uncix.stdin)
                uncix_in = -1
            if uncix_out in readable:
                chunk = os.read(uncix_out, 4096)
                if chunk:
                    decoded.extend(chunk)
                    if first_decoded_at is None:
                        first_decoded_at = time.monotonic() - start
                else:
                    uncix_stdout_eof = True
            if (cix_stdout_eof and uncix_stdout_eof and cix.poll() is not None
                    and uncix.poll() is not None):
                break
        if probe is None:
            raise RuntimeError("450 ms liveness probe was not reached")
        if cix.returncode != 0 or uncix.returncode != 0:
            raise RuntimeError(f"stream process exit: cix={cix.returncode}, uncix={uncix.returncode}")
        if bytes(decoded) != source:
            raise RuntimeError("uncix did not restore deterministic source exactly")
        if (first_output_at is None or first_decoded_at is None or input_eof_at is None
                or first_output_at >= input_eof_at or first_decoded_at >= input_eof_at):
            raise RuntimeError("compressed and decoded bytes must be observed before input EOF")
        return ({
            "case": "slow_consumer_backpressure" if slow_consumer else "idle_open_pipe",
            "commands": {"cix": cix_command, "uncix": uncix_command},
            "start_utc": start_utc,
            "duration_seconds": time.monotonic() - start,
            "pipe": {"cix_stdout_initial_bytes": initial_pipe,
                     "cix_stdout_constrained_bytes": constrained_pipe if slow_consumer else None,
                     "relay_limit_bytes": RELAY_LIMIT, "consumer_pause_seconds": 0.700 if slow_consumer else 0},
            "probe_450ms": probe,
            "pre_eof": {"first_compressed_seconds": first_output_at,
                        "first_decoded_seconds": first_decoded_at,
                        "input_eof_seconds": input_eof_at},
            "exit_codes": {"cix": cix.returncode, "uncix": uncix.returncode},
            "archive": {"bytes": len(archive), "sha256": sha256_bytes(bytes(archive))},
            "restore": {"bytes": len(decoded), "sha256": sha256_bytes(bytes(decoded)), "exact": True},
        }, bytes(archive))
    finally:
        terminate(cix)
        terminate(uncix)
        for process in (cix, uncix):
            for stream in (process.stdin, process.stdout, process.stderr):
                close_stream(stream)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True,
                        help="new receipt JSON; refuses to overwrite")
    parser.add_argument("--repetitions", type=int, default=3,
                        help="number of normal and slow-consumer runs (default: 3)")
    args = parser.parse_args()
    if args.receipt.exists():
        raise SystemExit(f"refusing to overwrite receipt: {args.receipt}")
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be positive")
    if not CIX.is_file() or not UNCIX.is_file():
        raise SystemExit("frozen cix/uncix binaries are unavailable")
    source = deterministic_input()
    pre = {"cix": binary_identity(CIX), "uncix": binary_identity(UNCIX)}
    receipt: dict[str, Any] = {
        "kind": "cixg1_native_bounded_stream_latency_receipt",
        "scope": "focused local correctness and latency evidence; not isolated-host corpus qualification",
        "created_utc": utc_now(),
        "resources": {
            "cpu_affinity": [CPU],
            "per_child_virtual_address_rlimit_bytes": MEMORY_LIMIT,
            "aggregate_rss": "unverified by this local probe",
            "temporary_aggregate_cap_bytes": TEMP_LIMIT,
            "swap": "unverified; this probe is not a no-swap qualification",
        },
        "input": {"construction": "sha256(cix-stream-latency-probe-v1:<counter>) concatenation",
                  "bytes": len(source), "sha256": sha256_bytes(source),
                  "segments": [FIRST, TOTAL - FIRST], "idle_open_seconds": IDLE_SECONDS},
        "binaries_before": pre,
        "repetitions_per_case": args.repetitions,
        "cases": [],
    }
    with tempfile.TemporaryDirectory(prefix="cix-stream-latency-") as temporary:
        # The directory is deliberately local and bounded by the receipt's
        # observed artifacts; no corpus inputs or archives are retained.
        if shutil.disk_usage(temporary).free < TEMP_LIMIT:
            raise RuntimeError("insufficient local temporary capacity")
        archive = b""
        for repetition in range(1, args.repetitions + 1):
            normal, archive = run_case(source, slow_consumer=False)
            normal["repetition"] = repetition
            receipt["cases"].append(normal)
            slow, _ = run_case(source, slow_consumer=True)
            slow["repetition"] = repetition
            receipt["cases"].append(slow)
        receipt["rejection_after_eof"] = [
            process_rejection(archive[:-1], "truncated_last_byte"),
            process_rejection(archive[:100] + bytes([archive[100] ^ 1]) + archive[101:],
                              "corrupt_first_frame_payload_byte"),
        ]
        if not all(item["rejected"] for item in receipt["rejection_after_eof"]):
            raise RuntimeError("truncated or corrupt archive was accepted")
    post = {"cix": binary_identity(CIX), "uncix": binary_identity(UNCIX)}
    receipt["binaries_after"] = post
    receipt["binary_identities_unchanged"] = pre == post
    if not receipt["binary_identities_unchanged"]:
        raise RuntimeError("frozen binary or resolved shared library changed during probe")
    receipt["status"] = "VERIFIED"
    receipt["host"] = {"platform": platform.platform(), "python": sys.version, "logical_cpus": os.cpu_count()}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"receipt": str(args.receipt), "status": receipt["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
