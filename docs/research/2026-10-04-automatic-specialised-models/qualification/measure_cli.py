#!/usr/bin/env python3
"""Measure one ordinary staged CLI phase under its existing cgroup.

The outer WaveScheduler owns CPU, memory, temporary-storage and cgroup setup.
This wrapper neither reads an input nor verifies an archive: it only executes
the supplied CLI argv after "--" and records the completed subprocess phase.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from typing import Any


def _cgroup_directory() -> tuple[Path | None, str | None]:
    try:
        for line in Path("/proc/self/cgroup").read_text().splitlines():
            if line.startswith("0::"):
                relative = line.removeprefix("0::")
                return Path("/sys/fs/cgroup") / relative.lstrip("/"), relative
    except OSError:
        pass
    return None, None


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text().strip(), None
    except OSError as error:
        return None, f"{type(error).__name__}: {error}"


def _cpu_stat(path: Path) -> tuple[dict[str, int] | None, str | None]:
    text, error = _read_text(path)
    if error is not None or text is None:
        return None, error
    values: dict[str, int] = {}
    try:
        for line in text.splitlines():
            key, value = line.split(maxsplit=1)
            values[key] = int(value)
    except (TypeError, ValueError):
        return None, "invalid cpu.stat"
    return values, None


def _cgroup_observation() -> dict[str, Any]:
    directory, relative = _cgroup_directory()
    observation: dict[str, Any] = {
        "path": str(directory) if directory is not None else None,
        "relative_path": relative,
        "memory_peak_scope": (
            "kernel cgroup v2 memory.peak read after CLI exit while the "
            "measurement wrapper remains alive; it includes wrapper/phase "
            "overhead and is cumulative for this scheduler-created phase cgroup"
        ),
    }
    if directory is None:
        observation["error"] = "unified cgroup v2 path unavailable"
        return observation
    memory_peak, memory_peak_error = _read_text(directory / "memory.peak")
    memory_current, memory_current_error = _read_text(directory / "memory.current")
    cpu_stat, cpu_stat_error = _cpu_stat(directory / "cpu.stat")
    observation.update(
        memory_peak_bytes=int(memory_peak) if memory_peak and memory_peak.isdigit() else None,
        memory_current_bytes=int(memory_current) if memory_current and memory_current.isdigit() else None,
        cpu_stat=cpu_stat,
    )
    errors = [error for error in (memory_peak_error, memory_current_error, cpu_stat_error) if error]
    if errors:
        observation["read_errors"] = errors
    return observation


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=4, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _arguments(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if "--" not in argv:
        raise SystemExit("measure_cli.py requires ordinary CLI argv after --")
    split = argv.index("--")
    parser = argparse.ArgumentParser(
        description="Measure one staged CIX CLI phase without reading or verifying its data."
    )
    parser.add_argument(
        "--result",
        type=Path,
        required=True,
        help="JSON receipt written before the wrapper exits with the CLI status.",
    )
    parser.add_argument(
        "--phase",
        choices=("encode", "decode"),
        required=True,
        help="Descriptive phase label only; it does not alter CLI argv.",
    )
    return parser.parse_args(argv[:split]), argv[split + 1:]


def main(argv: list[str]) -> int:
    arguments, command = _arguments(argv)
    if not command:
        raise SystemExit("ordinary CLI argv after -- is empty")

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter_ns()
    launched = True
    try:
        process = subprocess.Popen(command)
        exit_code = process.wait()
        error: str | None = None
    except OSError as failure:
        launched = False
        exit_code = 127
        error = f"{type(failure).__name__}: {failure}"
    ended = time.perf_counter_ns()
    after = resource.getrusage(resource.RUSAGE_CHILDREN)

    receipt: dict[str, Any] = {
        "schema": "cix-cli-phase-measurement-v1",
        "phase": arguments.phase,
        "command": command,
        "status": "completed" if launched and exit_code == 0 else "failed",
        "cli_exit_code": exit_code if launched else None,
        "launch_error": error,
        "wall_seconds": (ended - started) / 1_000_000_000,
        "cpu_seconds": {
            "user": after.ru_utime - before.ru_utime,
            "system": after.ru_stime - before.ru_stime,
            "total": (
                after.ru_utime - before.ru_utime
                + after.ru_stime - before.ru_stime
            ),
            "scope": "resource.RUSAGE_CHILDREN delta for the ordinary CLI subprocess",
        },
        "cgroup": _cgroup_observation(),
    }
    _write_json(arguments.result, receipt)

    if launched and exit_code < 0:
        signum = -exit_code
        if signum not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        return 128 + signum
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
