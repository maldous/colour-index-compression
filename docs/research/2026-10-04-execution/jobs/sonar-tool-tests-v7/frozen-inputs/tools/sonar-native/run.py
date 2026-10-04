#!/usr/bin/env python3
"""Bounded final Rust and exported-optional-Python Sonar analysis.

This CIX-owned runner deliberately imports, rather than reimplements, the
authenticated stopped-benchmark and idle checks from sonar-cxx/repair.py.
It never scans the retired Python runtime tree.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, re, secrets, shutil, subprocess, sys, time, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CXX = ROOT / "tools/sonar-cxx/repair.py"
HYGIENE = ROOT / "docs/research/2026-10-04-automatic-specialised-models/hygiene"
STOP_SUMMARY = ROOT / "docs/research/2026-10-04-automatic-specialised-models/qualification/silesia-confirmation-v1/summary.json"
SERVER = "sonarqube@sha256:4905574ab8584dcac1a06c01cdc43a4ce9e369723ac4a7ab1d029c1bf71e6fe9"
SCANNER = "sonarsource/sonar-scanner-cli@sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57"
CPUS = [8, 10, 12, 14]
SERVER_MEMORY, SCANNER_MEMORY = 4 * 1024**3, 1 * 1024**3
TEMP_BUDGET = 4_000_000_000

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path); module = importlib.util.module_from_spec(spec)
    assert spec.loader; spec.loader.exec_module(module); return module

def sha(path: Path) -> str:
    with path.open("rb") as f: return hashlib.file_digest(f, "sha256").hexdigest()

def save(path: Path, value) -> None: path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def tree_digest(root: Path) -> str:
    rows=[(p.relative_to(root).as_posix(),sha(p)) for p in sorted(root.rglob("*")) if p.is_file()]
    return hashlib.sha256(json.dumps(rows,separators=(",",":"),sort_keys=True).encode()).hexdigest()

def verify_clippy(report: Path, receipt: Path, root: Path) -> dict:
    if not report.is_file() or not receipt.is_file(): raise RuntimeError("fresh Clippy report and binding receipt are required")
    row=json.loads(receipt.read_text())
    required={"source_root","source_tree_sha256","command","exit_code","output_sha256"}
    if not required.issubset(row): raise RuntimeError("Clippy receipt lacks required source/command/exit/hash binding")
    if Path(row["source_root"]).resolve()!=root.resolve() or row["source_tree_sha256"]!=tree_digest(root): raise RuntimeError("Clippy receipt source binding differs")
    if row["exit_code"]!=0 or not row["command"] or row["output_sha256"]!=sha(report): raise RuntimeError("Clippy receipt is not a successful bound report")
    return row

PLUGIN_NAMES = ("sonar-rust-plugin-1.8.1.3395.jar", "sonar-python-plugin-5.31.0.36502.jar")

def expected_plugins(cxx) -> list[dict]:
    sizes={name:size for name,size,_ in cxx.IMAGE_CORE_EXTENSION_INVENTORY}
    if not all(name in sizes for name in PLUGIN_NAMES): raise RuntimeError("pinned image inventory lacks Rust/Python plugins")
    return [{"jar":name,"bytes":sizes[name]} for name in PLUGIN_NAMES]

def stage_language_plugins(stage: Path, expected: list[dict]) -> list[dict]:
    """Copy only Rust/Python core plugins from the pinned local image under the lease."""
    stage.mkdir()
    container="cix-final-native-plugin-extract"
    try:
        subprocess.run(["docker","create","--name",container,SERVER],check=True,timeout=60,capture_output=True)
        rows=[]
        for item in expected:
            name=item["jar"]
            subprocess.run(["docker","cp",f"{container}:/opt/sonarqube/lib/extensions/plugins/{name}",str(stage/name)],check=True,timeout=60,capture_output=True)
            actual=(stage/name).stat().st_size
            if actual != item["bytes"]: raise RuntimeError("pinned image plugin size differs from recorded inventory: "+name)
            rows.append({"jar":name,"bytes":actual,"sha256":sha(stage/name)})
        return rows
    finally:
        subprocess.run(["docker","rm","-f",container],check=False,capture_output=True,timeout=30)

def temporary_accounting(cxx, plugins: list[dict]) -> dict:
    retained=cxx.allocated_bytes(cxx.RETAINED_NATIVE_WORK)
    tmpfs=(cxx.PROBE_SERVER_DATA_BYTES+cxx.PROBE_SERVER_LOG_BYTES+cxx.PROBE_SERVER_TEMP_BYTES
           +cxx.PROBE_SERVER_EXTENSIONS_BYTES+cxx.PROBE_SERVER_TMP_BYTES+cxx.PROBE_SCANNER_TEMP_BYTES)
    staged=sum(x["bytes"] for x in plugins); total=retained+tmpfs+staged+cxx.PROBE_EVIDENCE_RESERVE_BYTES
    row={"retained_work_bytes":retained,"server_tmpfs_bytes":cxx.PROBE_SERVER_DATA_BYTES+cxx.PROBE_SERVER_LOG_BYTES+cxx.PROBE_SERVER_TEMP_BYTES+cxx.PROBE_SERVER_EXTENSIONS_BYTES+cxx.PROBE_SERVER_TMP_BYTES,"scanner_tmpfs_bytes":cxx.PROBE_SCANNER_TEMP_BYTES,"staged_plugin_bytes":staged,"evidence_reserve_bytes":cxx.PROBE_EVIDENCE_RESERVE_BYTES,"aggregate_bytes":total,"budget_bytes":TEMP_BUDGET}
    if total>TEMP_BUDGET: raise RuntimeError("final Sonar temporary reservation exceeds shared 4GB policy: "+json.dumps(row,sort_keys=True))
    return row

def inventory(root: Path, suffix: str) -> list[dict]:
    return [{"path": p.relative_to(root).as_posix(), "sha256": sha(p)} for p in sorted(root.rglob("*"))
            if p.is_file() and p.suffix == suffix and "__pycache__" not in p.parts]

def prepare(source: Path, out: Path) -> None:
    if out.exists(): raise RuntimeError("refusing to overwrite prepared evidence")
    manifest = source / "EXPORT-MANIFEST.json"
    native = source / "rust/cix-native"
    if not manifest.is_file() or not (native / "Cargo.toml").is_file():
        raise RuntimeError("source must be a materialised public export with EXPORT-MANIFEST.json")
    exported = json.loads(manifest.read_text())
    members = exported.get("members_sha256")
    if not isinstance(members, dict): raise RuntimeError("export manifest lacks members_sha256")
    language_members = [{"path": path, "sha256": digest} for path, digest in sorted(members.items())
                        if path.endswith((".rs", ".py"))]
    excluded = []
    selected = []
    for row in language_members:
        path = row["path"]
        if "/vendor/" in path or path.startswith("third_party/"):
            excluded.append({**row, "reason": "preserved third-party/vendor source; separately visible in CXX scope"})
        elif path.startswith(("rust/cix-native/", "rust/cix-portable/")):
            selected.append(row)
        else:
            excluded.append({**row, "reason": "outside the CIX Rust/Python export members"})
    for row in selected:
        file = source / row["path"]
        if not file.is_file() or sha(file) != row["sha256"]:
            raise RuntimeError("export manifest hash mismatch: " + row["path"])
    if any("runtime/cix_runtime" in row["path"] for row in selected):
        raise RuntimeError("retired runtime Python is forbidden")
    native_rust = [{**row, "path": row["path"].removeprefix("rust/cix-native/")}
                   for row in selected if row["path"].startswith("rust/cix-native/") and row["path"].endswith(".rs")]
    portable_rust = [{**row, "path": row["path"].removeprefix("rust/cix-portable/")}
                     for row in selected if row["path"].startswith("rust/cix-portable/") and row["path"].endswith(".rs")]
    python = [row for row in selected if row["path"].endswith(".py")]
    if not native_rust or not portable_rust:
        raise RuntimeError("exported native or portable Rust selection is unexpectedly empty")
    out.mkdir(parents=True); raw = out / "raw"; raw.mkdir()
    plan = {"schema": "cix-final-sonar-native-v1", "source": str(source), "export_manifest_sha256": sha(manifest),
      "source_tree": language_members, "projects": {
        "cix-final-native-rust": {"root": "rust/cix-native", "sources": native_rust, "required": True,
          "properties": ["sonar.sources=.", "sonar.inclusions=**/*.rs", "sonar.exclusions=target/**,vendor/**,**/.scannerwork/**", "sonar.rust.clippy.enabled=false", "sonar.rust.clippyReport.reportPaths=/out/clippy.jsonl"]},
        "cix-final-portable-rust": {"root": "rust/cix-portable", "sources": portable_rust, "required": True,
          "properties": ["sonar.sources=.", "sonar.inclusions=**/*.rs", "sonar.exclusions=target/**,vendor/**,**/.scannerwork/**", "sonar.rust.clippy.enabled=false", "sonar.rust.clippyReport.reportPaths=/out/clippy.jsonl"]},
        "cix-final-python-export": {"root": ".", "sources": python, "required": bool(python), "optional_binding": True,
          "properties": ["sonar.sources=.", "sonar.inclusions=**/*.py", "sonar.exclusions=**/__pycache__/**,**/*.pyc"]}
      }, "excluded_files": excluded,
      "images": {"server": SERVER, "scanner": SCANNER}}
    save(out / "plan.json", plan)

def request(h, base, password, endpoint, fields=None):
    return h.api(base, endpoint, "admin", password, urllib.parse.urlencode(fields).encode() if fields else None)

def indexed(h, base, password, key):
    rows=[]; page=1
    while True:
        doc=request(h, base, password, f"/api/components/tree?component={key}&qualifiers=FIL&ps=500&p={page}")
        rows += doc.get("components", [])
        if len(rows) >= doc.get("paging",{}).get("total",0): return rows
        page += 1

def worker(prepared: Path, out: Path, clippy: Path, native_receipt: Path, portable_clippy: Path, portable_receipt: Path, parent: str) -> None:
    cxx, h = load("cix_sonar_cxx_guard", CXX), load("cix_sonar_hygiene", HYGIENE / "run_scan.py")
    plan=json.loads((prepared/"plan.json").read_text()); source=Path(plan["source"])
    native_clippy=verify_clippy(clippy,native_receipt,source/"rust/cix-native")
    portable_clippy_binding=verify_clippy(portable_clippy,portable_receipt,source/"rust/cix-portable")
    # Re-derive selection so a changed export cannot inherit a clean result.
    scratch=out.parent/(out.name+".selection-check"); prepare(source, scratch)
    refreshed=json.loads((scratch/"plan.json").read_text())
    for field in ("export_manifest_sha256","source_tree","projects","excluded_files"):
        if refreshed[field] != plan[field]: raise RuntimeError("export identity or selection changed after preparation: "+field)
    import shutil; shutil.rmtree(scratch)
    budget=cxx.EvidenceBudget(out); budget.mkdir(out); raw=out/"raw"; budget.mkdir(raw)
    for label,image in (("server",SERVER),("scanner",SCANNER)): budget.write_text(raw/(label+"-image-inspect.json"),h.image_receipt(image))
    expected_plugin_rows=expected_plugins(cxx)
    # Admission uses the inventory sizes before the staging directory is made.
    # The copy happens only after the shared 4 GB policy accepts that reservation.
    cxx.save(raw/"temporary-accounting-prestage.json",temporary_accounting(cxx,expected_plugin_rows),budget)
    plugin_stage=out.parent/(out.name+".language-plugins")
    plugins=stage_language_plugins(plugin_stage,expected_plugin_rows); cxx.save(raw/"language-plugin-inventory.json",plugins,budget)
    cxx.save(raw/"temporary-accounting.json",temporary_accounting(cxx,plugins),budget)
    cxx.save(raw/"clippy-bindings.json",{"native":native_clippy,"portable":portable_clippy_binding},budget)
    base, server="http://127.0.0.1:9018", "cix-final-native-sonarqube"; password="Aa1!"+secrets.token_urlsafe(32); token=None; env=raw/".scanner-env"; result={"status":"STARTED","projects":{}}
    server_options, server_command, server_receipt=cxx.server_start_contract()
    cxx.save(raw/"server-start-contract.json",server_receipt,budget)
    try:
        empty=raw/"empty-core-extensions"; budget.mkdir(empty); empty.chmod(0o555)
        cxx.save(raw/"language-plugin-overlay.json",{"empty_core_extensions":str(empty),"mounted_plugins":plugins,"purpose":"language-enabled Rust/Python-only server; CXX and unrelated built-ins absent"},budget)
        h.docker_run(server, SERVER, h.SERVER_MEMORY, parent, ["-p","127.0.0.1:9018:9000",*server_options,"-v",f"{empty}:/opt/sonarqube/lib/extensions:ro","-v",f"{plugin_stage}:/opt/sonarqube/extensions/plugins:ro"],server_command)
        cxx.wait_server_or_exit(h,base,password,server)
        languages=request(h,base,password,"/api/languages/list"); cxx.save(raw/"languages.json",languages,budget); active={x["key"] for x in languages.get("languages",[])}
        if not {"rust","python"}.issubset(active): raise RuntimeError("pinned language-enabled server lacks Rust or Python")
        token=request(h,base,password,"/api/user_tokens/generate",{"name":"cix-final-native"})["token"]; budget.write_text(env,f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"); os.chmod(env,0o600)
        for key, project in plan["projects"].items():
            if not project["required"]: result["projects"][key]={"status":"NOT_SELECTED"}; continue
            project_out=out/key; budget.mkdir(project_out); root=source/project["root"]; props=[f"sonar.projectKey={key}","sonar.scm.disabled=true","sonar.scm.exclusions.disabled=true","sonar.working.directory=/tmp/.scannerwork",*project["properties"]]
            vendor_exclusions=[row["path"] for row in plan["excluded_files"] if row["path"].endswith(".py")]
            if key == "cix-final-python-export" and vendor_exclusions:
                props.append("sonar.exclusions=" + ",".join(vendor_exclusions + ["**/__pycache__/**","**/*.pyc"]))
            budget.write_text(project_out/"properties","\n".join(props)+"\n")
            if key == "cix-final-native-rust": budget.write_bytes(project_out/"clippy.jsonl",clippy.read_bytes())
            if key == "cix-final-portable-rust": budget.write_bytes(project_out/"clippy.jsonl",portable_clippy.read_bytes())
            # Reuse the CXX runner's read-only bounded scanner wrapper: its
            # only writable paths are the declared tmpfs and capped evidence bind.
            task=cxx.bounded_scanner(h,base,password,token,env,parent,key,root,project_out,budget)
            cxx.collect(h,base,key,task,password,project_out,budget); files=indexed(h,base,password,key); cxx.save(project_out/"indexed-files.json",files,budget)
            expected={x["path"] for x in project["sources"]}; got={x.get("path","") for x in files}
            if not expected or got != expected: raise RuntimeError(key+": Sonar indexed-file selection differs from manifest")
            result["projects"][key]={"status":"SCANNED","expected_files":len(expected),"indexed_files":len(files),"issues":json.loads((project_out/"issues.json").read_text())["paging"]["total"],"quality_gate":json.loads((project_out/"quality-gate.json").read_text())}
        result["status"]="SCANNED_WITH_RECORDED_FINDINGS"; cxx.save_terminal_result(out/"result.json",result,budget)
    except Exception as e:
        result.update(status="FAILED",error=h.scrub(str(e),[password,token])); cxx.save_terminal_result(out/"result.json",result,budget); raise
    finally:
        if token:
            try: request(h,base,password,"/api/user_tokens/revoke",{"name":"cix-final-native"})
            except Exception: pass
        if env.exists(): env.unlink()
        try:
            budget.write_text(raw/"server.log",cxx.bounded_server_log(server,budget,h,[password,token]),failure=True)
        finally:
            h.stop(server)
            shutil.rmtree(plugin_stage,ignore_errors=True)

def run(prepared: Path, out: Path, clippy: Path, native_receipt: Path, portable_clippy: Path, portable_receipt: Path) -> None:
    cxx=load("cix_sonar_cxx_guard",CXX); sched=load("cix_sonar_scheduler",HYGIENE/"schedule_scan.py")
    cxx.require_stopped_confirmation(STOP_SUMMARY)
    if out.exists(): raise RuntimeError("refusing to overwrite a scan attempt")
    scheduler=sched.WaveScheduler(ROOT,max_jobs=1,max_memory_bytes=SERVER_MEMORY+SCANNER_MEMORY,max_temp_bytes=TEMP_BUDGET); scheduler.state.mkdir(exist_ok=True)
    parent,anchor="cix-final-native-sonar.slice","cix-final-native-sonar-anchor"
    import fcntl
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); leases=scheduler._lease_cores([{"physical_core":[sched._core(c) for c in CPUS]}])
        try:
            cxx.assert_benchmark_idle(); sched._make_slice(parent,anchor); receipt=sched._slice_receipt(parent); sched._verify_slice(receipt)
            outer_budget=cxx.EvidenceBudget(out); outer_budget.mkdir(out); outer_budget.write_text(out/"slice-receipt.txt",receipt)
            cmd=["sudo","-n","systemd-run","--uid",str(os.getuid()),"--gid",str(os.getgid()),"--wait","--pipe","--collect","--slice",parent,sys.executable,str(Path(__file__).resolve()),"worker","--prepared",str(prepared),"--out",str(out),"--clippy-json",str(clippy),"--native-clippy-receipt",str(native_receipt),"--portable-clippy-json",str(portable_clippy),"--portable-clippy-receipt",str(portable_receipt)]
            if subprocess.run(cmd,timeout=21600).returncode: raise RuntimeError("final Sonar failed; retain attempt evidence")
        finally:
            subprocess.run(["sudo","-n","systemctl","stop",anchor],check=False,capture_output=True)
            for lease in leases: lease.close()

def main():
    p=argparse.ArgumentParser(); p.add_argument("action",choices=("prepare","run","worker")); p.add_argument("--source",type=Path); p.add_argument("--prepared",type=Path); p.add_argument("--out",type=Path,required=True); p.add_argument("--clippy-json",type=Path); p.add_argument("--native-clippy-receipt",type=Path); p.add_argument("--portable-clippy-json",type=Path); p.add_argument("--portable-clippy-receipt",type=Path); a=p.parse_args()
    if a.action=="prepare": prepare(a.source.resolve(),a.out.resolve())
    elif a.action=="run": run(a.prepared.resolve(),a.out.resolve(),a.clippy_json.resolve(),a.native_clippy_receipt.resolve(),a.portable_clippy_json.resolve(),a.portable_clippy_receipt.resolve())
    else:
        parent="cix-final-native-sonar.slice"
        if parent not in Path("/proc/self/cgroup").read_text(): raise RuntimeError("worker is outside reserved aggregate slice")
        load("cix_sonar_cxx_guard",CXX).require_stopped_confirmation(STOP_SUMMARY); worker(a.prepared.resolve(),a.out.resolve(),a.clippy_json.resolve(),a.native_clippy_receipt.resolve(),a.portable_clippy_json.resolve(),a.portable_clippy_receipt.resolve(),parent)
if __name__=="__main__": main()
