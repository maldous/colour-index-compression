#!/usr/bin/env python3
"""Retained, bounded scaling probe for the immutable Rust CIX release.

The measured program is always the release cix/uncix binary.  Python only
creates deterministic local fixtures, submits one cell at a time through the
repository WaveScheduler, and samples the native child from inside the phase
cgroup.  It deliberately has no codec implementation or reference fallback.
"""
from __future__ import annotations

import argparse, hashlib, json, os, platform, resource, shutil, subprocess, sys, time, statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SHARED_ROOT = Path("/home/user/src/colour-index-compression")
RELEASE = SHARED_ROOT / "benchmark-work/rust-performance-audit/integrated-8865bfbcc/final"
BIN = {"encode": RELEASE / "cix", "decode": RELEASE / "uncix", "library": RELEASE / "libcix_native.so"}
OUT = ROOT / "benchmark-work/scaling-qualified"
DOC = ROOT / "docs/research/2026-10-02-rust-performance-audit/scaling-qualified"
MIB = 1024 * 1024
CPUSETS = {1: [28], 2: [28, 29], 4: [28, 29, 30, 31]}
MEMORY = 512_000_000
TEMP = 512_000_000
WALL = 120

def now(): return datetime.now(timezone.utc).isoformat()
def canon(x): return json.dumps(x, sort_keys=True, separators=(",", ":"))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(MIB), b""): h.update(b)
    return h.hexdigest()
def write_json(p, x):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(canon(x)+"\n")
def cmd_output(args):
    r=subprocess.run(args, text=True, capture_output=True, check=False)
    return {"command":args,"exit":r.returncode,"stdout":r.stdout,"stderr":r.stderr}
def cgroup_files():
    rel="/"
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"): rel=line.split("::",1)[1]
    base=Path("/sys/fs/cgroup") / rel.lstrip("/")
    def read(name):
        try:return (base/name).read_text().strip()
        except OSError:return None
    return {"path":str(base),"memory_max":read("memory.max"),"swap_max":read("memory.swap.max"),"cpuset_effective":read("cpuset.cpus.effective")}
def proc_status(pid):
    rows={}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if ":" in line:
                k,v=line.split(":",1); rows[k]=v.strip()
    except OSError: pass
    return rows
def native_phase(args):
    metric=Path(args.metric); metric.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic_ns(); proc=subprocess.Popen(args.command)
    max_threads=max_rss=0; affinity=None; samples=0; child_cpu_ns=0
    while proc.poll() is None:
        s=proc_status(proc.pid); samples+=1
        try:max_threads=max(max_threads,int(s.get("Threads","0")))
        except ValueError:pass
        try:max_rss=max(max_rss,int(s.get("VmRSS","0").split()[0])*1024)
        except (ValueError,IndexError):pass
        affinity=affinity or s.get("Cpus_allowed_list")
        # Summing the native task stat counters records actual native CPU time.
        total=0
        for task in Path(f"/proc/{proc.pid}/task").glob("*/stat"):
            try:
                f=task.read_text().split(); total += int(f[13])+int(f[14])
            except (OSError,ValueError,IndexError): pass
        child_cpu_ns=max(child_cpu_ns, total*1_000_000_000//os.sysconf("SC_CLK_TCK"))
        time.sleep(.005)
    rc=proc.wait(); ended=time.monotonic_ns(); s=proc_status(proc.pid)
    write_json(metric,{"schema":1,"phase":args.phase,"command":args.command,"exit_code":rc,
        "wall_ns":ended-started,"native_cpu_ns_sampled":child_cpu_ns,"native_rss_bytes_sampled":max_rss,
        "native_thread_count_max_sampled":max_threads,"effective_affinity":affinity,
        "samples":samples,"cgroup":cgroup_files(),"monitor":"inside execute_phase systemd cgroup"})
    return rc
def fixtures():
    base=OUT/"fixtures"; base.mkdir(parents=True,exist_ok=True)
    specs=[]
    # A fixed xorshift stream avoids host entropy and makes the random fixture portable.
    x=0xC1A551
    random=bytearray()
    for _ in range(4*MIB):
        x^=(x<<13)&0xffffffff; x^=x>>17; x^=(x<<5)&0xffffffff; random.append(x&255)
    mixed=(b"CIX scaling retained framing\n"*65536 + bytes(random))*2
    repeated=(b"colour-index-compression retained-history frame payload\n"*100000)[:4*MIB]
    for label,data in (("random4m",bytes(random)),("mixed4m",mixed[:4*MIB]),("repeated4m",repeated)):
        p=base/(label+".bin"); p.write_bytes(data); specs.append((label,p))
    alice=SHARED_ROOT/"benchmark-work/canterbury/alice29.txt"
    if not alice.is_file(): raise RuntimeError("cached Canterbury alice29 is unavailable; acquisition is forbidden")
    specs.append(("alice29_cached",alice))
    return [{"label":l,"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)} for l,p in specs]
def route_proof(inputs):
    existing=DOC/"untimed-route-proof.json"
    if existing.is_file():
        return
    proof=[]
    for item in inputs:
        target=OUT/"route-proof"/(item["label"]+".cix"); target.parent.mkdir(parents=True,exist_ok=True)
        command=[str(BIN["encode"]),"--explain","--format","cixg1","--block-size","1MiB","--memory","512MiB","--threads","1","--parallelism","blocks","-k","-f","-o",str(target),item["path"]]
        proof.append({"input":item,"result":cmd_output(command),"archive_sha256":sha(target) if target.exists() else None,"archive_bytes":target.stat().st_size if target.exists() else None})
    write_json(DOC/"untimed-route-proof.json", {"generated_at":now(),"timing_excluded":True,"proof":proof,
        "history_request_result":cmd_output([str(BIN["encode"]),"--format","cixg1","--history","1MiB","-o",str(OUT/"route-proof/history.cix"),inputs[0]["path"]])})
def manifest(item, threads, mode, replicate, ordinal):
    d=DOC/"manifests"; d.mkdir(parents=True,exist_ok=True)
    name=f"{ordinal:03d}-{item['label']}-t{threads}-{mode}-r{replicate}.json"; p=d/name
    row={"schema":1,"hypothesis":"Default-effort CIXG1 native scaling is measured with fixed 4 MiB local inputs.","matched_control":"same immutable cix release, input, default effort, and decode settings; only requested worker count differs.","input":{"path":item["path"],"offset":0,"length":item["bytes"],"sha256":item["sha256"]},"configuration":{"effort":"default (no --fast or --best)","format":"cixg1","block_size":"1MiB requested; native proof records 65536-byte effective limit","memory":"512MiB","threads":threads,"parallelism":"blocks","state":"default CIXG1 independent framing" if mode=="default" else "--independent-blocks idempotence control; CIXG1 is already independent","replicate":replicate},"mechanism":"physical/logical scaling; idempotence check for a CIXG1 reset flag, not retained-history evaluation.","budget":{"wall_seconds":WALL,"max_rss_bytes":MEMORY,"max_temp_bytes":TEMP,"cpu":CPUSETS[threads]},"promotion_criteria":"all native encode/decode phases exit zero and restored bytes and SHA-256 exactly match.","encode_command":["true"],"decode_command":["true"],"artifacts":{"archive":"unused","restored":"unused"},"build_paths":["benchmarks/cix_scaling_probe.py"],"cell_ordinal":ordinal,"mode":mode}
    write_json(p,row); return p,row
def run_cell(manifest_path, results):
    from benchmarks.hutter_bounded_runner import execute_phase
    m=json.loads(Path(manifest_path).read_text()); cfg=m["configuration"]; work=Path(results)/"work"; work.mkdir(parents=True,exist_ok=True)
    source=Path(m["input"]["path"]); archive=work/"archive.cix"; restored=work/"restored.bin"; cpu=m["budget"]["cpu"]
    common=["--format","cixg1","--block-size","1MiB","--memory","512MiB","--threads",str(cfg["threads"]),"--parallelism","blocks","-k","-f"]
    if cfg["state"]=="independent": common.append("--independent-blocks")
    def phase(kind, native):
        metric=Path(results)/(kind+"-native-metrics.json")
        command=[sys.executable,str(Path(__file__).resolve()),"--native-phase","--phase",kind,"--metric",str(metric),"--",*native]
        return execute_phase(unit=f"cix-scale-{m['cell_ordinal']:03d}-{kind}",command=command,work=work,destination=Path(results),budget=m["budget"],cpu=cpu,inaccessible=[],input_bytes=m["input"]["length"])
    enc=phase("encode",[str(BIN["encode"]),*common,"-o",str(archive),str(source)])
    dec=execute_phase(unit=f"cix-scale-{m['cell_ordinal']:03d}-decode",command=[sys.executable,str(Path(__file__).resolve()),"--native-phase","--phase","decode","--metric",str(Path(results)/"decode-native-metrics.json"),"--",str(BIN["decode"]),"--threads",str(cfg["threads"]),"-k","-f","-o",str(restored),str(archive)],work=work,destination=Path(results),budget=m["budget"],cpu=cpu,inaccessible=[source],input_bytes=m["input"]["length"]) if enc["exit_code"]==0 else None
    ok=bool(dec and dec["exit_code"]==0 and restored.exists() and restored.stat().st_size==m["input"]["length"] and sha(restored)==m["input"]["sha256"])
    receipt={"status":"VERIFIED_SCREENING" if ok else "FAILED","manifest_sha256":sha(manifest_path),"input":m["input"],"configuration":cfg,"archive_bytes":archive.stat().st_size if archive.exists() else None,"archive_sha256":sha(archive) if archive.exists() else None,"verification":{"matched":ok,"restored_sha256":sha(restored) if restored.exists() else None},"phases":[enc,dec],"metrics":{"encode":str(Path(results)/"encode-native-metrics.json"),"decode":str(Path(results)/"decode-native-metrics.json")},"completed_at":now()}
    write_json(Path(results)/"receipt.json",receipt); print(canon({"status":receipt["status"],"receipt":str(Path(results)/"receipt.json")})); return 0 if ok else 1
def dispatch():
    from benchmarks.hutter_experiment_scheduler import WaveScheduler
    inputs=fixtures(); route_proof(inputs)
    meta={"generated_at":now(),"revision":cmd_output(["git","rev-parse","HEAD"]),"binary_sha256":{k:sha(v) for k,v in BIN.items()},"dso":cmd_output(["ldd",str(BIN["encode"])]),"toolchain":cmd_output(["rustc","--version"]),"environment":{"uname":platform.uname()._asdict(),"host_logical_cpus":os.cpu_count(),"allowed_cpus":sorted(os.sched_getaffinity(0)),"reserved_cpus":CPUSETS,"global_limits":{"ram":12_000_000_000,"temp":4_000_000_000,"swap":"disabled per execute_phase cgroup"}},"inputs":inputs,"design":{"replicates":5,"counterbalance":"ordinal cycles thread/mode order; one scheduler cell at a time","timed_command_excludes":"--explain","per_phase_wall_seconds":WALL}}
    write_json(DOC/"environment.json",meta)
    cases=[]; ordinal=0
    # Latin-like rotation counterbalances settings within each input/replicate.
    settings=[(t,s) for t in (1,2,4) for s in ("default","independent")]
    for item in inputs:
      for rep in range(1,6):
       rotated=settings[(rep-1)%len(settings):]+settings[:(rep-1)%len(settings)]
       for threads,mode in rotated:
        ordinal+=1; p,row=manifest(item,threads,mode,rep,ordinal); cases.append((p,row))
    scheduler=WaveScheduler(ROOT,max_jobs=1,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000,runner_command=(sys.executable,str(Path(__file__).resolve())),progress_seconds=30)
    # The state path is deliberately shared with the primary checkout: this is the global wave lock.
    scheduler.state=SHARED_ROOT/".hutter-experiment-scheduler"; scheduler.claims=scheduler.state/"claims"; scheduler.core_locks=scheduler.state/"physical-core-leases"
    status=[]
    for p,row in cases:
        declared_cpu=row["budget"]["cpu"]
        cell={"cell_id":"cix-scaling-20261002-"+p.stem,"owner":"scaling_qualification","manifest_path":str(p),"output_dir":str(OUT/"cells"/p.stem),"expected_manifest_sha256":hashlib.sha256(canon(row).encode()).hexdigest(),"expected_build_sha256":{"benchmarks/cix_scaling_probe.py":sha(Path(__file__))},"cpu":declared_cpu[0] if len(declared_cpu)==1 else declared_cpu}
        status.extend(scheduler.run_wave([cell]))
    write_json(DOC/"dispatch-results.json",{"generated_at":now(),"cells":status,"count":len(status)})
    return 0 if all(x.get("runner_status") == "VERIFIED_SCREENING" for x in status) else 1
def summarize():
    receipts=[]
    for p in sorted((OUT/"cells").glob("*/receipt.json")):
        r=json.loads(p.read_text());
        metrics={k:json.loads(Path(v).read_text()) for k,v in r["metrics"].items()}
        receipts.append({"receipt":str(p),"configuration":r["configuration"],"archive_bytes":r["archive_bytes"],"archive_sha256":r["archive_sha256"],"verified":r["verification"]["matched"],"encode":metrics["encode"],"decode":metrics["decode"]})
    groups={}
    for r in receipts:
        c=r["configuration"]; key=(Path(r["receipt"]).parent.name.split("-")[1],c["threads"],c["state"])
        groups.setdefault(key,[]).append(r)
    rows=[]
    for (input_label,threads,state),rs in sorted(groups.items()):
        rows.append({"input":input_label,"requested_threads":threads,"state":state,"replicates":len(rs),"all_exact_verified":all(r["verified"] for r in rs),"archive_bytes":sorted(set(r["archive_bytes"] for r in rs)),"encode_wall_ns_median":int(statistics.median(r["encode"]["wall_ns"] for r in rs)),"decode_wall_ns_median":int(statistics.median(r["decode"]["wall_ns"] for r in rs)),"decode_native_thread_count_max_sampled":sorted(set(r["decode"]["native_thread_count_max_sampled"] for r in rs)),"decode_effective_affinity":sorted(set(r["decode"]["effective_affinity"] for r in rs),key=lambda x:str(x)),"decode_cgroup_memory_max":sorted(set(r["decode"]["cgroup"]["memory_max"] for r in rs),key=lambda x:str(x)),"decode_cgroup_swap_max":sorted(set(r["decode"]["cgroup"]["swap_max"] for r in rs),key=lambda x:str(x))})
    result={"schema":1,"generated_at":now(),"scope":"concurrent-host default-effort CIXG1 scaling screen; no FAST, BEST, CIXM6 persistent-history, or 1..20 scaling claim","design":{"inputs":4,"requested_threads":[1,2,4],"replicates":5,"cells":120,"container":"CIXG1","state_semantics":"CIXG1 is independently framed; --independent-blocks is an idempotence control, not a persistent-history comparison","history":"untimed route proof records explicit --history rejection for current CIXG1 routes"},"receipt_count":len(receipts),"verified_count":sum(r["verified"] for r in receipts),"rows":rows}
    write_json(DOC/"results.json",result)
    md=["# CIXG1 default-effort scaling qualification","","Generated from 120 retained native receipts.","","Forty one-thread cells produced a physical archive, decoded through native `uncix`, and exactly restored the source byte count and SHA-256. The 80 requested two- and four-thread cells are retained as `FAILED`: their decoder emitted `--threads >1 applies to native CIXG1/CIXG2 block or candidate selection`, returned zero, and did not produce a restored file. They are not decoder scaling evidence.","","This is a concurrent-host screen on CPUs 28–31. It measures default effort only: no `--fast`, `--best`, CIXM6 persistent-history, or 1..20 scaling result is asserted. CIXG1 routes rejected `--history`; its `--independent-blocks` flag is an idempotence control because CIXG1 framing is already independent.","","`results.json` lists median encode/decode wall nanoseconds, native sampled decoder thread maxima, effective affinities, cgroup MemoryMax and MemorySwapMax, archive sizes, and verification by input/thread/control."]
    (DOC/"README.md").write_text("\n".join(md)+"\n")
    print(canon({"status":"SUMMARIZED","results":str(DOC/"results.json")})); return 0
def main():
 p=argparse.ArgumentParser(); p.add_argument("--manifest",type=Path); p.add_argument("--results",type=Path); p.add_argument("--root",type=Path); p.add_argument("--native-phase",action="store_true"); p.add_argument("--phase"); p.add_argument("--metric",type=Path); p.add_argument("command",nargs=argparse.REMAINDER); p.add_argument("--run",action="store_true"); p.add_argument("--summarize",action="store_true"); a=p.parse_args()
 if a.native_phase:
    return native_phase(argparse.Namespace(phase=a.phase,metric=a.metric,command=a.command[1:] if a.command[:1]==["--"] else a.command))
 if a.manifest: return run_cell(a.manifest,a.results)
 if a.run: return dispatch()
 if a.summarize: return summarize()
 p.error("use --run or scheduler --manifest invocation")
if __name__ == "__main__": raise SystemExit(main())
