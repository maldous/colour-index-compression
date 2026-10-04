#!/usr/bin/env python3
"""Write a bounded, non-secret platform inventory for one reviewed target."""
from __future__ import annotations
import argparse, json, os, platform, re, shutil, signal, subprocess, sys, threading, time
from pathlib import Path

TARGETS = {"linux-arm64", "windows-x64", "macos-arm64", "macos-x64"}
SHA = re.compile(r"^[0-9a-f]{40}$")

def memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def bounded_text(path: Path) -> str | None:
    try:
        return path.open("rt", encoding="ascii").read(128).strip()
    except OSError:
        return None


def cgroup_memory_cap_bytes() -> int | None:
    value = bounded_text(Path("/sys/fs/cgroup/memory.max"))
    return int(value) if value and value.isdecimal() else None


def stop_process(child: subprocess.Popen[bytes]) -> str:
    """Stop the direct child on Windows; stop its isolated group on POSIX."""
    if child.poll() is not None:
        return "none"
    if os.name == "posix":
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            return "process-group"
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
        return "process-group"
    child.terminate()
    try:
        child.wait(timeout=1)
    except subprocess.TimeoutExpired:
        child.kill()
    return "direct-child"


def toolchain_fact(name: str) -> dict[str, object]:
    executable = shutil.which(name)
    if executable is None:
        return {"available": False}
    retained = bytearray()
    overflow = threading.Event()
    child: subprocess.Popen[bytes] | None = None

    def drain(stream: object) -> None:
        assert hasattr(stream, "read")
        while True:
            block = stream.read(1024)  # type: ignore[union-attr]
            if not block:
                return
            remaining = 4096 - len(retained)
            retained.extend(block[:max(0, remaining)])
            if len(block) > remaining:
                overflow.set()
                return

    try:
        child = subprocess.Popen([executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 start_new_session=(os.name == "posix"))
        assert child.stdout is not None
        reader = threading.Thread(target=drain, args=(child.stdout,), daemon=True)
        reader.start()
        deadline, termination = time.monotonic() + 5, "none"
        while child.poll() is None and not overflow.is_set() and time.monotonic() < deadline:
            time.sleep(0.02)
        timed_out = child.poll() is None and not overflow.is_set() and time.monotonic() >= deadline
        if overflow.is_set() or timed_out:
            termination = stop_process(child)
        returncode = child.wait(timeout=2)
        reader.join(timeout=1)
        first = bytes(retained).decode("utf-8", errors="replace").splitlines()[:1]
        return {"available": True, "path": executable, "returncode": returncode,
                "retained_output_cap_bytes": 4096, "output_overflow_observed": overflow.is_set(),
                "timed_out": timed_out, "termination_scope": termination,
                "version_first_line": first[0][:512] if first else ""}
    except (OSError, subprocess.TimeoutExpired) as error:
        if child is not None:
            stop_process(child)
        return {"available": False, "error": type(error).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--target", required=True, choices=sorted(TARGETS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not SHA.fullmatch(args.source_sha):
        raise SystemExit("source SHA must be exactly 40 lowercase hexadecimal characters")
    if args.output.exists():
        raise SystemExit("refusing to overwrite an existing inventory artifact")
    disk = shutil.disk_usage(Path.cwd())
    observed_system, observed_machine = platform.system().lower(), platform.machine().lower()
    expected = {
        "linux-arm64": ("linux", {"aarch64", "arm64"}),
        "windows-x64": ("windows", {"amd64", "x86_64"}),
        "macos-arm64": ("darwin", {"arm64", "aarch64"}),
        "macos-x64": ("darwin", {"x86_64", "amd64"}),
    }[args.target]
    result = {
        "schema": "cix-platform-inventory-v1",
        "scope": "inventory only; no native or full-engine qualification",
        "requested": {"source_sha": args.source_sha, "target": args.target},
        "observed": {
            "platform": platform.platform(), "system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "python": platform.python_version(),
            "target_matches_observed_host": observed_system == expected[0] and observed_machine in expected[1],
            "runner_os": os.environ.get("RUNNER_OS"), "runner_arch": os.environ.get("RUNNER_ARCH"),
            "cpu_count": os.cpu_count(), "memory_bytes_visible": memory_bytes(),
            "cgroup_memory_cap_bytes": cgroup_memory_cap_bytes(),
            "cgroup_cpu_max": bounded_text(Path("/sys/fs/cgroup/cpu.max")),
            "workspace_disk_total_bytes": disk.total, "workspace_disk_free_bytes": disk.free,
            "toolchains": {name: toolchain_fact(name) for name in ("cargo", "rustc", "cmake", "cc", "c++")},
        },
        "limits": {"job_timeout_minutes": 8, "artifact_cap_bytes": 64_000_000,
                   "artifact_retention_days": 3, "no_secrets_or_dataset_content": True},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output.stat().st_size > 64_000_000:
        raise SystemExit("inventory artifact exceeds 64 MB cap")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
