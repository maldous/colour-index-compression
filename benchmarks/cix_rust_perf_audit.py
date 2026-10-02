#!/usr/bin/env python3
"""Reproducible, bounded local performance audit for native Rust CIX.

``prepare`` is deliberately non-executing: it freezes two already-built CIX
releases, the cached CCA gate fixtures, and a measurement matrix.  ``run`` is
an explicit local operation.  It refuses Silesia until every requested CCA
gate measurement has a fresh native decode and matching SHA-256.

The harness measures complete archives, not route payloads.  It has no input
name based encoder policy: labels exist solely for immutable evidence.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_bounded_runner import execute_phase as supervised_phase, stop_unit
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core
AREA = ROOT / "docs/research/2026-10-02-rust-performance-audit"
GATE_DIRS = (("canterbury", 11), ("calgary", 18), ("artificial", 4))
SILESIA_DIR = ROOT / "benchmark-work/silesia"
PROFILES = {
    "fast": {"flags": ["--fast"], "semantic": "FAST: latency-biased bounded search", "wall_seconds": 1800},
    "default": {"flags": [], "semantic": "DEFAULT/current: balanced automatic selection", "wall_seconds": 1800},
    "best": {"flags": ["--best"], "semantic": "BEST/size: size-biased bounded search", "wall_seconds": 7200},
}
SCHEMA = "cix-rust-performance-audit-v1"
# A result receipt is intentionally tiny.  Keeping every archive and every
# reconstructed input would turn a repeated Silesia audit into an unbounded
# duplicate corpus.  The fresh owning and cross decodes happen before this
# limit is applied; later resume validates the sealed measurement receipt.
MAX_RETAINED_EVIDENCE_BYTES = 128 * 1024
MAX_TOTAL_ATTEMPT_EVIDENCE_BYTES = 128 * 1024 * 1024


def execute_phase(**kwargs) -> dict:
    """Require the child receipt; transient-unit collection can erase status."""
    command = kwargs["command"]
    receipt = kwargs["destination"] / (kwargs["unit"] + ".child-status.json")
    if receipt.exists():
        raise RuntimeError(f"refusing stale phase child receipt: {receipt}")
    command_file = (kwargs["destination"] / (kwargs["unit"] + ".command.json")).resolve()
    with command_file.open("x") as stream:
        json.dump(command, stream)
    command_hash = sha256(command_file)
    launcher = ["/usr/bin/python3", str(ROOT / "benchmarks/cix_phase_receipt.py"),
                str(receipt), "--command-file", str(command_file), command_hash]
    result = supervised_phase(**{**kwargs, "command": launcher})
    result["command"] = command
    result["supervisor_command"] = launcher
    result["supervisor_exit_code"] = result["exit_code"]
    result["command_file_sha256"] = command_hash
    try:
        if sha256(command_file) != command_hash:
            raise ValueError("phase command file changed")
        child = json.loads(receipt.read_text())
        if (not isinstance(child, dict) or child.get("command") != command
                or type(child.get("child_exit_code")) is not int):
            raise ValueError("invalid child status receipt")
        result["child_status"] = child
        result["child_status_sha256"] = sha256(receipt)
        # Preserve an outer resource failure even if the child exited normally.
        if result["stop_reason"] is None:
            result["exit_code"] = child["child_exit_code"] or result["exit_code"]
    except (OSError, ValueError, TypeError):
        result["exit_code"] = result["exit_code"] or 1
        result["stop_reason"] = result["stop_reason"] or "missing_or_invalid_child_status"
    return result


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical(value) + b"\n")
    tmp.replace(path)


def rel(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)


def runtime_dsos(binary: Path) -> list[dict]:
    """Hash the dynamic objects actually resolved for a release executable."""
    probe = subprocess.run(["ldd", str(binary)], text=True, capture_output=True, check=False)
    if probe.returncode:
        raise RuntimeError(f"ldd failed for {binary}: {probe.stderr.strip()}")
    result: list[dict] = []
    for line in probe.stdout.splitlines():
        candidate = None
        if "=>" in line:
            right = line.split("=>", 1)[1].strip().split()
            if right and right[0].startswith("/"):
                candidate = Path(right[0])
        elif line.lstrip().startswith("/"):
            candidate = Path(line.split()[0])
        if candidate and candidate.is_file():
            result.append({"path": str(candidate), "sha256": sha256(candidate), "bytes": candidate.stat().st_size})
    return sorted(result, key=lambda value: value["path"])


def release_revision(value: dict) -> str:
    """Support both release schemas without losing or inventing provenance."""
    legacy = value.get("source_revision")
    source = value.get("source")
    current = source.get("revision") if isinstance(source, dict) else None
    revisions = [revision for revision in (legacy, current) if revision is not None]
    if not revisions or any(not isinstance(revision, str) or len(revision) != 40
                            or any(char not in "0123456789abcdef" for char in revision)
                            for revision in revisions):
        raise RuntimeError("release metadata requires an exact source commit")
    if len(set(revisions)) != 1:
        raise RuntimeError("release metadata has conflicting source commits")
    return revisions[0]


def artifact(path: Path, name: str) -> dict:
    path = path.resolve()
    metadata = path / "native-release.json"
    if not metadata.is_file():
        raise RuntimeError(f"{name}: native-release.json is missing: {path}")
    value = json.loads(metadata.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("binaries"), dict):
        raise RuntimeError(f"{name}: invalid native release metadata")
    binaries: dict[str, dict] = {}
    for binary in ("cix", "uncix"):
        entry = value["binaries"].get(binary, {})
        target = path / binary
        if not target.is_file() or not os.access(target, os.X_OK):
            raise RuntimeError(f"{name}: executable {binary} is unavailable")
        actual = sha256(target)
        if actual != entry.get("sha256"):
            raise RuntimeError(f"{name}: {binary} differs from release metadata")
        binaries[binary] = {"path": rel(target), "sha256": actual, "bytes": target.stat().st_size,
                            "runtime_dsos": runtime_dsos(target)}
    return {"name": name, "directory": rel(path), "source_revision": release_revision(value),
            "metadata": {"path": rel(metadata), "sha256": sha256(metadata)}, "binaries": binaries,
            "release_metadata": value}


def inputs(include_silesia: bool) -> list[dict]:
    census_path = ROOT / "docs/research/2026-10-02-fast-opportunity/fast-lz-cca-v2/input-census.json"
    census = {item["label"]: item for item in json.loads(census_path.read_text())["inputs"]}
    if len(census) != 33:
        raise RuntimeError("the frozen CCA census is incomplete")
    result: list[dict] = []
    for category, count in GATE_DIRS:
        directory = ROOT / "benchmark-work" / category
        members = sorted(p for p in directory.iterdir() if p.is_file()) if directory.is_dir() else []
        if len(members) != count:
            raise RuntimeError(f"expected {count} cached {category} gate fixtures, found {len(members)}")
        for p in members:
            label, digest = f"{category}/{p.name}", sha256(p)
            frozen = census.get(label)
            if not frozen or frozen.get("length") != p.stat().st_size or frozen.get("sha256") != digest:
                raise RuntimeError(f"cached gate fixture differs from the frozen census: {label}")
            result.append({"stage": "gate", "label": label, "path": rel(p), "bytes": p.stat().st_size,
                           "sha256": digest, "frozen_census": {"path": rel(census_path), "sha256": sha256(census_path)}})
    if include_silesia:
        members = sorted(p for p in SILESIA_DIR.iterdir() if p.is_file()) if SILESIA_DIR.is_dir() else []
        if len(members) != 12:
            raise RuntimeError(f"expected 12 cached Silesia fixtures, found {len(members)}")
        frozen_path = ROOT / "docs/research/2026-10-01-complete-benchmarks/silesia-v3/results.json"
        frozen = {item["name"]: item for item in json.loads(frozen_path.read_text()).get("members", [])}
        for p in members:
            digest, member = sha256(p), frozen.get(p.name)
            if not member or member.get("length") != p.stat().st_size or member.get("sha256") != digest:
                raise RuntimeError(f"cached Silesia fixture differs from frozen identity: {p.name}")
            result.append({"stage": "silesia", "label": f"silesia/{p.name}", "path": rel(p),
                           "bytes": p.stat().st_size, "sha256": digest,
                           "frozen_census": {"path": rel(frozen_path), "sha256": sha256(frozen_path)}})
    if len(result) != 33 + (12 if include_silesia else 0):
        raise RuntimeError("fixture census failed")
    return result


def physical_cpus() -> list[int]:
    available = sorted(os.sched_getaffinity(0))
    seen: set[tuple[str, str]] = set()
    answer: list[int] = []
    for cpu in available:
        top = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            core = ((top / "physical_package_id").read_text().strip(), (top / "core_id").read_text().strip())
        except OSError:
            core = ("unknown", str(cpu))
        if core not in seen:
            seen.add(core)
            answer.append(cpu)
    return answer


def cpu_topology() -> list[dict]:
    rows = []
    for cpu in sorted(os.sched_getaffinity(0)):
        top, base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology"), Path(f"/sys/devices/system/cpu/cpu{cpu}")
        def read(name: str) -> str | None:
            try: return (top / name).read_text().strip()
            except OSError: return None
        try: capacity = (base / "cpu_capacity").read_text().strip()
        except OSError: capacity = None
        rows.append({"cpu": cpu, "package": read("physical_package_id"), "core": read("core_id"),
                     "siblings": read("thread_siblings_list"), "capacity": capacity})
    return rows


def cpu_sets(workers: int, jobs: int) -> list[list[int]]:
    physical = physical_cpus()
    required = workers * jobs
    if len(physical) < required:
        raise RuntimeError(f"need {required} distinct physical CPUs for {jobs} jobs x {workers} threads; have {len(physical)}")
    return [physical[i * workers:(i + 1) * workers] for i in range(jobs)]


def summary_stats(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {"count": len(values), "min": min(values), "max": max(values), "mean": mean,
            "stdev_population": variance ** 0.5}


def parse_gnu_time(path: Path) -> dict:
    fields = {}
    for line in path.read_text(errors="replace").splitlines():
        # GNU time's elapsed label itself contains h:mm:ss.  Splitting on the
        # first colon turns the key into "Elapsed (wall clock) time (h".
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip()
    required = ("User time (seconds)", "System time (seconds)", "Elapsed (wall clock) time (h:mm:ss or m:ss)",
                "Maximum resident set size (kbytes)")
    if any(key not in fields for key in required):
        raise RuntimeError(f"incomplete GNU time record: {path}")
    wall = fields["Elapsed (wall clock) time (h:mm:ss or m:ss)"]
    parts = [float(part) for part in wall.split(":")]
    seconds = parts[-1] + (60 * parts[-2] if len(parts) >= 2 else 0) + (3600 * parts[-3] if len(parts) == 3 else 0)
    return {"user_seconds": float(fields["User time (seconds)"]), "system_seconds": float(fields["System time (seconds)"]),
            "wall_seconds": seconds, "max_rss_bytes": int(fields["Maximum resident set size (kbytes)"]) * 1024,
            "raw": fields}


def task_id(row: dict) -> str:
    return hashlib.sha256(canonical(row)).hexdigest()[:24]


def plan_rows(artifacts: list[dict], fixture_rows: list[dict], profiles: list[str], threads: list[int], repetitions: int) -> list[dict]:
    rows = []
    for fixture in fixture_rows:
        for profile in profiles:
            for workers in threads:
                for repetition in range(repetitions):
                    # Alternating the two releases within a repetition
                    # controls slow thermal/frequency drift without ever
                    # running the same input concurrently.
                    ordered_releases = artifacts if repetition % 2 == 0 else list(reversed(artifacts))
                    for release in ordered_releases:
                        row = {"stage": fixture["stage"], "input": fixture, "release": release["name"],
                               "release_cix_sha256": release["binaries"]["cix"]["sha256"],
                               "release_uncix_sha256": release["binaries"]["uncix"]["sha256"],
                               "profile": profile, "flags": PROFILES[profile]["flags"], "threads": workers,
                               "repetition": repetition + 1}
                        row["task_id"] = task_id(row)
                        rows.append(row)
    return rows


def require_idle_wave(function):
    """Keep non-timed hashing/reporting from disturbing an active wave."""
    @wraps(function)
    def locked(*args, **kwargs):
        scheduler = WaveScheduler(ROOT)
        scheduler.state.mkdir(parents=True, exist_ok=True)
        lock = scheduler._wave_lock_path().open("a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock.close()
            raise RuntimeError("another WaveScheduler wave holds the aggregate resource budget") from exc
        try:
            return function(*args, **kwargs)
        finally:
            lock.close()
    return locked


@require_idle_wave
def prepare(args: argparse.Namespace) -> None:
    destination = AREA / args.id
    if destination.exists():
        raise RuntimeError(f"immutable audit exists: {destination}")
    before, current = artifact(args.before, "pre_refactor"), artifact(args.current, "current")
    if before["binaries"]["cix"]["sha256"] == current["binaries"]["cix"]["sha256"]:
        raise RuntimeError("pre-refactor and current CIX binaries are identical; provide distinct releases")
    profiles = args.profiles.split(",")
    if not profiles or any(profile not in PROFILES for profile in profiles):
        raise RuntimeError("profiles must be a non-empty subset of fast,default,best")
    threads = [int(value) for value in args.threads.split(",")]
    if any(value < 1 or value > 20 for value in threads) or len(set(threads)) != len(threads):
        raise RuntimeError("threads must be unique values from 1 through 20")
    fixtures = inputs(args.include_silesia)
    rows = plan_rows([before, current], fixtures, profiles, threads, args.repetitions)
    destination.mkdir(parents=True)
    write_json(destination / "fixtures.json", {"schema": SCHEMA, "frozen_at": utc(), "fixtures": fixtures})
    write_json(destination / "artifacts.json", {"schema": SCHEMA, "frozen_at": utc(), "artifacts": [before, current]})
    plan_value = {
        "schema": SCHEMA, "identity": args.id, "status": "PREPARED_NOT_EXECUTED", "prepared_at": utc(),
        "objective": "Matched pre-refactor/current Rust performance audit; complete archive cost and fresh native exact decode.",
        "profiles": {key: PROFILES[key] for key in profiles}, "historical_profile_mapping": {"current": "default", "size": "best"},
        "repetitions": args.repetitions, "thread_sweep": threads,
        "execution_policy": {"gate_before_silesia": True, "max_parallel_datasets": 4, "threads_per_dataset_default": 4,
                             "global_ram_bytes": 12_000_000_000, "global_temp_bytes": 4_000_000_000, "swap_bytes": 0,
                             "no_actions": True, "no_acquisition": True},
        "rows": rows, "row_count": len(rows), "artifact_sha256": hashlib.sha256(canonical([before, current])).hexdigest(),
        "fixture_sha256": hashlib.sha256(canonical(fixtures)).hexdigest(),
    }
    write_json(destination / "plan.json", plan_value)
    environment = {
        "captured_at": utc(), "platform": platform.platform(), "python": sys.version, "kernel": platform.release(),
        "affinity": sorted(os.sched_getaffinity(0)), "physical_cpus_visible": physical_cpus(), "cpu_topology": cpu_topology(),
        "cix_worker_limit": {"maximum_supported": 20, "visible_logical_cpus": len(os.sched_getaffinity(0)),
                             "gap": "CIX deliberately rejects --threads >20; logical-core scaling beyond 20 is unavailable until implementation changes."},
        "rustc": subprocess.run(["rustc", "-Vv"], text=True, capture_output=True, check=False).stdout,
        "cargo": subprocess.run(["cargo", "-V"], text=True, capture_output=True, check=False).stdout,
        "perf_available": shutil.which("perf") is not None, "gnu_time": "/usr/bin/time" if Path("/usr/bin/time").is_file() else None,
    }
    write_json(destination / "environment.json", environment)
    binding = {"schema": SCHEMA, "identity": args.id, "created_at": utc(),
               "files": {name: sha256(destination / name) for name in ("fixtures.json", "artifacts.json", "plan.json", "environment.json")},
               "artifact_sha256": plan_value["artifact_sha256"], "fixture_sha256": plan_value["fixture_sha256"],
               "implementation": {rel(Path(__file__)): sha256(Path(__file__)),
                                  "benchmarks/hutter_bounded_runner.py": sha256(ROOT / "benchmarks/hutter_bounded_runner.py"),
                                  "benchmarks/cix_phase_receipt.py": sha256(ROOT / "benchmarks/cix_phase_receipt.py"),
                                  "benchmarks/hutter_experiment_scheduler.py": sha256(ROOT / "benchmarks/hutter_experiment_scheduler.py")},
               "row_ids": [row["task_id"] for row in rows]}
    if len(set(binding["row_ids"])) != len(rows):
        raise RuntimeError("task ID collision in immutable audit plan")
    write_json(destination / "manifest-binding.json", binding)
    print(json.dumps({"prepared": rel(destination), "rows": len(rows), "gate_fixtures": 33,
                      "silesia_fixtures": 12 if args.include_silesia else 0,
                      "binding_sha256": sha256(destination / "manifest-binding.json")}, sort_keys=True))


def phase_command(row: dict, release: dict, work: Path, decode: bool, *, output: Path | None = None) -> tuple[list[str], Path]:
    source = ROOT / row["input"]["path"]
    archive = work / "candidate.cix"
    output = output or (work / "restored.bin")
    binary = ROOT / release["binaries"]["uncix" if decode else "cix"]["path"]
    time_file = work / ("decode.gnu-time.txt" if decode else "encode.gnu-time.txt")
    command = ["/usr/bin/time", "-v", "-o", str(time_file), str(binary)]
    if decode:
        command += ["-f", "-o", str(output), str(archive)]
    else:
        # Timed measurements deliberately omit --verbose: stderr reporting
        # changes allocation and formatting work without changing the format.
        command += [*row["flags"], "--threads", str(row["threads"]), "-f", "-o", str(archive), str(source)]
    return command, time_file


def affinity_wrapped(command: list[str], affinity_path: Path, cgroup_path: Path) -> list[str]:
    """Record effective affinity and cgroup limits from inside the unit."""
    script = ('set -e; taskset -pc $$ > "$1"; cg=$(awk -F: \'$1 == "0" {print $3}\' /proc/self/cgroup); '
              'base=/sys/fs/cgroup$cg; test -r "$base/cpuset.cpus.effective"; test -r "$base/memory.max"; test -r "$base/memory.swap.max"; printf "cpuset=%s\\nmemory.max=%s\\nmemory.swap.max=%s\\n" '
              '"$(cat "$base/cpuset.cpus.effective")" "$(cat "$base/memory.max")" "$(cat "$base/memory.swap.max")" > "$2"; shift 2; exec "$@"')
    return ["/bin/bash", "-c", script, "cix-cgroup", str(affinity_path), str(cgroup_path), *command]


def affinity_set(record: str | None) -> list[int] | None:
    if not record or ":" not in record:
        return None
    try:
        result = []
        for part in record.rsplit(":", 1)[1].strip().split(","):
            lo, *hi = part.split("-", 1)
            result.extend(range(int(lo), int(hi[0]) + 1) if hi else [int(lo)])
        return sorted(result)
    except ValueError:
        return None


def cgroup_ok(record: str | None, cpus: list[int], budget: dict) -> bool:
    try:
        fields = dict(line.split("=", 1) for line in (record or "").splitlines() if "=" in line)
        listed = affinity_set("cpuset: " + fields["cpuset"])
        return (listed == sorted(cpus) and fields["memory.max"] == str(budget["max_rss_bytes"])
                and fields["memory.swap.max"] == "0")
    except (KeyError, ValueError):
        return False


def revalidate_input(row: dict) -> tuple[Path, str]:
    """Reject a mutable fixture before it reaches any timed worker."""
    source = ROOT / row["input"]["path"]
    source_hash = sha256(source) if source.is_file() else None
    if source_hash != row["input"]["sha256"] or source.stat().st_size != row["input"]["bytes"]:
        raise RuntimeError("input differs from the immutable fixture identity")
    return source, source_hash


def revalidate_release(release: dict) -> None:
    """Reject mutable executables/DSOs before or after a timed wave."""
    metadata = ROOT / release["metadata"]["path"]
    if not metadata.is_file() or sha256(metadata) != release["metadata"]["sha256"]:
        raise RuntimeError(f"frozen {release['name']} release metadata changed before trial")
    for name, declared in release["binaries"].items():
        binary = ROOT / declared["path"]
        if not binary.is_file() or sha256(binary) != declared["sha256"]:
            raise RuntimeError(f"frozen {release['name']} {name} artifact changed before trial")
        if runtime_dsos(binary) != declared.get("runtime_dsos", []):
            raise RuntimeError(f"runtime DSO identity changed for frozen {release['name']} {name}")


def revalidate_task(row: dict, release: dict) -> tuple[Path, str]:
    """Compatibility helper for non-timed receipt validation."""
    source, source_hash = revalidate_input(row)
    revalidate_release(release)
    return source, source_hash


def preflight(rows: list[dict], releases: dict[str, dict]) -> dict:
    """Sequentially hash all dependencies outside timed worker intervals."""
    fixture_identity = {}
    for row in rows:
        label = row["input"]["label"]
        if label not in fixture_identity:
            source, digest = revalidate_input(row)
            fixture_identity[label] = {"path": str(source), "bytes": source.stat().st_size, "sha256": digest}
    for release in releases.values():
        revalidate_release(release)
    value = {"fixtures": fixture_identity,
             "releases": {name: {binary: release["binaries"][binary]["sha256"] for binary in ("cix", "uncix")}
                          for name, release in releases.items()}}
    return {"value": value, "sha256": hashlib.sha256(canonical(value)).hexdigest()}


def phase_ok(phase: object) -> bool:
    return isinstance(phase, dict) and phase.get("exit_code") == 0 and phase.get("stop_reason") is None


def complete_metrics(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        return (all(math.isfinite(float(value[key])) and float(value[key]) >= 0
                    for key in ("user_seconds", "system_seconds", "wall_seconds"))
                and isinstance(value["max_rss_bytes"], int) and value["max_rss_bytes"] >= 0
                and isinstance(value.get("raw"), dict))
    except (KeyError, TypeError, ValueError):
        return False


def directory_bytes(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def prune_verified_payloads(work: Path, output: dict, archive: Path, restored: Path) -> None:
    """Retain a bounded receipt after fresh owning and cross decode proof.

    Every payload below was hashed and compared while it existed.  We preserve
    its name/length/digest and the phase receipts, but remove raw archives and
    decoded copies so a complete repeated corpus plan stays within the shared
    temporary-space ceiling.
    """
    paths = [archive, restored, *(Path(item["path"]) for item in output["cross_decode"] if item.get("path"))]
    if not all(path.is_file() for path in paths):
        raise RuntimeError("cannot seal a verified measurement with a missing payload")
    output["pruned_artifacts"] = [
        {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in paths
    ]
    for path in paths:
        path.unlink()
    # The structured phase record retains exit status, exact command, stop
    # reason and cgroup high-water.  Raw command logs can be arbitrarily large
    # for a failing native backend and therefore are not retained in a verified
    # receipt.  GNU Time, affinity and cgroup observations remain reparseable.
    for pattern in ("*.stdout.log", "*.stderr.log", "progress.jsonl"):
        for path in work.glob(pattern):
            path.unlink()
    output["artifacts_pruned_after_fresh_verification"] = True
    retained = directory_bytes(work)
    if retained > MAX_RETAINED_EVIDENCE_BYTES:
        raise RuntimeError(f"verified receipt exceeds bounded evidence limit: {retained} bytes")
    output["retained_evidence_bytes"] = retained


def expected_payload_receipts(output: dict, archive: Path, restored: Path) -> list[dict]:
    """The pre-prune receipt is sufficient to name every verified payload."""
    input_id = output["task"]["input"]
    paths = [
        {"path": str(archive), "bytes": output["archive_bytes"], "sha256": output["archive_sha256"]},
        {"path": str(restored), "bytes": input_id["bytes"], "sha256": input_id["sha256"]},
    ]
    for item in output["cross_decode"]:
        paths.append({"path": item["path"], "bytes": input_id["bytes"], "sha256": item["restored_sha256"]})
    return paths


def archive_attempt(destination: Path, work: Path, reason: str) -> None:
    """Preserve interrupted/unqualified evidence while permitting one retry."""
    # An interrupted encoder can leave a near-input-sized raw fallback or a
    # backend log behind.  Keep only small diagnostic receipts, never a second
    # unbounded payload corpus under attempts/.
    for path in (work / "candidate.cix", work / "restored.bin", *work.glob("cross-*.bin")):
        path.unlink(missing_ok=True)
    keep_suffixes = (".gnu-time.txt", ".effective-affinity.txt", ".effective-cgroup.txt")
    keep_names = {"result.json", "sealing-receipt.json"}
    for path in sorted(work.rglob("*"), reverse=True):
        if path.is_file() and path.name not in keep_names and not path.name.endswith(keep_suffixes):
            path.unlink()
        elif path.is_dir() and path != work:
            try:
                path.rmdir()
            except OSError:
                pass
    if directory_bytes(work) > MAX_RETAINED_EVIDENCE_BYTES:
        raise RuntimeError("interrupted attempt exceeds bounded evidence limit")
    attempts = destination / "attempts" / work.name
    existing = directory_bytes(destination / "attempts") if (destination / "attempts").is_dir() else 0
    if existing + directory_bytes(work) > MAX_TOTAL_ATTEMPT_EVIDENCE_BYTES:
        raise RuntimeError("aggregate interrupted-attempt evidence limit reached; preserve and review before retrying")
    attempts.mkdir(parents=True, exist_ok=True)
    suffix = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{reason}"
    work.replace(attempts / suffix)


def finalize_pruning(work: Path, output: dict, archive: Path, restored: Path, sealing: Path) -> dict:
    """Finish an interrupted sealing transaction without rerunning a task.

    The first atomic sealing receipt is written before deletion.  If the host
    stops after that point, a later invocation reconstructs the bounded
    receipt from that record and removes any surviving payloads.  It never
    mistakes a partial directory for a completed benchmark result.
    """
    paths = [archive, restored, *(Path(item["path"]) for item in output["cross_decode"])]
    expected = {item["path"]: item for item in expected_payload_receipts(output, archive, restored)}
    for path in paths:
        if path.is_file() and (path.stat().st_size != expected[str(path)]["bytes"]
                               or sha256(path) != expected[str(path)]["sha256"]):
            raise RuntimeError("payload changed after the atomic pre-prune receipt")
    if all(path.is_file() for path in paths):
        prune_verified_payloads(work, output, archive, restored)
    else:
        for path in paths:
            if path.is_file():
                path.unlink()
        output["pruned_artifacts"] = expected_payload_receipts(output, archive, restored)
        output["artifacts_pruned_after_fresh_verification"] = True
        retained = directory_bytes(work)
        if retained > MAX_RETAINED_EVIDENCE_BYTES:
            raise RuntimeError(f"interrupted verified receipt exceeds bounded evidence limit: {retained} bytes")
        output["retained_evidence_bytes"] = retained
    output["status"] = "VERIFIED"
    output["finished_at"] = utc()
    write_json(work / "result.json", output)
    sealing.unlink(missing_ok=True)
    return output


def valid_execution_identity(destination: Path, identity: object) -> bool:
    if not isinstance(identity, dict):
        return False
    content = {key: value for key, value in identity.items() if key != "sha256"}
    digest = hashlib.sha256(canonical(content)).hexdigest()
    path = destination / "execution-bindings" / f"{digest}.json"
    try:
        return identity.get("sha256") == digest and path.is_file() and json.loads(path.read_text()) == identity
    except (OSError, json.JSONDecodeError):
        return False


def wave_completed(destination: Path, identity: dict) -> bool:
    """Rows become reusable only after the locked postflight succeeds."""
    try:
        path = destination / "wave-completions" / f"{identity['sha256']}.json"
        value = json.loads(path.read_text())
        return (value.get("status") == "POSTFLIGHT_VERIFIED" and value.get("execution_identity") == identity
                and value.get("preflight_sha256") == identity.get("sequential_preflight_sha256")
                and value.get("postflight_sha256") == identity.get("sequential_preflight_sha256"))
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def validate_binding(destination: Path, supplied_sha256: str) -> tuple[dict, dict[str, dict]]:
    binding_path = destination / "manifest-binding.json"
    if sha256(binding_path) != supplied_sha256:
        raise RuntimeError("--binding-sha does not match the immutable manifest binding")
    binding = json.loads(binding_path.read_text())
    helper = "benchmarks/cix_phase_receipt.py"
    if binding.get("implementation", {}).get(helper) != sha256(ROOT / helper):
        raise RuntimeError("audit binding lacks the current child-status supervisor; prepare a new identity")
    for name, expected in binding.get("files", {}).items():
        if sha256(destination / name) != expected:
            raise RuntimeError(f"immutable audit file changed after preparation: {name}")
    for name, expected in binding.get("implementation", {}).items():
        if sha256(ROOT / name) != expected:
            raise RuntimeError(f"audit implementation changed after preparation: {name}")
    plan = json.loads((destination / "plan.json").read_text())
    artifacts = json.loads((destination / "artifacts.json").read_text())["artifacts"]
    fixtures = json.loads((destination / "fixtures.json").read_text())["fixtures"]
    if (plan.get("artifact_sha256") != binding.get("artifact_sha256")
            or plan.get("fixture_sha256") != binding.get("fixture_sha256")
            or hashlib.sha256(canonical(artifacts)).hexdigest() != binding.get("artifact_sha256")
            or hashlib.sha256(canonical(fixtures)).hexdigest() != binding.get("fixture_sha256")):
        raise RuntimeError("plan/artifact/fixture immutable binding mismatch")
    if [row.get("task_id") for row in plan.get("rows", [])] != binding.get("row_ids"):
        raise RuntimeError("plan task rows changed after preparation")
    releases = {value["name"]: value for value in artifacts}
    if len(releases) != 2:
        raise RuntimeError("audit requires exactly two frozen releases")
    for row in plan["rows"]:
        if task_id({key: value for key, value in row.items() if key != "task_id"}) != row["task_id"]:
            raise RuntimeError("task ID does not bind its complete task manifest")
        release = releases.get(row["release"])
        if not release or row.get("release_cix_sha256") != release["binaries"]["cix"]["sha256"] or row.get("release_uncix_sha256") != release["binaries"]["uncix"]["sha256"]:
            raise RuntimeError("task release binding mismatch")
    return plan, releases


def verified_result(path: Path, row: dict, releases: dict[str, dict]) -> bool:
    """Revalidate an unpruned payload or its bounded fresh-decode receipt."""
    try:
        value = json.loads(path.read_text())
        work = path.parent
        identity = value.get("execution_identity")
        if value.get("status") != "VERIFIED" or value.get("task") != row or not isinstance(identity, dict):
            return False
        destination = path.parents[2]
        if not valid_execution_identity(destination, identity):
            return False
        if not wave_completed(destination, identity):
            return False
        lane = identity.get("dataset_lane", {}).get(row["input"]["label"])
        cpu_sets = identity.get("cpu_sets")
        if (identity.get("manifest_binding_sha256") != sha256(destination / "manifest-binding.json") or identity.get("stage") != row["stage"]
                or identity.get("threads") != row["threads"] or not isinstance(lane, int) or not isinstance(cpu_sets, list)
                or lane < 0 or lane >= len(cpu_sets) or value.get("cpu_set") != cpu_sets[lane] or len(value["cpu_set"]) != row["threads"]):
            return False
        if value.get("sequential_preflight_sha256") != identity.get("sequential_preflight_sha256"):
            return False
        if value.get("budget") != {"max_rss_bytes": identity.get("max_rss_bytes_per_job"), "max_temp_bytes": identity.get("max_temp_bytes_per_job"), "wall_seconds": PROFILES[row["profile"]]["wall_seconds"]}:
            return False
        source, digest = revalidate_task(row, releases[row["release"]])
        for release in releases.values():
            revalidate_task(row, release)
        archive, restored = work / "candidate.cix", work / "restored.bin"
        encode_command, encode_time = phase_command(row, releases[row["release"]], work, False)
        decode_command, decode_time = phase_command(row, releases[row["release"]], work, True)
        expected_encode = affinity_wrapped(encode_command, work / "encode.effective-affinity.txt", work / "encode.effective-cgroup.txt")
        expected_decode = affinity_wrapped(decode_command, work / "decode.effective-affinity.txt", work / "decode.effective-cgroup.txt")
        pruned = value.get("artifacts_pruned_after_fresh_verification") is True
        if (value.get("encode_exit") != 0 or value.get("decode_exit") != 0
                or not phase_ok(value.get("encode_phase"))
                or not phase_ok(value.get("decode_phase")) or not complete_metrics(value.get("encode"))
                or not complete_metrics(value.get("decode")) or parse_gnu_time(encode_time) != value.get("encode")
                or parse_gnu_time(decode_time) != value.get("decode")
                or value.get("encode_phase", {}).get("command") != expected_encode or value.get("decode_phase", {}).get("command") != expected_decode
                or affinity_set(value.get("encode_effective_affinity")) != sorted(value["cpu_set"])
                or affinity_set(value.get("decode_effective_affinity")) != sorted(value["cpu_set"])
                or not cgroup_ok(value.get("encode_effective_cgroup"), value["cpu_set"], value["budget"])
                or not cgroup_ok(value.get("decode_effective_cgroup"), value["cpu_set"], value["budget"])):
            return False
        cross = value.get("cross_decode")
        other = next((name for name in releases if name != row["release"]), None)
        if not (other and isinstance(cross, list) and len(cross) == 1 and cross[0].get("matched") and phase_ok(cross[0].get("phase"))
                and cross[0].get("decoder_release") == other and affinity_set(cross[0].get("effective_affinity")) == sorted(value["cpu_set"])
                and cgroup_ok(cross[0].get("effective_cgroup"), value["cpu_set"], value["budget"])):
            return False
        cross_path = Path(cross[0].get("path", ""))
        expected_cross = path.parent / f"cross-{other}.bin"
        expected_cross_command = affinity_wrapped([str(ROOT / releases[other]["binaries"]["uncix"]["path"]), "-f", "-o", str(expected_cross), str(archive)],
                                                  work / f"cross-{other}.effective-affinity.txt", work / f"cross-{other}.effective-cgroup.txt")
        if cross_path != expected_cross or cross[0].get("phase", {}).get("command") != expected_cross_command:
            return False
        expected_payloads = {
            str(archive): {"bytes": value.get("archive_bytes"), "sha256": value.get("archive_sha256")},
            str(restored): {"bytes": source.stat().st_size, "sha256": digest},
            str(expected_cross): {"bytes": source.stat().st_size, "sha256": digest},
        }
        if pruned:
            sealed = value.get("pruned_artifacts")
            if (not isinstance(sealed, list) or value.get("retained_evidence_bytes") is None
                    or not isinstance(value["retained_evidence_bytes"], int)
                    or value["retained_evidence_bytes"] > MAX_RETAINED_EVIDENCE_BYTES
                    or directory_bytes(work) > MAX_RETAINED_EVIDENCE_BYTES
                    or len(sealed) != len(expected_payloads) or any(Path(name).is_file() for name in expected_payloads)):
                return False
            by_path = {item.get("path"): {"bytes": item.get("bytes"), "sha256": item.get("sha256")}
                       for item in sealed if isinstance(item, dict)}
            return by_path == expected_payloads and cross[0].get("restored_sha256") == digest
        return (archive.is_file() and restored.is_file() and value.get("archive_bytes") == archive.stat().st_size
                and value.get("archive_sha256") == sha256(archive) and value.get("restored_sha256") == sha256(restored)
                and sha256(restored) == digest and restored.stat().st_size == source.stat().st_size
                and cross_path.is_file() and cross[0].get("restored_sha256") == sha256(cross_path)
                and sha256(cross_path) == digest and cross_path.stat().st_size == source.stat().st_size)
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError):
        return False


def run_one(destination: Path, row: dict, releases: dict[str, dict], cpus: list[int], budget: dict,
            execution_identity: dict, preflight_identity: dict) -> dict:
    work = destination / "runs" / row["task_id"]
    result_path = work / "result.json"
    if work.exists():
        if result_path.is_file():
            old = json.loads(result_path.read_text())
            if old.get("status") == "VERIFIED" and wave_completed(destination, old.get("execution_identity", {})):
                return old
            archive_attempt(destination, work, "unqualified" if old.get("status") != "VERIFIED" else "unsealed-wave")
        else:
            sealing = work / "sealing-receipt.json"
            had_sealing = sealing.is_file()
            if sealing.is_file():
                sealed = json.loads(sealing.read_text())
                output = sealed.get("output") if isinstance(sealed, dict) else None
                same_execution = (isinstance(output, dict) and output.get("execution_identity") == execution_identity
                                  and output.get("cpu_set") == cpus and output.get("budget") == budget
                                  and output.get("sequential_preflight_sha256") == preflight_identity["sha256"])
                if (isinstance(sealed, dict) and sealed.get("state") == "PRUNING" and isinstance(output, dict)
                        and output.get("task") == row and same_execution):
                    return finalize_pruning(work, output, work / "candidate.cix", work / "restored.bin", sealing)
            archive_attempt(destination, work, "interrupted-other-execution" if had_sealing else "interrupted")
    work.mkdir(parents=True, exist_ok=False)
    release = releases[row["release"]]
    source_hash = None
    source = None
    encode, encode_time = phase_command(row, release, work, False)
    decode, decode_time = phase_command(row, release, work, True)
    encode_affinity, decode_affinity = work / "encode.effective-affinity.txt", work / "decode.effective-affinity.txt"
    encode_cgroup, decode_cgroup = work / "encode.effective-cgroup.txt", work / "decode.effective-cgroup.txt"
    encode, decode = affinity_wrapped(encode, encode_affinity, encode_cgroup), affinity_wrapped(decode, decode_affinity, decode_cgroup)
    started = utc()
    archive, restored = work / "candidate.cix", work / "restored.bin"
    output = {"schema": SCHEMA, "task": row, "started_at": started, "cpu_set": cpus,
              "execution_identity": execution_identity,
              "sequential_preflight_sha256": preflight_identity["sha256"],
              "requested_cpu_set": cpus, "effective_worker_count": row["threads"],
              "resource_enforcement": "systemd cgroup MemoryMax + MemorySwapMax=0 + KillMode=control-group + RuntimeMaxSec + AllowedCPUs",
              "budget": budget, "input_sha256": row["input"]["sha256"], "cross_decode": []}
    try:
        source = ROOT / row["input"]["path"]
        fixture = preflight_identity["value"]["fixtures"].get(row["input"]["label"])
        if not fixture or fixture.get("path") != str(source) or fixture.get("sha256") != row["input"]["sha256"]:
            raise RuntimeError("worker lacks the immutable sequential preflight identity")
        source_hash = fixture["sha256"]
        begin = time.perf_counter_ns()
        encoded = execute_phase(unit=f"cix-perf-{row['task_id']}-encode", command=encode, work=work, destination=work,
                                budget=budget, cpu=cpus, inaccessible=[], input_bytes=row["input"]["bytes"])
        output["encode_phase"] = {**encoded, "wrapper_wall_nanoseconds": time.perf_counter_ns() - begin}
        output["encode_effective_affinity"] = encode_affinity.read_text().strip() if encode_affinity.is_file() else None
        output["encode_effective_cgroup"] = encode_cgroup.read_text().strip() if encode_cgroup.is_file() else None
        decoded = None
        if phase_ok(encoded):
            begin = time.perf_counter_ns()
            decoded = execute_phase(unit=f"cix-perf-{row['task_id']}-decode", command=decode, work=work, destination=work,
                                    budget=budget, cpu=cpus, inaccessible=[source], input_bytes=row["input"]["bytes"])
            output["decode_phase"] = {**decoded, "wrapper_wall_nanoseconds": time.perf_counter_ns() - begin}
            output["decode_effective_affinity"] = decode_affinity.read_text().strip() if decode_affinity.is_file() else None
            output["decode_effective_cgroup"] = decode_cgroup.read_text().strip() if decode_cgroup.is_file() else None
        output["encode_exit"] = encoded["exit_code"]
        output["decode_exit"] = None if decoded is None else decoded["exit_code"]
    except BaseException as exc:
        output["execution_error"] = f"{type(exc).__name__}: {exc}"
        output["encode_exit"], output["decode_exit"] = None, None
    for key, path in (("encode", encode_time), ("decode", decode_time)):
        if path.is_file():
            try: output[key] = parse_gnu_time(path)
            except BaseException as exc: output[f"{key}_metric_error"] = f"{type(exc).__name__}: {exc}"
        else:
            output[f"{key}_metric_error"] = "missing GNU Time record"
    output.update({"archive_bytes": archive.stat().st_size if archive.is_file() else None,
                   "archive_sha256": sha256(archive) if archive.is_file() else None,
                   "restored_sha256": sha256(restored) if restored.is_file() else None,
                   "revalidated_input_sha256": source_hash})
    if source and archive.is_file() and phase_ok(output.get("encode_phase")):
        for other_name, other in releases.items():
            if other_name == release["name"]: continue
            cross_output = work / f"cross-{other_name}.bin"
            cross_affinity = work / f"cross-{other_name}.effective-affinity.txt"
            cross_cgroup = work / f"cross-{other_name}.effective-cgroup.txt"
            command = affinity_wrapped([str(ROOT / other["binaries"]["uncix"]["path"]), "-f", "-o", str(cross_output), str(archive)], cross_affinity, cross_cgroup)
            try:
                phase = execute_phase(unit=f"cix-perf-{row['task_id']}-cross-{other_name}", command=command, work=work,
                                      destination=work, budget=budget, cpu=cpus, inaccessible=[source], input_bytes=row["input"]["bytes"])
                restored_hash = sha256(cross_output) if cross_output.is_file() else None
                output["cross_decode"].append({"decoder_release": other_name, "exit_code": phase["exit_code"],
                                               "phase": phase, "path": str(cross_output), "effective_affinity": cross_affinity.read_text().strip() if cross_affinity.is_file() else None, "effective_cgroup": cross_cgroup.read_text().strip() if cross_cgroup.is_file() else None, "restored_sha256": restored_hash,
                                               "matched": phase_ok(phase) and restored_hash == source_hash and cross_output.stat().st_size == row["input"]["bytes"] if cross_output.is_file() else False})
            except BaseException as exc:
                output["cross_decode"].append({"decoder_release": other_name, "execution_error": f"{type(exc).__name__}: {exc}", "matched": False})
    metrics_ok = (all(complete_metrics(output.get(key)) for key in ("encode", "decode"))
                  and not any(key.endswith("_metric_error") for key in output))
    primary_ok = bool(source and phase_ok(output.get("encode_phase")) and phase_ok(output.get("decode_phase")) and restored.is_file()
                      and output.get("restored_sha256") == source_hash and restored.stat().st_size == row["input"]["bytes"])
    cross_ok = bool(output["cross_decode"]) and all(item.get("matched") for item in output["cross_decode"])
    affinity_ok = (affinity_set(output.get("encode_effective_affinity")) == sorted(cpus)
                   and affinity_set(output.get("decode_effective_affinity")) == sorted(cpus)
                   and all(affinity_set(item.get("effective_affinity")) == sorted(cpus) for item in output["cross_decode"]))
    cgroups_ok = (cgroup_ok(output.get("encode_effective_cgroup"), cpus, budget)
                   and cgroup_ok(output.get("decode_effective_cgroup"), cpus, budget)
                   and all(cgroup_ok(item.get("effective_cgroup"), cpus, budget) for item in output["cross_decode"]))
    output["status"] = "VERIFIED" if metrics_ok and primary_ok and cross_ok and affinity_ok and cgroups_ok else "UNQUALIFIED"
    if output["status"] == "VERIFIED":
        # This atomic checkpoint exists before any payload deletion.  A crash
        # can therefore resume/finalize the PRUNING receipt rather than leave
        # a blocked half-directory or claim an unrecorded measurement.
        output["status"] = "PRUNING"
        sealing = work / "sealing-receipt.json"
        write_json(sealing, {"schema": SCHEMA, "state": "PRUNING", "output": output})
        try:
            return finalize_pruning(work, output, archive, restored, sealing)
        except BaseException as exc:
            output["status"] = "UNQUALIFIED"
            output["sealing_error"] = f"{type(exc).__name__}: {exc}"
    output["finished_at"] = utc()
    write_json(result_path, output)
    return output


def gate_complete(destination: Path, rows: list[dict], releases: dict[str, dict]) -> bool:
    for row in rows:
        if row["stage"] != "gate":
            continue
        result = destination / "runs" / row["task_id"] / "result.json"
        if not result.is_file() or not verified_result(result, row, releases):
            return False
    return True


def run_dataset(destination: Path, dataset_rows: list[dict], releases: dict[str, dict], cpus: list[int], resource_limits: dict,
                cancelled: threading.Event, execution_identity: dict, preflight_identity: dict) -> list[dict]:
    """One dataset owns one CPU group; releases/repetitions remain serial."""
    results = []
    for row in dataset_rows:
        if cancelled.is_set():
            break
        path = destination / "runs" / row["task_id"] / "result.json"
        if path.is_file():
            prior = json.loads(path.read_text())
            if prior.get("status") == "VERIFIED":
                if not wave_completed(destination, prior.get("execution_identity", {})):
                    pass
                elif not verified_result(path, row, releases):
                    raise RuntimeError(f"invalid verified receipt blocks immutable resume: {path}")
                elif prior.get("execution_identity", {}).get("sha256") != execution_identity.get("sha256") or prior.get("cpu_set") != cpus:
                    raise RuntimeError(f"prior result uses a different CPU/resource execution identity: {path}")
                else:
                    results.append(prior)
                    continue
        budget = {**resource_limits, "wall_seconds": PROFILES[row["profile"]]["wall_seconds"]}
        result = run_one(destination, row, releases, cpus, budget, execution_identity, preflight_identity)
        results.append(result)
        if result["status"] != "VERIFIED":
            cancelled.set()
            raise RuntimeError(f"unqualified measurement: {row['task_id']}")
    return results


def stop_active_units(groups: list[list[dict]]) -> None:
    """Fail-stop every deterministic transient-unit name in active cohorts."""
    for group in groups:
        for row in group:
            prefix = f"cix-perf-{row['task_id']}"
            for suffix in ("encode", "decode", "cross-pre_refactor", "cross-current"):
                stop_unit(f"{prefix}-{suffix}")


def invalidate_wave_results(destination: Path, rows: list[dict], execution_sha: str, reason: str) -> None:
    """Do not leave a reusable VERIFIED row after postflight identity drift."""
    for row in rows:
        path = destination / "runs" / row["task_id"] / "result.json"
        if not path.is_file():
            continue
        value = json.loads(path.read_text())
        if value.get("status") == "VERIFIED" and value.get("execution_identity", {}).get("sha256") == execution_sha:
            value["status"] = "UNQUALIFIED"
            value["postflight_invalidation"] = reason
            write_json(path, value)


class LeaseGuard:
    def __init__(self, leases: list, wave_lock):
        self.leases, self.wave_lock = leases, wave_lock
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, traceback):
        for lease in self.leases:
            lease.close()
        self.wave_lock.close()
        return False


def run(args: argparse.Namespace) -> None:
    if not args.confirm_execution:
        raise RuntimeError("execution is intentionally explicit; pass --confirm-execution after reviewing the immutable plan")
    destination = AREA / args.id
    if args.jobs < 1 or args.jobs > 4 or args.rss_per_job * args.jobs > 12_000_000_000 or args.temp_per_job * args.jobs > 4_000_000_000:
        raise RuntimeError("jobs/resources exceed the 4-job, 12 GB RAM, 4 GB temporary global budget")
    # Acquire the shared scheduler lock before *any* input hashing, ldd call
    # or receipt revalidation.  These are deliberately excluded from timing,
    # but must not steal cache/memory bandwidth from another active wave.
    scheduler = WaveScheduler(ROOT, max_jobs=args.jobs, max_memory_bytes=args.rss_per_job * args.jobs,
                              max_temp_bytes=args.temp_per_job * args.jobs)
    scheduler.state.mkdir(parents=True, exist_ok=True)
    wave_lock = scheduler._wave_lock_path().open("a+")
    try:
        fcntl.flock(wave_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        wave_lock.close()
        raise RuntimeError("another WaveScheduler wave holds the aggregate resource budget") from exc
    plan, releases = validate_binding(destination, args.binding_sha)
    rows = [row for row in plan["rows"] if row["stage"] == args.stage and row["threads"] == args.threads]
    if not rows:
        raise RuntimeError(f"no {args.stage} rows in plan")
    if args.stage == "silesia" and not gate_complete(destination, plan["rows"], releases):
        raise RuntimeError("CCA gate is not completely VERIFIED; refusing Silesia")
    sets = cpu_sets(args.workers_per_dataset, args.jobs)
    if args.threads != args.workers_per_dataset:
        raise RuntimeError("--threads and --workers-per-dataset must agree; this avoids hidden oversubscription")
    # Hashing inputs, binaries and every resolved DSO is deliberately outside
    # the timed worker interval.  Running `ldd` or reading a Silesia member in
    # an unpinned sibling Python thread would contaminate FAST measurements.
    preflight_identity = preflight(rows, releases)
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["input"]["label"], []).append(row)
    ordered_labels = list(groups)
    lane_by_label = {label: index % args.jobs for index, label in enumerate(ordered_labels)}
    execution_identity = {"manifest_binding_sha256": args.binding_sha, "stage": args.stage, "threads": args.threads,
                          "jobs": args.jobs, "cpu_sets": sets, "dataset_lane": lane_by_label,
                          "max_rss_bytes_per_job": args.rss_per_job, "max_temp_bytes_per_job": args.temp_per_job, "swap_bytes": 0,
                          "timed_flags": "no --verbose", "scheduler": "WaveScheduler global lock and physical-core leases",
                          "sequential_preflight_sha256": preflight_identity["sha256"]}
    execution_sha = hashlib.sha256(canonical(execution_identity)).hexdigest()
    execution_identity["sha256"] = execution_sha
    execution_path = destination / "execution-bindings" / f"{execution_sha}.json"
    if execution_path.exists():
        if json.loads(execution_path.read_text()) != execution_identity:
            raise RuntimeError("execution binding collision")
    else:
        write_json(execution_path, execution_identity)
    def reusable(row: dict) -> bool:
        result = destination / "runs" / row["task_id"] / "result.json"
        if not result.is_file(): return False
        value = json.loads(result.read_text())
        # A cancelled/failed attempt is preserved under attempts/ when retried;
        # only an allegedly verified receipt can block an immutable resume.
        if value.get("status") != "VERIFIED":
            return False
        if not wave_completed(destination, value.get("execution_identity", {})):
            return False
        if not verified_result(result, row, releases):
            raise RuntimeError(f"invalid prior result blocks immutable resume: {result}")
        return value.get("execution_identity", {}).get("sha256") == execution_sha and value.get("cpu_set") == sets[lane_by_label[row["input"]["label"]]]
    pending_by_lane = {lane: [] for lane in range(args.jobs)}
    for label, group in groups.items():
        if any(not reusable(row) for row in group):
            pending_by_lane[lane_by_label[label]].append(group)
    pending = [group for lane in range(args.jobs) for group in pending_by_lane[lane]]
    if not pending:
        print(json.dumps({"status": "nothing-pending", "stage": args.stage}))
        wave_lock.close()
        return
    # A deterministic execution identity can have an old completion marker
    # while one or more rows still need retrying.  Remove it under the shared
    # lock before any new worker starts; only the postflight below may create
    # the marker that makes this wave's receipts reusable.
    (destination / "wave-completions" / f"{execution_sha}.json").unlink(missing_ok=True)
    resource_limits = {"max_rss_bytes": args.rss_per_job, "max_temp_bytes": args.temp_per_job}
    # Coordinate physical-core leases and the aggregate wave lock with the
    # existing scheduler. Its four-job maximum is the current user-authorized
    # 4 datasets x 4 threads policy, not an obsolete four-CPU cap.
    try:
        lease_plans = [{"physical_core": [_core(cpu) for cpu in group]} for group in sets]
        leases = scheduler._lease_cores(lease_plans)
    except BaseException:
        wave_lock.close()
        raise
    # Keep only ``jobs`` distinct datasets submitted. A failure must not leave
    # later fixtures running after evidence becomes unqualified.
    # A dataset has a permanent lane in this execution binding. A resumed
    # stage cannot silently measure the remaining repetitions on another core
    # cohort merely because an earlier cohort has already completed.
    lane_iterators = {lane: iter(groups) for lane, groups in pending_by_lane.items()}
    cancelled = threading.Event()
    active: dict[concurrent.futures.Future, tuple[int, list[dict]]] = {}
    with LeaseGuard(leases, wave_lock), concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        try:
            for index in range(args.jobs):
                try:
                    group = next(lane_iterators[index])
                except StopIteration:
                    continue
                active[pool.submit(run_dataset, destination, group, releases, sets[index], resource_limits, cancelled, execution_identity, preflight_identity)] = (index, group)
            while active:
                done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    index, current_group = active.pop(future)
                    results = future.result()
                    for result in results:
                        print(json.dumps({"task_id": result["task"]["task_id"], "status": result["status"], "archive_bytes": result["archive_bytes"]}, sort_keys=True), flush=True)
                    if any(result["status"] != "VERIFIED" for result in results):
                        raise RuntimeError("unqualified measurement retained; stop before continuing")
                    try:
                        next_group = next(lane_iterators[index])
                    except StopIteration:
                        continue
                    if not cancelled.is_set():
                        active[pool.submit(run_dataset, destination, next_group, releases, sets[index], resource_limits, cancelled, execution_identity, preflight_identity)] = (index, next_group)
            # Keep the shared lease while the postflight rehash establishes
            # that no input, release or DSO changed during the timed wave.
            postflight_identity = preflight(rows, releases)
            if postflight_identity != preflight_identity:
                invalidate_wave_results(destination, rows, execution_sha,
                                        "input, executable or runtime DSO changed during timed wave")
                raise RuntimeError("input, executable or runtime DSO changed during timed wave; receipts are invalid")
            write_json(destination / "wave-completions" / f"{execution_sha}.json", {
                "schema": SCHEMA, "status": "POSTFLIGHT_VERIFIED", "completed_at": utc(),
                "execution_identity": execution_identity,
                "preflight_sha256": preflight_identity["sha256"], "postflight_sha256": postflight_identity["sha256"],
            })
        except BaseException:
            cancelled.set()
            for queued in active:
                queued.cancel()
            stop_active_units([entry[1] for entry in active.values()])
            raise


@require_idle_wave
def collect(args: argparse.Namespace) -> None:
    destination = AREA / args.id
    plan, releases = validate_binding(destination, args.binding_sha)
    values = []
    for row in plan["rows"]:
        path = destination / "runs" / row["task_id"] / "result.json"
        if path.is_file():
            value = json.loads(path.read_text())
            value["revalidated"] = verified_result(path, row, releases)
            values.append(value)
    groups: dict[str, list[dict]] = {}
    for item in values:
        task = item["task"]
        key = "/".join((task["stage"], task["input"]["label"], task["release"], task["profile"], str(task["threads"]), item.get("execution_identity", {}).get("sha256", "invalid")))
        groups.setdefault(key, []).append(item)
    report = {"schema": SCHEMA, "collected_at": utc(), "plan": args.id, "completed": len(values), "planned": len(plan["rows"]),
              "revalidated": sum(bool(item.get("revalidated")) for item in values),
              "status": "COMPLETE" if len(values) == len(plan["rows"]) and all(item.get("revalidated") for item in values) else "INCOMPLETE_OR_UNQUALIFIED",
              "execution_identities": sorted({item.get("execution_identity", {}).get("sha256", "invalid") for item in values}), "groups": []}
    for key, group in sorted(groups.items()):
        verified = [item for item in group if item.get("revalidated")]
        report["groups"].append({"key": key, "runs": len(group), "verified": len(verified),
            "archive_bytes": sorted({item["archive_bytes"] for item in verified}),
            "archive_sha256": sorted({item["archive_sha256"] for item in verified}),
            "encode_wall_seconds": summary_stats([item["encode"]["wall_seconds"] for item in verified if "encode" in item]),
            "decode_wall_seconds": summary_stats([item["decode"]["wall_seconds"] for item in verified if "decode" in item]),
            "encode_cpu_seconds": summary_stats([item["encode"]["user_seconds"] + item["encode"]["system_seconds"] for item in verified if "encode" in item]),
            "decode_cpu_seconds": summary_stats([item["decode"]["user_seconds"] + item["decode"]["system_seconds"] for item in verified if "decode" in item]),
            "encode_peak_rss_bytes": summary_stats([item["encode"]["max_rss_bytes"] for item in verified if "encode" in item]),
            "decode_peak_rss_bytes": summary_stats([item["decode"]["max_rss_bytes"] for item in verified if "decode" in item]),
            "encode_sampled_cgroup_high_water_bytes": summary_stats([item.get("encode_phase", {}).get("sampled_cgroup_memory_high_water_bytes") for item in verified if item.get("encode_phase", {}).get("sampled_cgroup_memory_high_water_bytes") is not None]),
            "decode_sampled_cgroup_high_water_bytes": summary_stats([item.get("decode_phase", {}).get("sampled_cgroup_memory_high_water_bytes") for item in verified if item.get("decode_phase", {}).get("sampled_cgroup_memory_high_water_bytes") is not None]),
            "encode_throughput_bytes_per_second": summary_stats([item["task"]["input"]["bytes"] / item["encode"]["wall_seconds"] for item in verified if "encode" in item and item["encode"]["wall_seconds"] > 0]),
            "decode_throughput_bytes_per_second": summary_stats([item["task"]["input"]["bytes"] / item["decode"]["wall_seconds"] for item in verified if "decode" in item and item["decode"]["wall_seconds"] > 0]),
            "throughput_resolution_note": "GNU Time zero-wall samples are omitted from throughput; wrapper latency is separate.",
            "encode_zero_wall_samples": sum(item["encode"]["wall_seconds"] == 0 for item in verified if "encode" in item),
            "decode_zero_wall_samples": sum(item["decode"]["wall_seconds"] == 0 for item in verified if "decode" in item),
            "encode_wrapper_wall_nanoseconds": summary_stats([item.get("encode_phase", {}).get("wrapper_wall_nanoseconds") for item in verified if item.get("encode_phase", {}).get("wrapper_wall_nanoseconds") is not None]),
            "decode_wrapper_wall_nanoseconds": summary_stats([item.get("decode_phase", {}).get("wrapper_wall_nanoseconds") for item in verified if item.get("decode_phase", {}).get("wrapper_wall_nanoseconds") is not None])})
    write_json(destination / "results.json", report)
    print(json.dumps({"completed": len(values), "planned": len(plan["rows"]), "groups": len(report["groups"])}, sort_keys=True))


def profile_plan(args: argparse.Namespace) -> None:
    destination = AREA / args.id
    plan, releases = validate_binding(destination, args.binding_sha)
    row = next((value for value in plan["rows"] if value["task_id"] == args.task_id), None)
    if row is None:
        raise RuntimeError("--task-id is not in the immutable plan")
    execution_path = destination / "execution-bindings" / f"{args.execution_sha}.json"
    if not execution_path.is_file():
        raise RuntimeError("--execution-sha does not identify an immutable execution binding")
    execution = json.loads(execution_path.read_text())
    if (not valid_execution_identity(destination, execution) or execution.get("sha256") != args.execution_sha
            or execution.get("manifest_binding_sha256") != args.binding_sha or execution.get("stage") != row["stage"]
            or execution.get("threads") != row["threads"]):
        raise RuntimeError("execution binding belongs to a different manifest")
    release = releases[row["release"]]
    output = destination / "profiles" / row["task_id"] / "candidate.cix"
    command = " ".join([str(ROOT / release["binaries"]["cix"]["path"]), *row["flags"], "--threads", str(row["threads"]), "-f", "-o", str(output), str(ROOT / row["input"]["path"])])
    lane = execution.get("dataset_lane", {}).get(row["input"]["label"])
    if not isinstance(lane, int) or lane < 0 or lane >= len(execution.get("cpu_sets", [])):
        raise RuntimeError("execution binding lacks this task's CPU lane")
    cpu_set = ",".join(map(str, execution["cpu_sets"][lane]))
    value = {"schema": SCHEMA, "created_at": utc(), "plan": args.id, "status": "INSTRUCTIONS_ONLY_NOT_A_SCHEDULER_DISPATCH",
        "task": row, "execution_identity": execution,
        "preconditions": ["Complete one matched baseline group first.", "Create the recorded output directory before execution.", "Acquire the recorded WaveScheduler lock/core lease and cgroup budget through a reviewed profiling runner before executing any command.", "Do not compare a perf recording made while other benchmark jobs share its cores."],
        "output_parent": str(output.parent),
        "cpu_and_microarchitecture": [
            {"tool": "perf stat", "events": ["task-clock", "cycles", "instructions", "branches", "branch-misses", "cache-references", "cache-misses", "context-switches", "cpu-migrations"], "command": f"sudo -n perf stat -r 5 -e task-clock,cycles,instructions,branches,branch-misses,cache-references,cache-misses,context-switches,cpu-migrations -- taskset -c {cpu_set} {command}"},
            {"tool": "perf record/report", "purpose": "attribute CPU samples to CIX, Rust helpers and native libraries", "command": f"sudo -n perf record -g --call-graph dwarf -- taskset -c {cpu_set} {command}; sudo -n perf report"},
            {"tool": "perf lock", "purpose": "inspect lock contention only when context-switch or waiting evidence warrants it", "command": f"sudo -n perf lock record -- taskset -c {cpu_set} {command}; sudo -n perf lock report"}],
        "allocation": {"tool": "DHAT", "status": "available in the separately reviewed audit-only cix-dhat-audit feature branch; merge only after Sonar revision is final", "measure": ["allocation count", "allocated bytes", "peak live bytes", "allocation hot sites"]},
        "kernel_benchmarks": {"tool": "Criterion", "status": "available in the separately reviewed audit-only cix_hot_kernels branch; merge only after Sonar revision is final", "candidate_kernels": ["rank/composition per-symbol loop", "range/Huffman coding", "context model update", "match parsing", "block framing/checksum"], "command": "cargo bench --manifest-path FROZEN_SOURCE/rust/cix-native/Cargo.toml --bench cix_hot_kernels"},
        "assembly": {"tools": ["cargo asm", "cargo llvm-objdump"], "purpose": "inspect bounds checks, inlining and vectorization only at demonstrated hot kernels"},
        "build_matrix": [
            {"name": "portable-opt2-no-lto", "RUSTFLAGS": "-C opt-level=2 -C lto=off -C codegen-units=16 -C target-cpu=x86-64-v2"},
            {"name": "portable-opt3-thin-lto", "RUSTFLAGS": "-C opt-level=3 -C lto=thin -C codegen-units=1 -C target-cpu=x86-64-v2"},
            {"name": "portable-opt3-fat-lto", "RUSTFLAGS": "-C opt-level=3 -C lto=fat -C codegen-units=1 -C target-cpu=x86-64-v2"},
            {"name": "host-native-opt3-fat-lto", "RUSTFLAGS": "-C opt-level=3 -C lto=fat -C codegen-units=1 -C target-cpu=native", "deployment": "host-only; keep portable build separately"},
            {"name": "pgo", "command": "instrument on development fixtures, merge profraw, rebuild with profile-use, then evaluate only held-out frozen fixtures", "guard": "record training/evaluation fixture hashes and never use same fixture in both"}],
        "acceptance": ["fresh native exact decode SHA-256 for every retained build", "no archive-size regression unless explicitly accepted", "repeat wall/CPU/RSS measurement with variance", "portable and host-native artifacts labelled separately", "re-run malformed/truncation and deterministic-format tests after code changes"]}
    write_json(destination / "profiling-plan.json", value)
    print(json.dumps({"written": rel(destination / "profiling-plan.json"), "planned_rows": len(plan["rows"])}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    p = sub.add_parser("prepare", help="freeze releases, fixtures and a non-executing audit matrix")
    p.add_argument("--id", required=True); p.add_argument("--before", type=Path, required=True); p.add_argument("--current", type=Path, required=True)
    p.add_argument("--profiles", default="fast,default,best"); p.add_argument("--threads", default="1,2,4,8,12,16,20")
    p.add_argument("--repetitions", type=int, default=5); p.add_argument("--include-silesia", action="store_true")
    r = sub.add_parser("run", help="explicitly run one stage of a reviewed immutable plan")
    r.add_argument("--id", required=True); r.add_argument("--stage", choices=("gate", "silesia"), required=True)
    r.add_argument("--workers-per-dataset", type=int, default=4); r.add_argument("--threads", type=int, default=4); r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--rss-per-job", type=int, default=3_000_000_000); r.add_argument("--temp-per-job", type=int, default=1_000_000_000)
    r.add_argument("--binding-sha", required=True); r.add_argument("--confirm-execution", action="store_true")
    c = sub.add_parser("collect", help="derive size/time/CPU/RSS variance summaries")
    c.add_argument("--id", required=True); c.add_argument("--binding-sha", required=True)
    q = sub.add_parser("profile-plan", help="write exact perf/DHAT/Criterion/build comparison queue")
    q.add_argument("--id", required=True); q.add_argument("--binding-sha", required=True); q.add_argument("--task-id", required=True); q.add_argument("--execution-sha", required=True)
    args = parser.parse_args()
    if args.operation == "prepare":
        if args.repetitions < 2: raise RuntimeError("at least two repetitions are required for a variance claim")
        prepare(args)
    elif args.operation == "run": run(args)
    elif args.operation == "collect": collect(args)
    else: profile_plan(args)


if __name__ == "__main__":
    main()
