#!/usr/bin/env python3
"""Prepare and, only after an explicit qualified-release freeze, run CIX hotspot profiles.

``prepare`` is deliberately non-executing.  It binds one existing CCA plan row,
an immutable native release and CPU 8 (P) / CPU 16 (E) command vectors.  ``run``
requires both ``--execute`` and a reviewed qualified-release freeze plus a
scheduler lease receipt; it never creates an independent worker pool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cix-hotspot-audit-v1"
EVENTS = ("cycles", "instructions", "cache-misses", "branch-misses", "context-switches", "cpu-migrations")
CPU_PROFILES = ((8, "P"), (16, "E"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def absolute_from_root(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def executable_tool(name: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    result: dict[str, Any] = {"tool": name, "path": resolved, "available": bool(resolved)}
    if resolved:
        p = Path(resolved).resolve()
        result.update({"path": str(p), "sha256": digest(p)})
        probe = subprocess.run([str(p), "--version"], text=True, capture_output=True, check=False)
        result["version_exit"] = probe.returncode
        result["version"] = (probe.stdout or probe.stderr).splitlines()[:1]
    return result


def cpu_info(cpu: int, kind: str) -> dict[str, Any]:
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}")
    available = base.exists() and cpu in os.sched_getaffinity(0)
    def read(relative: str) -> str | None:
        try:
            return (base / relative).read_text().strip()
        except OSError:
            return None
    return {"cpu": cpu, "declared_class": kind, "available_to_runner": available, "online": read("online"),
            "package": read("topology/physical_package_id"), "core": read("topology/core_id"),
            "siblings": read("topology/thread_siblings_list"), "capacity": read("cpu_capacity"),
            "max_frequency_khz": read("cpufreq/cpuinfo_max_freq")}


def release_binding(release: Path) -> dict[str, Any]:
    meta = release / "native-release.json"
    value = load_json(meta)
    revision = value.get("source_revision")
    if not isinstance(revision, str) or len(revision) != 40:
        raise RuntimeError("release native-release.json has no exact source_revision")
    binaries: dict[str, Any] = {}
    for name in ("cix", "uncix"):
        path = release / name
        expected = value.get("binaries", {}).get(name, {}).get("sha256")
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"missing executable: {path}")
        actual = digest(path)
        if actual != expected:
            raise RuntimeError(f"release binary differs from metadata: {path}")
        binaries[name] = {"path": str(path.resolve()), "sha256": actual, "bytes": path.stat().st_size}
    return {"directory": str(release.resolve()), "metadata": str(meta.resolve()), "metadata_sha256": digest(meta),
            "source_revision": revision, "binaries": binaries}


def select_plan_row(plan_path: Path, task_id: str) -> dict[str, Any]:
    plan = load_json(plan_path)
    rows = plan.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError("CCA plan has no rows")
    row = next((x for x in rows if isinstance(x, dict) and x.get("task_id") == task_id), None)
    if row is None:
        raise RuntimeError("--task-id is not in the supplied immutable CCA plan")
    inp = row.get("input", {})
    path = absolute_from_root(inp.get("path", "")) if isinstance(inp, dict) else Path()
    if not path.is_file():
        raise RuntimeError("CCA task input is unavailable")
    if digest(path) != inp.get("sha256") or path.stat().st_size != inp.get("bytes"):
        raise RuntimeError("CCA task input differs from its immutable plan identity")
    return {"plan": str(plan_path.resolve()), "plan_sha256": digest(plan_path), "row": row,
            "input_path": str(path.resolve())}


def profilers() -> dict[str, Any]:
    answer = {name: executable_tool(name) for name in ("perf", "taskset", "systemd-run", "strace", "cargo", "rustc")}
    try:
        answer["perf_event_paranoid"] = Path("/proc/sys/kernel/perf_event_paranoid").read_text().strip()
    except OSError as e:
        answer["perf_event_paranoid"] = {"unavailable": str(e)}
    answer["dhat"] = {"status": "requires separately built audit-dhat artifact; this runner does not rebuild or profile dirty source"}
    answer["assembly"] = {"cargo_asm": executable_tool("cargo-asm"), "llvm_objdump": executable_tool("llvm-objdump"),
                           "status": "inspect only a hotspot established by perf; no assembly claim is generated here"}
    return answer


def command_vectors(binding: dict[str, Any], cpu: int, kind: str, output: Path) -> dict[str, list[str]]:
    row, release = binding["task"], binding["release"]
    inp = binding["task"]["input"]
    archive = output / f"cpu{cpu}-{kind}.cix"
    cix = release["binaries"]["cix"]["path"]
    payload = [cix, *row.get("flags", []), "--threads", str(row.get("threads", 1)), "-f", "-o", str(archive), inp["path"]]
    pin = ["/usr/bin/taskset", "-c", str(cpu)]
    # Pin perf itself before it opens counters: do not pin only its child.
    stat = [*pin, "/usr/bin/perf", "stat", "--no-big-num", "--field-separator", ",",
            "--output", str(output / f"cpu{cpu}-{kind}.stat.csv"), "-e", ",".join(EVENTS), "--", *payload]
    record = [*pin, "/usr/bin/perf", "record", "--call-graph", "dwarf", "--output", str(output / f"cpu{cpu}-{kind}.data"), "--", *payload]
    lock = [*pin, "/usr/bin/perf", "lock", "record", "--output", str(output / f"cpu{cpu}-{kind}.lock.data"), "--", *payload]
    io = [*pin, "/usr/bin/strace", "-ff", "-c", "-o", str(output / f"cpu{cpu}-{kind}.strace"), "--", *payload]
    return {"workload": payload, "perf_stat": stat, "perf_record": record, "perf_lock": lock, "strace_io": io}


def prepare(args: argparse.Namespace) -> None:
    dest = Path(args.output).resolve()
    if dest.exists():
        raise RuntimeError("refusing to overwrite an existing preflight directory")
    plan = select_plan_row(Path(args.cca_plan).resolve(), args.task_id)
    release = release_binding(Path(args.release).resolve())
    row = plan["row"]
    task = {"task_id": row["task_id"], "profile": row.get("profile"), "flags": row.get("flags", []),
            "threads": row.get("threads", 1), "input": {**row["input"], "path": plan["input_path"]}}
    payload = {"schema": SCHEMA, "status": "PREPARED_NOT_EXECUTED_AWAITING_QUALIFIED_RELEASE_FREEZE",
               "created_at": now(), "task": task, "cca_plan": {"path": plan["plan"], "sha256": plan["plan_sha256"]},
               "release": release, "cpu_profiles": [], "events": list(EVENTS), "tools": profilers(),
               "execution_guards": ["requires --execute", "requires a qualified-release freeze matching release metadata and binary hashes",
                 "requires a reviewed existing WaveScheduler lease receipt; this runner creates no scheduler or worker pool",
                 "runs one CPU profile at a time", "records actual child cgroup/resource readback before accepting results"],
               "metric_limits": {"lock": "perf lock is conditional; unsupported/permitted failures are recorded as unavailable",
                 "io": "strace syscall summary is optional I/O attribution, not CPU attribution", "dhat": "not measured without separately frozen audit artifact",
                 "assembly": "not measured without a demonstrated perf hotspot"}}
    for cpu, kind in CPU_PROFILES:
        payload["cpu_profiles"].append({"cpu": cpu_info(cpu, kind), "commands": command_vectors({"task": task, "release": release}, cpu, kind, dest / "raw")})
    write_json(dest / "preflight.json", payload)
    print(json.dumps({"status": payload["status"], "written": str(dest / "preflight.json")}, sort_keys=True))


def verify_freeze(path: Path, preflight: dict[str, Any]) -> dict[str, Any]:
    value = load_json(path)
    if value.get("status") != "QUALIFIED_RELEASE_FROZEN" or value.get("release") != preflight["release"]:
        raise RuntimeError("freeze is not a qualified exact release binding")
    return value



def physical_core(cpu: int) -> dict[str, str]:
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
    try:
        return {"package": (base / "physical_package_id").read_text().strip(), "core": (base / "core_id").read_text().strip()}
    except OSError as error:
        raise RuntimeError(f"cannot establish physical-core identity for CPU {cpu}: {error}") from error


def preflight_sha256(preflight: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(preflight, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_lease(lease: dict[str, Any], preflight: dict[str, Any]) -> None:
    """Require an active scheduler claim specifically authorising these profiles.

    A merely active unrelated lease cannot grant use of CPU 8/16.  This strict
    schema is intentional: older generic receipts are insufficient authority.
    """
    if lease.get("status") != "ACTIVE" or lease.get("scheduler", {}).get("status") != "ACTIVE":
        raise RuntimeError("scheduler lease and scheduler claim must both be ACTIVE")
    if lease.get("preflight_sha256") != preflight_sha256(preflight):
        raise RuntimeError("scheduler lease belongs to a different hotspot preflight")
    if lease.get("task_id") != preflight.get("task", {}).get("task_id") or lease.get("release") != preflight.get("release"):
        raise RuntimeError("scheduler lease task or release does not match preflight")
    requested = [int(profile["cpu"]["cpu"]) for profile in preflight.get("cpu_profiles", [])]
    granted = lease.get("cpus")
    if not isinstance(granted, list) or sorted(granted) != sorted(requested) or any(type(cpu) is not int for cpu in granted):
        raise RuntimeError("scheduler lease does not exactly cover the selected CPUs")
    cores = lease.get("physical_cores")
    expected_cores = [physical_core(cpu) for cpu in requested]
    if not isinstance(cores, list) or sorted(cores, key=lambda x: (x.get("package", ""), x.get("core", ""))) != sorted(expected_cores, key=lambda x: (x["package"], x["core"])):
        raise RuntimeError("scheduler lease physical-core ownership does not match selected CPUs")
    if len({(core["package"], core["core"]) for core in expected_cores}) != len(expected_cores):
        raise RuntimeError("selected CPUs are not distinct physical cores")
    resources = lease.get("resources")
    if not isinstance(resources, dict) or resources.get("memory_max_bytes") != 1_073_741_824 or resources.get("swap_max_bytes") != 0:
        raise RuntimeError("scheduler lease does not authorise the required per-profile memory/no-swap budget")
    if resources.get("aggregate_memory_reserved_bytes", 12_000_000_001) > 12_000_000_000 or resources.get("aggregate_swap_bytes") != 0:
        raise RuntimeError("scheduler lease aggregate memory/swap budget is invalid")
    phases = lease.get("allowed_phases")
    needed = {"perf_stat", "perf_record", "perf_lock", "strace_io"}
    if not isinstance(phases, list) or not needed.issubset(phases):
        raise RuntimeError("scheduler lease does not authorise every requested profiling phase")
    claim_path = lease.get("active_claim_path")
    claim_sha = lease.get("active_claim_sha256")
    if not isinstance(claim_path, str) or not isinstance(claim_sha, str):
        raise RuntimeError("scheduler lease has no active claim identity")
    claim = Path(claim_path)
    if not claim.is_file() or digest(claim) != claim_sha:
        raise RuntimeError("scheduler active claim is absent or changed")
    claim_value = load_json(claim)
    claim_id = lease.get("claim_id")
    if (not isinstance(claim_id, str) or lease.get("scheduler", {}).get("active_claim_id") != claim_id
            or claim_value.get("claim_id") != claim_id or claim_value.get("status") != "ACTIVE"
            or claim_value.get("preflight_sha256") != lease["preflight_sha256"]):
        raise RuntimeError("scheduler active claim does not bind this preflight")

def run_phase(raw: Path, cpu: int, kind: str, name: str, command: list[str]) -> dict[str, Any]:
    """Run one profiler below a named cgroup and retain pre/post child readbacks.

    The command is stored as an argv list and passed after ``--``.  The shell
    wrapper invokes ``"$@"`` so paths or fixture names cannot become shell code.
    A profiler permission failure is a retained unavailable metric, not success.
    """
    stem = f"cpu{cpu}-{kind}-{name}"
    receipt, log, wrapper = raw / f"{stem}.resources.raw", raw / f"{stem}.log", raw / f"{stem}.sh"
    cix_path = command[command.index("--") + 1] if "--" in command else ""
    wrapper.write_text("""#!/bin/sh
set -u
receipt="$1"; cix="$2"; shift 2
cg=$(awk -F: '$1 == "0" { print $3; exit }' /proc/self/cgroup)
printf 'pid=%s\ncgroup=%s\n' "$$" "$cg" > "$receipt"
for key in memory.current memory.peak memory.max memory.swap.current memory.swap.max; do
  printf '%s=' "$key" >> "$receipt"
  cat "/sys/fs/cgroup$cg/$key" >> "$receipt" 2>&1 || printf 'UNAVAILABLE\n' >> "$receipt"
done
"$@" & profiler=$!; observed=0
while kill -0 "$profiler" 2>/dev/null; do
  frontier="$profiler"
  while [ -n "$frontier" ]; do
    next=""
    for child in $(pgrep -P "$frontier" 2>/dev/null || true); do
      next="$next $child"
      if [ "$(readlink -f "/proc/$child/exe" 2>/dev/null || true)" = "$cix" ]; then
        observed=1
        printf 'cix_pid=%s\n' "$child" >> "$receipt"
        printf 'cix_cgroup=' >> "$receipt"; cat "/proc/$child/cgroup" >> "$receipt" 2>&1 || true
        printf 'cix_affinity=' >> "$receipt"; taskset -pc "$child" >> "$receipt" 2>&1 || true
      fi
    done
    frontier="$next"
  done
  sleep 0.02
done
wait "$profiler"; code=$?
printf 'cix_observed=%s\nexit_code=%s\n' "$observed" "$code" >> "$receipt"
if [ "$observed" -ne 1 ] && [ "$code" -eq 0 ]; then code=125; fi
for key in memory.current memory.peak memory.max memory.swap.current memory.swap.max; do
  printf 'post_%s=' "$key" >> "$receipt"
  cat "/sys/fs/cgroup$cg/$key" >> "$receipt" 2>&1 || printf 'UNAVAILABLE\n' >> "$receipt"
done
exit "$code"
""")
    wrapper.chmod(0o700)
    unit = f"cix-hotspot-{cpu}-{name}-{os.getpid()}"
    launcher = ["/usr/bin/systemd-run", "--user", "--wait", "--pipe", f"--unit={unit}",
                f"--property=CPUAffinity={cpu}", "--property=MemoryMax=1G", "--property=MemorySwapMax=0",
                "--", "/bin/sh", str(wrapper), str(receipt), cix_path, *command]
    completed = subprocess.run(launcher, text=True, capture_output=True, check=False)
    log.write_text("launcher=" + shlex.join(launcher) + "\nstdout:\n" + completed.stdout + "\nstderr:\n" + completed.stderr)
    status = "MEASURED" if completed.returncode == 0 else "UNAVAILABLE_OR_FAILED"
    return {"cpu": cpu, "class": kind, "phase": name, "status": status, "exit_code": completed.returncode,
            "resource_scope": "aggregate profiler plus its CIX child cgroup; not CIX-only RSS", "cix_observation_required": True,
            "command": command, "launcher": launcher, "log": str(log), "resource_receipt": str(receipt) if receipt.exists() else None,
            "log_sha256": digest(log), "resource_sha256": digest(receipt) if receipt.exists() else None}


def run(args: argparse.Namespace) -> None:
    if not args.execute:
        raise RuntimeError("run requires --execute; use prepare for dry-run metadata")
    dest = Path(args.output).resolve(); preflight = load_json(dest / "preflight.json")
    if preflight.get("status") != "PREPARED_NOT_EXECUTED_AWAITING_QUALIFIED_RELEASE_FREEZE":
        raise RuntimeError("preflight is not runnable")
    verify_freeze(Path(args.freeze).resolve(), preflight)
    lease = load_json(Path(args.scheduler_lease).resolve())
    validate_lease(lease, preflight)
    raw = dest / "raw"; raw.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"schema": SCHEMA, "started_at": now(), "status": "COMPLETE_WITH_UNAVAILABLE_METRICS", "freeze": str(Path(args.freeze).resolve()), "lease": str(Path(args.scheduler_lease).resolve()), "phases": []}
    for profile in preflight["cpu_profiles"]:
        info = profile["cpu"]
        if not info.get("available_to_runner"):
            result["phases"].append({"cpu": info["cpu"], "class": info["declared_class"], "status": "UNAVAILABLE_CPU"})
            continue
        for name in ("perf_stat", "perf_record", "perf_lock", "strace_io"):
            tool = "strace" if name == "strace_io" else "perf"
            if not preflight["tools"].get(tool, {}).get("available"):
                result["phases"].append({"cpu": info["cpu"], "class": info["declared_class"], "phase": name, "status": "TOOL_UNAVAILABLE"})
                continue
            result["phases"].append(run_phase(raw, int(info["cpu"]), str(info["declared_class"]), name, profile["commands"][name]))
    result["finished_at"] = now()
    write_json(dest / "run-result.json", result)
    print(json.dumps({"status": result["status"], "phases": len(result["phases"])}, sort_keys=True))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="op", required=True)
    prep = sub.add_parser("prepare", help="bind immutable release/input and write commands only")
    prep.add_argument("--release", required=True); prep.add_argument("--cca-plan", required=True); prep.add_argument("--task-id", required=True); prep.add_argument("--output", required=True)
    runp = sub.add_parser("run", help="guarded future execution")
    runp.add_argument("--output", required=True); runp.add_argument("--freeze", required=True); runp.add_argument("--scheduler-lease", required=True); runp.add_argument("--execute", action="store_true")
    args = p.parse_args(); prepare(args) if args.op == "prepare" else run(args)

if __name__ == "__main__":
    main()
