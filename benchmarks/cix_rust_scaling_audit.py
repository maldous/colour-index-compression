#!/usr/bin/env python3
"""Frozen, gated native-CIX scaling cells using the established receipt path.

This module owns no worker pool. A released plan is dispatched serially under
the existing WaveScheduler lock and physical-core leases. Every native phase
uses cix_rust_perf_audit.execute_phase, including its direct-child receipt.
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, sys
from datetime import datetime, timezone
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.cix_rust_perf_audit import (affinity_wrapped, artifact as audited_artifact,
    cgroup_ok, cpu_sets, cpu_topology, parse_gnu_time, physical_cpus, release_revision, runtime_dsos,
    sha256 as digest, execute_phase)
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core

THREADS = (1, 2, 4, 8, 12, 16, 20, 24)
PROFILES = {"fast": ["--fast"], "default": [], "best": ["--best"]}
MAX_RAM, MAX_TEMP = 12_000_000_000, 4_000_000_000
SCHEMA = "cix-rust-scaling-audit-v3"

def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def now(): return datetime.now(timezone.utc).isoformat()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)

def artifact(directory):
    """Use the established release revision rule and bind actual DSOs."""
    directory = Path(directory).resolve(); metadata = directory / "native-release.json"
    value = json.loads(metadata.read_text()); source = release_revision(value)
    declared = value.get("binaries") or value.get("artifacts")
    if not isinstance(declared, dict): raise RuntimeError("native release metadata has no binary identity map")
    binaries = {}
    for name in ("cix", "uncix", "cixcat"):
        target, entry = directory / name, declared.get(name)
        expected = entry.get("sha256") if isinstance(entry, dict) else entry
        if not target.is_file() or not isinstance(expected, str) or digest(target) != expected:
            raise RuntimeError(f"invalid frozen {name} artifact")
        binaries[name] = {"path": str(target), "sha256": expected, "bytes": target.stat().st_size,
                          "runtime_dsos": runtime_dsos(target)}
    # Call the mature parser for its original metadata schema. New checkpoint
    # metadata uses artifacts rather than binaries, so the checks above retain
    # the same source/executable/DSO binding without inventing old fields.
    compatible = audited_artifact(directory, "scaling-release") if isinstance(value.get("binaries"), dict) else None
    return {"directory": str(directory), "metadata": {"path": str(metadata), "sha256": digest(metadata)},
            "source_revision": source, "release_metadata": value, "audited": compatible, "binaries": binaries}

def independent_forms():
    return [
        {"name":"cixg1_independent", "format":"cixg1", "mode":"independent", "history":"0",
         "encode_prefix":["--format","cixg1","--parallelism","blocks","--independent-blocks"]},
        {"name":"cixg2_independent", "format":"cixg2", "mode":"independent", "history":"0",
         "encode_prefix":["--format","cixg2","--parallelism","blocks","--independent-blocks"]},
    ]

def frozen_topology():
    """Keep all requested logical CPUs while identifying shared-core siblings."""
    rows = cpu_topology()
    return {"visible": rows, "physical_count": len({(r["package"], r["core"]) for r in rows}),
            "logical_count": len(rows), "mixed_capacity": len({r["capacity"] for r in rows}) > 1}

def select_cpus(workers, topology):
    visible = [r["cpu"] for r in topology["visible"]]
    if workers > len(visible): raise RuntimeError("frozen logical CPU point is unavailable")
    # Prefer one logical CPU per core, then sibling logical CPUs only for the
    # explicit >physical scaling points. A serial executor never overlaps them.
    first, rest, seen = [], [], set()
    for row in topology["visible"]:
        core = (row["package"], row["core"])
        (first if core not in seen else rest).append(row["cpu"]); seen.add(core)
    return (first + rest)[:workers]

def plan(release, inputs, output, block, history, memory, repetitions):
    if not inputs or repetitions < 1: raise RuntimeError("at least one input and one repetition are required")
    if history != "0": raise RuntimeError("current native routes reject nonzero --history; freeze history=0 only")
    if output.exists(): raise RuntimeError("immutable scaling plan already exists")
    cells = []
    for path in inputs:
        if not path.is_file(): raise RuntimeError(f"missing frozen input: {path}")
        source = {"path":str(path.resolve()), "bytes":path.stat().st_size, "sha256":digest(path)}
        for profile, flags in PROFILES.items():
            for workers in THREADS:
                for repetition in range(1, repetitions + 1):
                    for form in independent_forms():
                        cell = {"input":source, "profile":profile, "encode_threads":workers, "decode_threads":1,
                                "repetition":repetition, "form":form,
                                "encode_flags":[*flags,*form["encode_prefix"],"--threads",str(workers),"--block-size",block,"--history","0","--memory",memory],
                                "decode_flags":["--threads","1","--memory",memory],
                                "verification":"complete archive SHA-256 and fresh native restoration SHA-256"}
                        cell["cell_id"] = hashlib.sha256(canonical(cell)).hexdigest()[:24]; cells.append(cell)
    value = {"schema":SCHEMA, "status":"FROZEN_NOT_DISPATCHED",
             "execution_gate":"a JSON authorization binding this exact plan digest is required", "artifact":artifact(release),
             "harness":{"path":"benchmarks/cix_rust_scaling_audit.py", "sha256":digest(Path(__file__)),
                        "phase_executor":"benchmarks/cix_rust_perf_audit.py:execute_phase", "phase_executor_sha256":digest(ROOT / "benchmarks/cix_rust_perf_audit.py"),
                        "phase_supervisor":"benchmarks/cix_phase_receipt.py", "phase_supervisor_sha256":digest(ROOT / "benchmarks/cix_phase_receipt.py"),
                        "scheduler":"benchmarks/hutter_experiment_scheduler.py:WaveScheduler", "scheduler_sha256":digest(ROOT / "benchmarks/hutter_experiment_scheduler.py")},
             "threads":list(THREADS), "topology":frozen_topology(), "decode_claim":"decoder is fixed at one thread; no parallel decode claim",
             "persistent_container":{"name":"cixm6", "status":"UNSUPPORTED_UNPROVEN", "reason":"CIXM6 may retain container state, but no selected persistent-history route/window is proved; it is excluded from scaling cells."},
             "aggregate_budget":{"ram":MAX_RAM,"temporary":MAX_TEMP,"swap":0,"max_parallel_jobs":1,"parallel_library_oversubscription":"forbidden"}, "cells":cells}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as stream: stream.write(json.dumps(value, sort_keys=True, indent=2).encode() + b"\n")
    return value

def load_gate(plan_path, gate_path):
    if not gate_path.is_file(): raise RuntimeError("cleanup gate is absent; refusing scaling dispatch")
    try: gate = json.loads(gate_path.read_text())
    except json.JSONDecodeError as exc: raise RuntimeError("cleanup gate is not JSON") from exc
    if gate.get("schema") != "cix-rust-scaling-execution-gate-v1" or gate.get("authorize_dispatch") is not True:
        raise RuntimeError("cleanup gate does not authorize dispatch")
    if gate.get("plan_sha256") != digest(plan_path): raise RuntimeError("cleanup gate does not bind this immutable plan")
    return gate

def validate_plan(plan_path):
    value = json.loads(plan_path.read_text())
    if value.get("schema") != SCHEMA or value.get("status") != "FROZEN_NOT_DISPATCHED":
        raise RuntimeError("only an immutable undisbursed scaling plan is executable")
    expected = (("sha256",Path(__file__)), ("phase_executor_sha256",ROOT / "benchmarks/cix_rust_perf_audit.py"),
                ("phase_supervisor_sha256",ROOT / "benchmarks/cix_phase_receipt.py"), ("scheduler_sha256",ROOT / "benchmarks/hutter_experiment_scheduler.py"))
    for field, path in expected:
        if value.get("harness",{}).get(field) != digest(path): raise RuntimeError(f"frozen plan helper changed: {field}")
    if value.get("aggregate_budget") != {"ram":MAX_RAM,"temporary":MAX_TEMP,"swap":0,"max_parallel_jobs":1,"parallel_library_oversubscription":"forbidden"}:
        raise RuntimeError("plan aggregate resource budget differs from scaling policy")
    if value.get("persistent_container",{}).get("status") != "UNSUPPORTED_UNPROVEN":
        raise RuntimeError("plan makes an unsupported persistent-history claim")
    if value.get("topology") != frozen_topology(): raise RuntimeError("CPU topology changed since plan freeze")
    return value

def revalidate_artifact(bound):
    if canonical(artifact(bound["directory"])) != canonical(bound):
        raise RuntimeError("frozen executable, metadata, source revision, or resolved DSO changed")

def cell_command(cell, release, work, decode):
    binary = release["binaries"]["uncix" if decode else "cix"]["path"]
    archive, restored = work / "candidate.cix", work / "restored.bin"
    time_file = work / ("decode.gnu-time.txt" if decode else "encode.gnu-time.txt")
    command = ["/usr/bin/time", "-v", "-o", str(time_file), binary]
    if decode: command += [*cell["decode_flags"],"-f","-o",str(restored),str(archive)]
    else: command += [*cell["encode_flags"],"-f","-o",str(archive),cell["input"]["path"]]
    return command, restored, time_file

def run_cell(cell, release, destination, cpus, phase_runner=execute_phase):
    work = destination / "cells" / cell["cell_id"]; work.mkdir(parents=True, exist_ok=False)
    source = Path(cell["input"]["path"])
    if not source.is_file() or source.stat().st_size != cell["input"]["bytes"] or digest(source) != cell["input"]["sha256"]:
        raise RuntimeError("frozen input changed before dispatch")
    budget = {"max_rss_bytes":MAX_RAM,"max_temp_bytes":MAX_TEMP,"wall_seconds":1200}
    result = {"schema":SCHEMA,"cell":cell,"started_at":now(),"cpu_set":cpus,"budget":budget,"status":"UNQUALIFIED","phases":[]}
    for phase_name, decode in (("encode",False),("decode",True)):
        command, restored, time_file = cell_command(cell, release, work, decode)
        affinity, cgroup = work / f"{phase_name}.effective-affinity.txt", work / f"{phase_name}.effective-cgroup.txt"
        wrapped = affinity_wrapped(command, affinity, cgroup)
        try:
            phase = phase_runner(unit=f"cix-scaling-{cell['cell_id']}-{phase_name}",command=wrapped,work=work,destination=work,budget=budget,cpu=cpus,inaccessible=[] if not decode else [source],input_bytes=cell["input"]["bytes"])
        except BaseException as exc:
            result["execution_error"] = f"{type(exc).__name__}: {exc}"
            result["failed_phase"] = phase_name
            result["finished_at"] = now()
            write_json(work / "result.json", result)
            return result
        try: metrics = parse_gnu_time(time_file)
        except (OSError, RuntimeError, ValueError): metrics = None
        if metrics is not None:
            wall = metrics["wall_seconds"]
            metrics["throughput_bytes_per_second"] = cell["input"]["bytes"] / wall if wall > 0 else None
            metrics["throughput_note"] = None if wall > 0 else "GNU time wall value has no positive precision; throughput withheld"
        result["phases"].append({"name":phase_name,"phase":phase,"command":wrapped,"effective_affinity":affinity.read_text() if affinity.is_file() else None,"effective_cgroup":cgroup.read_text() if cgroup.is_file() else None,"metrics":metrics})
        if phase.get("exit_code") != 0 or phase.get("stop_reason") is not None:
            result["finished_at"]=now(); write_json(work / "result.json",result); return result
    archive = work / "candidate.cix"
    result["archive"]={"bytes":archive.stat().st_size if archive.is_file() else None,"sha256":digest(archive) if archive.is_file() else None}
    result["restored"]={"bytes":restored.stat().st_size if restored.is_file() else None,"sha256":digest(restored) if restored.is_file() else None}
    receipt_ok = all(cgroup_ok(item["effective_cgroup"],cpus,budget) and item["metrics"] is not None for item in result["phases"])
    restored_ok = restored.is_file() and result["restored"]["bytes"] == cell["input"]["bytes"] and result["restored"]["sha256"] == cell["input"]["sha256"]
    result["status"] = "VERIFIED" if archive.is_file() and restored_ok and receipt_ok else "UNQUALIFIED"; result["finished_at"]=now()
    write_json(work / "result.json",result); return result

def execute_frozen(plan_path, cleanup_gate, destination=None, *, phase_runner=execute_phase):
    """Serial real adapter: one shared WaveScheduler lock, then receipt phases."""
    plan_path = Path(plan_path).resolve(); cleanup_gate = Path(cleanup_gate)
    load_gate(plan_path,cleanup_gate); value = validate_plan(plan_path)
    destination = Path(destination or plan_path.with_suffix(".results")).resolve()
    if destination.exists(): raise RuntimeError("execution destination already exists; retain prior attempts")
    if len(value["topology"]["visible"]) < max(THREADS): raise RuntimeError("insufficient logical CPUs for the frozen 24-worker sweep")
    scheduler = WaveScheduler(ROOT,max_jobs=1,max_memory_bytes=MAX_RAM,max_temp_bytes=MAX_TEMP); scheduler.state.mkdir(parents=True,exist_ok=True)
    lock = scheduler._wave_lock_path().open("a+")
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError as exc: lock.close(); raise RuntimeError("another WaveScheduler wave holds the aggregate resource budget") from exc
    try:
        revalidate_artifact(value["artifact"]); destination.mkdir(parents=True)
        write_json(destination / "execution-binding.json",{"schema":SCHEMA,"plan_path":str(plan_path),"plan_sha256":digest(plan_path),"gate_sha256":digest(cleanup_gate),"started_at":now(),"scheduler":"WaveScheduler shared lock plus physical-core leases","max_parallel_jobs":1})
        results=[]
        for cell in value["cells"]:
            cpus=select_cpus(cell["encode_threads"],value["topology"])
            # Lease each physical core once even when the explicit logical-24
            # point uses sibling CPUs; serial execution prevents overlap.
            leases=scheduler._lease_cores([{"physical_core":list(dict.fromkeys(_core(cpu) for cpu in cpus))}])
            try: result=run_cell(cell,value["artifact"],destination,cpus,phase_runner)
            finally:
                for lease in leases: lease.close()
            results.append(result)
            if result["status"] != "VERIFIED": write_json(destination / "execution-summary.json",{"status":"STOPPED_UNQUALIFIED","results":results}); return results
        revalidate_artifact(value["artifact"]); write_json(destination / "execution-summary.json",{"status":"COMPLETED","results":results}); return results
    finally: lock.close()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--release",type=Path); parser.add_argument("--input",type=Path,action="append"); parser.add_argument("--output",type=Path); parser.add_argument("--block-size",default="1MiB"); parser.add_argument("--history",default="0"); parser.add_argument("--memory",default="2GiB"); parser.add_argument("--repetitions",type=int,default=3); parser.add_argument("--execute",type=Path); parser.add_argument("--cleanup-gate",type=Path); parser.add_argument("--results",type=Path); args=parser.parse_args()
    if args.execute:
        if not args.cleanup_gate: parser.error("--execute requires --cleanup-gate")
        print(json.dumps({"results":[item["status"] for item in execute_frozen(args.execute,args.cleanup_gate,args.results)]}))
    elif args.release and args.input and args.output:
        print(json.dumps({"cells":len(plan(args.release,args.input,args.output,args.block_size,args.history,args.memory,args.repetitions)["cells"])}))
    else: parser.error("plan arguments or --execute are required")
if __name__ == "__main__": main()
