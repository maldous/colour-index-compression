"""Validate include rebasing on retained first-party adapter compilation records."""
import collections, hashlib, importlib.util, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
DB=ROOT/"docs/research/2026-10-04-execution/sonar-preparation/prepared-v6/compile_commands.host.json"
TOOL=ROOT/"tools/sonar-cxx/include_context.py"
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1": raise RuntimeError("root lease required")
    identities={str(p.relative_to(ROOT)):digest(p) for p in (DB,TOOL)}
    for p in (DB,TOOL):
        (OUT/(p.name+".txt")).write_bytes(p.read_bytes())
    spec=importlib.util.spec_from_file_location("include_context",TOOL)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    prefixes=tuple(str(ROOT/"rust/cix-native"/x)+"/" for x in ("adapters","bindings","packaging","tests"))
    rows=[r for r in json.loads(DB.read_text()) if r["file"].startswith(prefixes)]
    if not rows: raise RuntimeError("no retained adapter records")
    receipt={"status":"started", "scope":"recorded include mapping validation only; no new compiler or analyzer execution", "input_sha256":identities,"records":len(rows)}
    try:
        mapped,mounts,evidence=module.rebase_include_context(rows,ROOT)
        for entry in evidence:
            if not entry["mapped"]: continue
            mapped_path=entry["mapped"]
            targets=[(host,dest) for host,dest in mounts if mapped_path==dest or mapped_path.startswith(dest+"/")]
            if targets:
                host,dest=max(targets,key=lambda x:len(x[1])); actual=host/mapped_path[len(dest):].lstrip("/")
            elif mapped_path.startswith("/usr/src/"): actual=ROOT/mapped_path[len("/usr/src/"):]
            else: raise RuntimeError("mapped operand has no mounted identity: "+mapped_path)
            if actual.resolve()!=Path(entry["resolved"]): raise RuntimeError("mapped operand differs from canonical recorded target")
            if not actual.exists(): raise RuntimeError("mapped input does not exist")
        (OUT/"mapped-commands.json").write_text(json.dumps(mapped,indent=2)+"\n")
        (OUT/"operand-evidence.json").write_text(json.dumps(evidence,indent=2)+"\n")
        (OUT/"mounts.json").write_text(json.dumps([{"host":str(h),"container":d,"read_only":True} for h,d in mounts],indent=2)+"\n")
        receipt["dispositions"]=dict(collections.Counter(r["disposition"] for r in evidence))
        receipt["mounts"]=len(mounts)
        receipt["inputs_unchanged"]=identities=={str(p.relative_to(ROOT)):digest(p) for p in (DB,TOOL)}
        if not receipt["inputs_unchanged"]: raise RuntimeError("inputs changed")
        receipt["status"]="pass_scoped_mapping"
    except Exception as e:
        receipt["status"]="fail";receipt["error"]=str(e);raise
    finally:(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
if __name__=="__main__":main()
