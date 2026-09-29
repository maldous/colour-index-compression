#!/usr/bin/env python3
"""Record a bounded local process-tree and temporary-space measurement.

This is measurement instrumentation for a future Hutter candidate, not proof of
Prize compliance. The caller supplies an empty dedicated temporary directory and
the exact input/archive/restored paths to hash after the command exits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_pids(root: int) -> set[int]:
    pending, result = [root], set()
    while pending:
        pid = pending.pop()
        if pid in result or not Path(f"/proc/{pid}").exists():
            continue
        result.add(pid)
        try:
            children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        except OSError:
            children = []
        pending.extend(int(child) for child in children if child.isdigit())
    return result


def tree_rss_bytes(root: int) -> int:
    total = 0
    for pid in tree_pids(root):
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total += int(line.split()[1]) * 1024
                    break
        except (OSError, ValueError, IndexError):
            pass
    return total


def directory_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file() and not path.is_symlink())


def file_observation(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def measure(command: list[str], temp_dir: Path, *, cpu: int | None = None, interval: float = 0.1) -> dict:
    if not command:
        raise ValueError("command is required")
    if not temp_dir.is_dir():
        raise ValueError("temp_dir must already exist")
    before = directory_bytes(temp_dir)
    if before:
        raise ValueError("temp_dir must be empty so peak temporary bytes are meaningful")

    def pin_cpu() -> None:
        if cpu is not None:
            os.sched_setaffinity(0, {cpu})

    start = time.perf_counter()
    process = subprocess.Popen(command, cwd=temp_dir, preexec_fn=pin_cpu if cpu is not None else None)
    peak_rss = peak_temp = 0
    while process.poll() is None:
        peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
        peak_temp = max(peak_temp, directory_bytes(temp_dir))
        time.sleep(interval)
    peak_rss = max(peak_rss, tree_rss_bytes(process.pid))
    peak_temp = max(peak_temp, directory_bytes(temp_dir))
    return {"command": command, "exit_code": process.returncode, "completed": process.returncode == 0,
            "wall_seconds": time.perf_counter() - start, "peak_process_tree_rss_bytes": peak_rss,
            "peak_temp_bytes": peak_temp, "measurement_scope": "whole_enwik9_process_tree",
            "cpu_cores": 1 if cpu is not None else None, "cpu_affinity_requested": cpu,
            "gpu_used": None, "instrumentation_note": "GPU non-use and Geekbench score require separate audited evidence."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--cpu", type=int, default=0)
    parser.add_argument("--interval", type=float, default=0.1)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--restored", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    report = measure(command, args.temp_dir, cpu=args.cpu, interval=args.interval)
    report["artifacts"] = {"input": file_observation(args.input), "archive": file_observation(args.archive),
                           "restored": file_observation(args.restored)}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["completed"] else report["exit_code"] or 1


if __name__ == "__main__":
    raise SystemExit(main())
