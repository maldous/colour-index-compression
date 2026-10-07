#!/usr/bin/env python3
"""Native raw-route pipe proof with source bytes larger than the cgroup cap."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time

from benchmarks.cix_stream_latency_probe import binary_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--encoder-memory", default="16MiB")
    args = parser.parse_args()
    total, chunk_size, relay_limit = 256 << 20, 65536, 65536
    cpu = sorted(os.sched_getaffinity(0))
    cg_path = next(x.split(":", 2)[2] for x in Path("/proc/self/cgroup").read_text().splitlines() if x.startswith("0::"))
    cg = Path("/sys/fs/cgroup" + cg_path)
    guard = {k: (cg / k).read_text().strip() for k in ("memory.max", "memory.swap.max")}
    assert guard == {"memory.max": str(64 << 20), "memory.swap.max": "0"}, guard
    assert cpu == [8], cpu
    cix, uncix = args.release.resolve() / "cix", args.release.resolve() / "uncix"
    identities = {"cix": binary_identity(cix), "uncix": binary_identity(uncix)}
    commands = [
        [str(cix), "--stream", "--fast", "--route", "raw", "--threads", "2", "--memory", args.encoder_memory, "--block-size", "64KiB", "-c", "-"],
        [str(uncix), "--stream", "--memory", "4MiB", "-c", "-"],
    ]
    source_hash, restored_hash, archive_hash = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    # The generator retains exactly one block. No source/archive/output spool.
    block = bytes(range(256)) * 256
    produced = restored = archive_bytes = offset = relay_peak = 0
    relay = bytearray()
    encoder_eof = False
    first_archive = first_restored = None
    started = time.monotonic()
    processes = []
    with tempfile.TemporaryDirectory(prefix="cix-large-pipe-diagnostics-") as tmp:
        with open(Path(tmp) / "encode.stderr", "wb+") as encerr, open(Path(tmp) / "decode.stderr", "wb+") as decerr:
            try:
                enc = subprocess.Popen(commands[0], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=encerr)
                processes.append(enc)
                dec = subprocess.Popen(commands[1], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=decerr)
                processes.append(dec)
                assert enc.stdin and enc.stdout and dec.stdin and dec.stdout
                streams = [enc.stdin, enc.stdout, dec.stdin, dec.stdout]
                for stream in streams:
                    os.set_blocking(stream.fileno(), False)
                child_cgroups = {}
                for proc in processes:
                    child_cgroups[str(proc.pid)] = Path(f"/proc/{proc.pid}/cgroup").read_text()
                    assert f"0::{cg_path}\n" in child_cgroups[str(proc.pid)]
                sent_before_consumer_release = None
                native_rss_peak = {str(proc.pid): 0 for proc in processes}
                while not dec.stdout.closed:
                    elapsed = time.monotonic() - started
                    if elapsed > 60:
                        raise TimeoutError("large pipe exceeded declared 60 s budget")
                    for proc in processes:
                        try:
                            for line in Path(f"/proc/{proc.pid}/status").read_text().splitlines():
                                if line.startswith("VmRSS:"):
                                    native_rss_peak[str(proc.pid)] = max(native_rss_peak[str(proc.pid)], int(line.split()[1]) * 1024)
                        except FileNotFoundError:
                            pass
                    # Hold downstream reads initially to exercise backpressure.
                    if elapsed >= 0.3 and sent_before_consumer_release is None:
                        sent_before_consumer_release = produced
                    reads = []
                    if not encoder_eof and len(relay) < relay_limit:
                        reads.append(enc.stdout)
                    if elapsed >= 0.3:
                        reads.append(dec.stdout)
                    writes = []
                    if produced < total:
                        writes.append(enc.stdin)
                    if relay:
                        writes.append(dec.stdin)
                    ready_read, ready_write, _ = select.select(reads, writes, [], 0.01)
                    for stream in ready_write:
                        if stream is enc.stdin:
                            n = os.write(stream.fileno(), memoryview(block)[offset:])
                            source_hash.update(memoryview(block)[offset:offset + n])
                            produced += n
                            offset = (offset + n) % chunk_size
                            if produced == total:
                                enc.stdin.close()
                        else:
                            n = os.write(stream.fileno(), relay)
                            del relay[:n]
                    for stream in ready_read:
                        nmax = relay_limit - len(relay) if stream is enc.stdout else chunk_size
                        data = os.read(stream.fileno(), nmax)
                        if stream is enc.stdout:
                            if data:
                                if first_archive is None:
                                    first_archive = time.monotonic() - started
                                archive_hash.update(data)
                                archive_bytes += len(data)
                                relay.extend(data)
                                relay_peak = max(relay_peak, len(relay))
                            else:
                                encoder_eof = True
                        elif data:
                            if first_restored is None:
                                first_restored = time.monotonic() - started
                            restored_hash.update(data)
                            restored += len(data)
                        else:
                            dec.stdout.close()
                    if encoder_eof and not relay and not dec.stdin.closed:
                        dec.stdin.close()
                exit_codes = [proc.wait(timeout=5) for proc in processes]
                assert exit_codes == [0, 0], exit_codes
                assert produced == restored == total
                assert source_hash.digest() == restored_hash.digest()
                assert sent_before_consumer_release is not None and sent_before_consumer_release < total
                assert identities == {"cix": binary_identity(cix), "uncix": binary_identity(uncix)}
                for log in (encerr, decerr):
                    assert os.fstat(log.fileno()).st_size < 65536, "unexpected diagnostics volume"
                result = {
                    "scope": "bounded native raw-route streaming correctness/backpressure screen, not selector/history or isolated-host throughput qualification",
                    "source_generator": "repeat bytes(range(256))*256; one 65536-byte block retained",
                    "input_bytes": total, "restored_bytes": restored,
                    "sha256": source_hash.hexdigest(), "archive_bytes": archive_bytes,
                    "archive_sha256": archive_hash.hexdigest(), "exit_codes": exit_codes,
                    "commands": commands, "binary_identities": identities,
                    "memory_guard": guard, "cgroup_path": cg_path, "child_cgroups": child_cgroups,
                    "cgroup_memory_peak": (cg / "memory.peak").read_text().strip(),
                    "cpu": cpu, "relay_peak_bytes": relay_peak,
                    "native_rss_peak_sampled_bytes": native_rss_peak,
                    "downstream_hold_seconds": 0.3,
                    "input_sent_before_consumer_release": sent_before_consumer_release,
                    "first_archive_seconds": first_archive, "first_restored_seconds": first_restored,
                    "wall_seconds": time.monotonic() - started,
                    "input_temporary_spooling": False,
                }
                args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            except BaseException as error:
                for proc in processes:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()
                diagnostics = []
                for log in (encerr, decerr):
                    log.seek(0)
                    diagnostics.append({"bytes": os.fstat(log.fileno()).st_size,
                                        "prefix": log.read(65536).decode("utf-8", errors="replace")})
                args.output.write_text(json.dumps({"status": "FAILED", "error": str(error),
                    "commands": commands, "binary_identities": identities, "memory_guard": guard,
                    "exit_codes": [proc.returncode for proc in processes], "diagnostics": diagnostics}, indent=2) + "\n")
                raise
            finally:
                for proc in processes:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()
                    for stream in (proc.stdin, proc.stdout):
                        if stream and not stream.closed:
                            stream.close()


if __name__ == "__main__":
    main()
