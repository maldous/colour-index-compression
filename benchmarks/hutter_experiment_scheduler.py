"""Guarded, declarative wave dispatch for bounded Hutter experiments.

The existing bounded runner remains the only experiment harness.  This module
only claims matrix cells, checks aggregate capacity, leases physical cores, and
launches that runner under ``taskset``.
"""
from __future__ import annotations

import concurrent.futures
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.hutter_bounded_runner import build_identity, load_manifest

GIB = 1024 ** 3
CELL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _available_memory():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")


def _core(cpu):
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
    try:
        return (int((base / "physical_package_id").read_text()), int((base / "core_id").read_text()))
    except (OSError, ValueError):
        return (0, cpu)


class WaveScheduler:
    """A four-lane scheduler that never retries claimed cells."""

    def __init__(self, root, *, max_jobs=4, max_memory_bytes=12_000_000_000,
                 max_temp_bytes=4_000_000_000, min_free_disk_bytes=10 * GIB,
                 runner_command=None, taskset_command="taskset", progress_seconds=30.0):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError("scheduler root must exist")
        if not isinstance(max_jobs, int) or not 1 <= max_jobs <= 4:
            raise ValueError("max_jobs must be 1..4")
        if min(max_memory_bytes, max_temp_bytes, min_free_disk_bytes) < 1:
            raise ValueError("scheduler limits must be positive")
        self.max_jobs, self.max_memory_bytes = max_jobs, int(max_memory_bytes)
        self.max_temp_bytes, self.min_free_disk_bytes = int(max_temp_bytes), int(min_free_disk_bytes)
        self.runner_command = tuple(runner_command or (sys.executable, str(self.root / "benchmarks/hutter_bounded_runner.py")))
        self.taskset_command, self.progress_seconds = taskset_command, float(progress_seconds)
        self.state = self.root / ".hutter-experiment-scheduler"
        self.claims, self.core_locks = self.state / "claims", self.state / "physical-core-leases"

    def _under_root(self, value, what):
        path = Path(value).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError(f"{what} must be under scheduler root")
        return path

    def _claim_path(self, cell_id):
        return self.claims / f"{cell_id}.claim.json"

    def _terminal_path(self, cell_id):
        return self.claims / f"{cell_id}.terminal.json"

    def _wave_lock_path(self):
        return self.state / "wave.lock"

    def _plan(self, cell):
        fields = ("cell_id", "owner", "manifest_path", "output_dir", "expected_manifest_sha256")
        if not isinstance(cell, dict) or any(field not in cell for field in fields):
            raise ValueError("cell requires cell_id, owner, manifest_path, output_dir, expected_manifest_sha256")
        if not isinstance(cell["cell_id"], str) or not CELL_ID.fullmatch(cell["cell_id"]):
            raise ValueError("invalid cell_id")
        if not isinstance(cell["owner"], str) or not cell["owner"].strip():
            raise ValueError("cell owner must be non-empty")
        manifest_path = self._under_root(cell["manifest_path"], "manifest_path")
        output_dir = self._under_root(cell["output_dir"], "output_dir")
        if not manifest_path.is_file():
            raise ValueError("manifest_path does not exist")
        manifest, manifest_sha = load_manifest(manifest_path)
        if cell["expected_manifest_sha256"] != manifest_sha:
            raise ValueError("expected_manifest_sha256 does not match immutable manifest")
        expected_build = cell.get("expected_build_sha256")
        if expected_build is not None:
            if not isinstance(expected_build, dict):
                raise ValueError("expected_build_sha256 must be a build-path hash map")
            actual_build = build_identity(manifest, self.root)
            if expected_build != actual_build:
                raise ValueError("expected_build_sha256 does not match current declared build")
        else:
            actual_build = None
        budget = manifest["budget"]
        cpus = budget["cpu"] if isinstance(budget["cpu"], list) else [budget["cpu"]]
        cpus = [int(cpu) for cpu in cpus]
        if not cpus or len(set(cpus)) != len(cpus):
            raise ValueError("manifest CPU list must be non-empty and unique")
        memory, temp = int(budget["max_rss_bytes"]), int(budget["max_temp_bytes"])
        cpu = cpus[0] if len(cpus) == 1 else cpus
        if cell.get("cpu", cpu) != cpu:
            raise ValueError("cell CPU must match immutable manifest budget")
        unavailable = set(cpus) - os.sched_getaffinity(0)
        if unavailable:
            raise ValueError(f"manifest CPUs {sorted(unavailable)} are unavailable")
        cores = [_core(cpu) for cpu in cpus]
        if len(set(cores)) != len(cores):
            raise ValueError("a cell cannot lease multiple logical CPUs from one physical core")
        if memory < 1 or temp < 1:
            raise ValueError("manifest resource limits must be positive")
        return dict(cell_id=cell["cell_id"], owner=cell["owner"], manifest_path=manifest_path,
                    output_dir=output_dir, manifest=manifest, manifest_sha256=manifest_sha, cpu=cpu,
                    physical_core=cores, memory=memory, temp=temp,
                    fresh_justification=cell.get("fresh_justification"), build_sha256=actual_build)

    def _validate(self, cells):
        if not isinstance(cells, list) or not cells:
            raise ValueError("cells must be a non-empty list")
        if len(cells) > self.max_jobs:
            raise ValueError("wave exceeds max_jobs")
        plans = [self._plan(cell) for cell in cells]
        if len({plan["cell_id"] for plan in plans}) != len(plans):
            raise ValueError("wave has duplicate cell IDs")
        leased_cores = [core for plan in plans for core in plan["physical_core"]]
        if len(set(leased_cores)) != len(leased_cores):
            raise ValueError("wave has overlapping physical CPU cores")
        memory, temp = sum(plan["memory"] for plan in plans), sum(plan["temp"] for plan in plans)
        if memory > self.max_memory_bytes or temp > self.max_temp_bytes:
            raise ValueError("wave exceeds scheduler aggregate resource budget")
        if _available_memory() < memory:
            raise RuntimeError("insufficient currently available RAM for planned wave")
        if shutil.disk_usage(self.root).free < self.min_free_disk_bytes + temp:
            raise RuntimeError("insufficient free disk after reserved minimum and planned temp budget")
        return plans

    def _same_manifest_claim_exists(self, manifest_sha):
        if not self.claims.exists():
            return False
        for claim in self.claims.glob("*.claim.json"):
            try:
                if json.loads(claim.read_text()).get("manifest_sha256") == manifest_sha:
                    return True
            except (OSError, json.JSONDecodeError):
                continue
        return False

    def _same_output_claim_exists(self, output_dir):
        if not self.claims.exists():
            return False
        for claim in self.claims.glob("*.claim.json"):
            try:
                if json.loads(claim.read_text()).get("output_dir") == str(output_dir):
                    return True
            except (OSError, json.JSONDecodeError):
                continue
        return False

    @staticmethod
    def _claim_identity(plan):
        return {"cell_id": plan["cell_id"], "owner": plan["owner"],
                "manifest_path": str(plan["manifest_path"]), "manifest_sha256": plan["manifest_sha256"],
                "output_dir": str(plan["output_dir"]), "cpu": plan["cpu"],
                "physical_core": list(plan["physical_core"]), "build_sha256": plan["build_sha256"]}

    def _verified_receipt(self, receipt_path, plan):
        """Rehash a bounded-runner receipt and both physical artifacts."""
        try:
            receipt = json.loads(Path(receipt_path).read_text())
            identity, verification, artifacts = receipt["identity"], receipt["verification"], receipt["artifacts"]
            archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
            input_identity = identity["input"]
            if (receipt["status"] != "VERIFIED_SCREENING" or not verification["matched"]
                    or identity["manifest_sha256"] != plan["manifest_sha256"]
                    or verification["source_sha256"] != input_identity["sha256"]
                    or verification["restored_sha256"] != input_identity["sha256"]
                    or not archive.is_file() or not restored.is_file()
                    or archive.stat().st_size != receipt["archive_bytes"]
                    or restored.stat().st_size != input_identity["length"]):
                return False
            return receipt["archive_sha256"] == _sha256(archive) and input_identity["sha256"] == _sha256(restored)
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return False

    def _claim(self, plan):
        self.claims.mkdir(parents=True, exist_ok=True)
        lock_path = self.claims / f"{plan['cell_id']}.lock"
        with lock_path.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            claim, terminal = self._claim_path(plan["cell_id"]), self._terminal_path(plan["cell_id"])
            if claim.exists():
                stored = json.loads(claim.read_text())
                if any(stored.get(key) != value for key, value in self._claim_identity(plan).items()):
                    raise ValueError("existing cell_id has a different immutable claim identity")
                if not terminal.exists():
                    raise RuntimeError("cell is already claimed and running or incomplete; never auto-restart")
                row = json.loads(terminal.read_text())
                runner_result = row.get("runner_result", {})
                receipt = runner_result.get("receipt") if isinstance(runner_result, dict) else None
                if row.get("runner_status") in ("VERIFIED_SCREENING", "REUSED_VERIFIED") and receipt and self._verified_receipt(receipt, plan):
                    return {"cell_id": plan["cell_id"], "status": "REUSED_VERIFIED", "terminal": str(terminal)}
                if row.get("runner_status") in ("VERIFIED_SCREENING", "REUSED_VERIFIED"):
                    raise RuntimeError("claimed verified result cannot be rehashed from its bounded-runner receipt")
                return {"cell_id": plan["cell_id"], "status": "TERMINAL_NEGATIVE", "terminal": str(terminal)}
            if self._same_manifest_claim_exists(plan["manifest_sha256"]) and not (isinstance(plan["fresh_justification"], str) and plan["fresh_justification"].strip()):
                raise ValueError("a new cell_id with an existing manifest requires fresh_justification")
            if self._same_output_claim_exists(plan["output_dir"]):
                raise ValueError("new cell must use a unique output_dir")
            row = {"schema": 1, "claimed_at": _now(), **self._claim_identity(plan),
                   "resource_budget": {"max_rss_bytes": plan["memory"], "max_temp_bytes": plan["temp"]},
                   "fresh_justification": plan["fresh_justification"]}
            with claim.open("x") as stream:
                stream.write(_canonical(row).decode() + "\n")
        return None

    def _terminal(self, plan, row):
        with self._terminal_path(plan["cell_id"]).open("x") as stream:
            stream.write(_canonical(row).decode() + "\n")

    def _lease_cores(self, plans):
        self.core_locks.mkdir(parents=True, exist_ok=True)
        handles = []
        try:
            for plan in plans:
                for package, core in plan["physical_core"]:
                    handle = (self.core_locks / f"package-{package}-core-{core}.lock").open("a+")
                    try:
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError as error:
                        handle.close(); raise RuntimeError(f"physical core {package}:{core} is already leased") from error
                    handles.append(handle)
            return handles
        except BaseException:
            for handle in handles: handle.close()
            raise

    def _command(self, plan):
        cpus = plan["cpu"] if isinstance(plan["cpu"], list) else [plan["cpu"]]
        return [self.taskset_command, "-c", ",".join(map(str, cpus)), *self.runner_command,
                "--manifest", str(plan["manifest_path"]), "--results", str(plan["output_dir"]), "--root", str(self.root)]

    def _run(self, plan):
        plan["output_dir"].mkdir(parents=True, exist_ok=True)
        logs = plan["output_dir"] / "scheduler-logs"; logs.mkdir(parents=True, exist_ok=True)
        stdout, progress = logs / f"{plan['cell_id']}.stdout.log", logs / f"{plan['cell_id']}.progress.jsonl"
        command, started = self._command(plan), time.monotonic()
        try:
            with progress.open("x") as stream:
                stream.write(_canonical({"at": _now(), "cell_id": plan["cell_id"], "state": "DISPATCHED", "cpu": plan["cpu"], "host_available_memory_bytes": _available_memory(), "free_disk_bytes": shutil.disk_usage(self.root).free}).decode()+"\n")
            with stdout.open("x") as output:
                process = subprocess.Popen(command, cwd=self.root, stdout=output, stderr=subprocess.STDOUT, text=True)
                next_progress = started
                while process.poll() is None:
                    now = time.monotonic()
                    if now >= next_progress:
                        with progress.open("a") as stream:
                            stream.write(_canonical({"at": _now(), "cell_id": plan["cell_id"], "state": "RUNNING", "cpu": plan["cpu"], "elapsed_seconds": now-started, "host_available_memory_bytes": _available_memory(), "free_disk_bytes": shutil.disk_usage(self.root).free}).decode()+"\n")
                        next_progress = now + self.progress_seconds
                    time.sleep(0.05)
                code = process.wait()
            rows = [json.loads(line) for line in stdout.read_text().splitlines() if line.startswith("{")]
            runner_result = rows[-1] if rows else {}
            status = runner_result.get("status", "RUNNER_NO_TERMINAL_JSON")
            error = None
        except BaseException as exc:
            code, status, error = 1, "DISPATCH_FAILED", f"{type(exc).__name__}: {exc}"
        row = {"cell_id": plan["cell_id"], "owner": plan["owner"], "manifest_sha256": plan["manifest_sha256"], "cpu": plan["cpu"], "physical_core": list(plan["physical_core"]), "command": command, "stdout_log": str(stdout), "progress_log": str(progress), "returncode": code, "runner_status": status, "runner_result": locals().get("runner_result", {}), "ended_at": _now(), "elapsed_seconds": time.monotonic()-started}
        if error: row["dispatch_error"] = error
        return row

    def run_wave(self, cells):
        self.state.mkdir(parents=True, exist_ok=True)
        wave_lock = self._wave_lock_path().open("a+")
        try:
            try:
                fcntl.flock(wave_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("another scheduler wave holds the global aggregate budget") from error
            plans = self._validate(cells)
            reusable, launch = [], []
            # All ownership claims precede directory creation and process launch.
            for plan in plans:
                existing = self._claim(plan)
                (reusable if existing else launch).append(existing or plan)
            if not launch: return reusable
            try:
                leases = self._lease_cores(launch)
            except BaseException as exc:
                rows = []
                for plan in launch:
                    row = {"cell_id": plan["cell_id"], "owner": plan["owner"], "manifest_sha256": plan["manifest_sha256"], "runner_status": "DISPATCH_BLOCKED", "returncode": 1, "ended_at": _now(), "dispatch_error": f"{type(exc).__name__}: {exc}"}
                    self._terminal(plan, row); rows.append(row)
                return reusable + rows
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=len(launch)) as pool:
                    futures = {pool.submit(self._run, plan): plan for plan in launch}
                    rows = []
                    for future in concurrent.futures.as_completed(futures):
                        plan, row = futures[future], future.result()
                        self._terminal(plan, row); rows.append(row)
            finally:
                for lease in leases: lease.close()
            return reusable + sorted(rows, key=lambda row: row["cell_id"])
        finally:
            wave_lock.close()


def run_wave(cells, *, root, **limits):
    return WaveScheduler(root, **limits).run_wave(cells)
