#!/usr/bin/env python3
"""Private, opt-in release benchmark plan and cell driver.

This program deliberately has no default execution path.  ``prepare`` freezes
the selected original inputs and release identity; ``run`` dispatches those
already-frozen cells through this directory's root-owned ``schedule.py``.
"""
from __future__ import annotations

import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
GIB = 1024 ** 3
PROFILES = {"fast": ["--fast"], "default": [], "best": ["--best"]}
MAX_ARCHIVE = 3_900_000_000
TEMP_CAP = 4_000_000_000
CPUS = [8, 10, 12, 14]

def now(): return datetime.now(timezone.utc).isoformat()
def canon(x): return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()
def dump(p, x): p.write_bytes(canon(x) + b"\n")
def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def stat_hash(p):
    p=Path(p); return {"path":str(p.resolve()),"bytes":p.stat().st_size,"sha256":sha(p)}
def tree_manifest(root):
    root=Path(root).resolve()
    if not root.is_dir(): raise RuntimeError(f"source export is not a directory: {root}")
    rows=[]
    for p in sorted(root.rglob("*")):
        rel=p.relative_to(root)
        if p.is_file() and not {".git","target","__pycache__"}.intersection(rel.parts): rows.append({"path":str(rel),"bytes":p.stat().st_size,"sha256":sha(p)})
    return {"root":str(root),"files":rows,"sha256":hashlib.sha256(canon(rows)).hexdigest()}
def dsos(binary):
    r=subprocess.run(["ldd",str(binary)],text=True,capture_output=True,check=False)
    found=[]
    for line in r.stdout.splitlines():
        if "=>" in line:
            q=line.split("=>",1)[1].strip().split(" ",1)[0]
            if q.startswith("/") and Path(q).is_file(): found.append(stat_hash(q))
    return sorted(found,key=lambda x:x["path"])
def release_meta(release_root, source_export):
    root=Path(release_root).resolve(); cix=root/"cix"; uncix=root/"uncix"
    for p in (cix,uncix):
        if not p.is_file() or not os.access(p,os.X_OK): raise RuntimeError(f"missing executable: {p}")
    return {"release_root":str(root),"cix":stat_hash(cix),"uncix":stat_hash(uncix),
            "release_files":sorted([stat_hash(p) for p in root.iterdir() if p.is_file()],key=lambda x:x["path"]),
            "runtime_dsos":{"cix":dsos(cix),"uncix":dsos(uncix),
                            "loader":stat_hash("/lib64/ld-linux-x86-64.so.2") if Path("/lib64/ld-linux-x86-64.so.2").is_file() else None},
            "source_export":tree_manifest(source_export)}

def members(item):
    root=Path(item.get("root", ""))
    if item.get("member_selector"):
        s=item["member_selector"]; d=json.loads(Path(s["manifest"]).read_text())
        v=d
        for q in s["object"].split("."): v=v[q]
        return [{"label":f"{item['id']}/{x['name']}","path":x["path"],"bytes":x["bytes"],"sha256":x["sha256"],"aliases":[]} for x in v if x.get("status")==s["status"]]
    if "path" in item: return [{"label":item["id"],"path":item["path"],"bytes":item["bytes"],"sha256":item["sha256"],"aliases":[]}]
    return [{"label":f"{item['id']}/{m if isinstance(m,str) else m['name']}","path":str(root/(m if isinstance(m,str) else m.get("path",m["name"]))),"bytes":(m.get("bytes") if isinstance(m,dict) else None),"sha256":(m.get("sha256") if isinstance(m,dict) else None),"aliases":[]} for m in item.get("members",[])]
def inventory(path):
    d=json.loads(Path(path).read_text()); out=[]
    for x in d["inventory"]:
        if not str(x.get("status","READY")).startswith("READY"): continue
        for a in members(x):
            p=Path(a["path"])
            if not p.is_file(): a["availability"]="MISSING_AT_FREEZE"; out.append(a); continue
            actual={"bytes":p.stat().st_size,"sha256":sha(p)}
            if a["bytes"] is not None and (a["bytes"]!=actual["bytes"] or a["sha256"]!=actual["sha256"]):
                a["availability"]="IDENTITY_MISMATCH"; a["actual"]=actual; out.append(a); continue
            a.update(actual); a["availability"]="READY"; out.append(a)
    # physical source identity wins; labels remain aliases so no duplicate compression is run.
    unique={}
    for a in out:
        if a["availability"]!="READY": continue
        k=(a["bytes"],a["sha256"])
        if k in unique: unique[k]["aliases"].append(a["label"])
        else: unique[k]=a
    gate=("canterbury-11/", "calgary-14/", "canterbury-artificial-4/")
    return sorted(unique.values(),key=lambda x:(0 if x["label"].startswith(gate) else 1,x["label"])), [a for a in out if a["availability"]!="READY"]
def wall(n, profile):
    if profile != "best":
        return min(1800, max(300, 1800 * max(1,n) // (128 << 20)))
    # Match the inspected shipped whole-file native search allowance, then
    # reserve 10 minutes for other candidates, restore and receipt generation.
    # Larger streaming inputs retain the original two-hour cap.
    scaled=min(7200, max(1800, 7200 * max(1,n) // (128 << 20)))
    if n <= (128 << 20):
        native=900 + min(2700, (n // (1 << 20)) * 30)
        return max(scaled, native + 600)
    return scaled
def plan(area, release, assets):
    cells=[]
    for a in assets:
        for profile, flags in PROFILES.items():
            ident=hashlib.sha256(canon([a["sha256"],profile,release["cix"]["sha256"]])).hexdigest()[:20]
            cells.append({"id":f"rel01-{profile}-{ident}","asset":a,"profile":profile,"flags":flags+["--threads","4","-f"],
                          "budget":{"wall_seconds":wall(a["bytes"],profile),"memory_bytes":10*GIB,"temp_bytes":TEMP_CAP,"cpus":CPUS},"status":"PENDING"})
    return {"schema":"cix.release-0.1.benchmark-plan.v1","prepared_at":now(),"status":"PREPARED_NOT_EXECUTED","release":release,
            "policy":{"profiles":"FAST, DEFAULT and BEST use their exact native CLI effort flags and ship defaults; BEST is never replaced by a constrained label","threads":4,"cli_memory":"native defaults: FAST/DEFAULT 512MiB; BEST/decode 2GiB","cgroup_memory_bytes":10*GIB,"cpus":CPUS,"archive_temp_cap_bytes":MAX_ARCHIVE,"temporary_cap_bytes":TEMP_CAP,"decode":"fresh uncix process writes stdout to a SHA-256 sink; no restored file is materialized","gate":"Canterbury, Calgary and Artificial cells must complete compatibly before Silesia and all later cells"},"cells":cells}

def prepare(a):
    out=Path(a.area).resolve()
    if out.exists(): raise RuntimeError("benchmark area exists; preserve frozen evidence")
    assets, missing=inventory(a.inventory); rel=release_meta(a.release_root,a.source_export)
    out.mkdir(parents=True); dump(out/"plan.json",plan(out,rel,assets)); dump(out/"excluded-at-freeze.json",{"missing":missing})
    print(json.dumps({"prepared":str(out),"physical_assets":len(assets),"cells":len(assets)*3},sort_keys=True))

def checked_release(m, check_source=False):
    for x in (m["cix"],m["uncix"]):
        if stat_hash(x["path"]) != x: raise RuntimeError("release binary changed after plan freeze")
    if check_source and tree_manifest(m["source_export"]["root"])["sha256"]!=m["source_export"]["sha256"]: raise RuntimeError("source export changed after plan freeze")
    loader=m["runtime_dsos"].get("loader")
    if loader and stat_hash(loader["path"])!=loader: raise RuntimeError("runtime loader changed after plan freeze")
    for entries in (m["runtime_dsos"]["cix"],m["runtime_dsos"]["uncix"]):
        for entry in entries:
            if stat_hash(entry["path"])!=entry: raise RuntimeError("runtime DSO changed after plan freeze")

def gnutime(path):
    raw=Path(path).read_text(errors="replace"); fields={}
    for line in raw.splitlines():
        if ": " in line: k,v=line.split(": ",1); fields[k.strip()]=v.strip()
    needed=["User time (seconds)","System time (seconds)","Elapsed (wall clock) time (h:mm:ss or m:ss)","Maximum resident set size (kbytes)"]
    if any(k not in fields for k in needed): raise RuntimeError("incomplete GNU time evidence")
    return fields
def safe_gnutime(path):
    try: return gnutime(path)
    except (OSError, RuntimeError): return None
def child(spec):
    s=json.loads(Path(spec).read_text()); cell=s["cell"]; work=Path(s["work"]); work.mkdir(parents=True,exist_ok=False); checked_release(s["release"])
    src=Path(cell["asset"]["path"])
    if not src.is_file() or src.stat().st_size!=cell["asset"]["bytes"] or sha(src)!=cell["asset"]["sha256"]: raise RuntimeError("source identity changed")
    archive=work/"archive.cix"; enc=work/"encode.gnu-time.txt"; dec=work/"decode.gnu-time.txt"
    cmd=["/usr/bin/time","-v","-o",str(enc),s["release"]["cix"]["path"],*cell["flags"],"-o",str(archive),str(src)]
    e=subprocess.run(cmd,text=True,capture_output=True); (work/"encode.stderr.txt").write_text(e.stderr)
    if e.returncode:
        if archive.exists(): archive.unlink()
        return dump(work/"result.json",{"status":"RESOURCE_OR_ENCODE_FAILURE","encode_gnu_time":safe_gnutime(enc),"stderr":e.stderr})
    if not archive.is_file() or archive.stat().st_size>MAX_ARCHIVE:
        size=archive.stat().st_size if archive.is_file() else None
        if archive.is_file(): archive.unlink()
        return dump(work/"result.json",{"status":"ARCHIVE_TEMP_CAP_EXCEEDED","archive_bytes_before_cleanup":size,"encode_gnu_time":safe_gnutime(enc)})
    ah=sha(archive); checked_release(s["release"])
    # stdout is consumed by the hash sink, providing archive-only fresh decode verification without a restored temp file.
    p=subprocess.Popen(["/usr/bin/time","-v","-o",str(dec),s["release"]["uncix"]["path"],"-c",str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    h=hashlib.sha256()
    while b:=p.stdout.read(1<<20): h.update(b)
    stderr=p.stderr.read().decode(errors="replace"); rc=p.wait(); (work/"decode.stderr.txt").write_text(stderr)
    if rc:
        dump(work/"result.json",{"status":"DECODE_CORRECTNESS_FAILURE","archive":{"bytes":archive.stat().st_size,"sha256":ah},"decode_gnu_time":safe_gnutime(dec),"stderr":stderr})
        raise RuntimeError("DECODE_CORRECTNESS_FAILURE")
    result={"status":"VERIFIED" if h.hexdigest()==cell["asset"]["sha256"] else "RESTORE_HASH_MISMATCH","asset":cell["asset"],"profile":cell["profile"],"archive":{"bytes":archive.stat().st_size,"sha256":ah,"percent":archive.stat().st_size*100/cell["asset"]["bytes"]},"restore_sha256":h.hexdigest(),"encode_gnu_time":safe_gnutime(enc),"decode_gnu_time":safe_gnutime(dec)}
    dump(work/"result.json",result)
    if result["status"]!="VERIFIED": raise RuntimeError("RESTORE_HASH_MISMATCH")
    archive.unlink()  # preserve the complete archive hash/size receipt, not multi-cell archive spools.

def run(a):
    area=Path(a.area).resolve(); p=json.loads((area/"plan.json").read_text()); checked_release(p["release"],check_source=True)
    for n,cell in enumerate(p["cells"]):
        # Mandatory corpus gate: CCA must verify before every non-CCA corpus, including Silesia.
        group=cell["asset"]["label"].split("/",1)[0]
        gate_rows=[json.loads((area/"results"/x["id"] / "work" / "result.json").read_text()) for x in p["cells"] if x["asset"]["label"].split("/",1)[0] in {"canterbury-11","calgary-14","canterbury-artificial-4"} and (area/"results"/x["id"] / "work" / "result.json").is_file()]
        if group not in {"canterbury-11","calgary-14","canterbury-artificial-4"} and (len(gate_rows)!=sum(x["asset"]["label"].split("/",1)[0] in {"canterbury-11","calgary-14","canterbury-artificial-4"} for x in p["cells"]) or any(r["status"]!="VERIFIED" for r in gate_rows)): raise RuntimeError("CCA qualification incomplete or resource-limited")
        cellout=area/"results"/cell["id"]
        receipt=cellout/"work"/"result.json"
        if receipt.is_file():
            prior=json.loads(receipt.read_text()).get("status")
            if prior in {"VERIFIED","RESOURCE_OR_ENCODE_FAILURE","ARCHIVE_TEMP_CAP_EXCEEDED","SCHEDULER_RESOURCE_OR_TIMEOUT"}: continue
            raise RuntimeError(f"non-resumable correctness terminal: {cell['id']} ({prior})")
        if cellout.exists(): raise RuntimeError("incomplete or failed cell exists; inspect its immutable receipt")
        spec={"id":cell["id"],"cpus":CPUS,"work":str(cellout),"input_bytes":cell["asset"]["bytes"],"wall_seconds":cell["budget"]["wall_seconds"],"memory_bytes":cell["budget"]["memory_bytes"],"temp_bytes":cell["budget"]["temp_bytes"],"command":[sys.executable,str(Path(__file__).resolve()),"child",str(cellout.parent/(cell["id"]+".spec.json"))]}
        sp=cellout.parent/(cell["id"]+".spec.json"); sp.parent.mkdir(parents=True,exist_ok=True); dump(sp,{"cell":cell,"release":p["release"],"work":str(cellout/"work")});
        # schedule consumes a separate spec; write it only after the immutable child spec.
        dump(sp.with_suffix(".schedule.json"),spec)
        r=subprocess.run([sys.executable,str(AREA/"schedule.py"),str(sp.with_suffix(".schedule.json"))])
        if r.returncode:
            if receipt.is_file() and json.loads(receipt.read_text()).get("status") in {"RESOURCE_OR_ENCODE_FAILURE","ARCHIVE_TEMP_CAP_EXCEEDED"}: continue
            if not receipt.exists():
                partial=cellout/"work"/"archive.cix"
                if partial.is_file(): partial.unlink()
                for temp in (cellout/"work").glob(".archive.cix.cix-tmp-*"):
                    if temp.is_file(): temp.unlink()
                receipt.parent.mkdir(parents=True,exist_ok=True)
                dump(receipt,{"status":"SCHEDULER_RESOURCE_OR_TIMEOUT","ranked":False,"cell":cell["id"],"note":"scheduler terminal failed before a child receipt; later independent cells may continue"})
                continue
            raise RuntimeError(f"correctness or unrecorded terminal failure: {cell['id']}")

def main():
    q=argparse.ArgumentParser(); sub=q.add_subparsers(dest="op",required=True)
    for n in ("prepare","run"):
        x=sub.add_parser(n); x.add_argument("--area",type=Path,required=True); x.add_argument("--release-root",type=Path,required=True); x.add_argument("--source-export",type=Path,required=True); x.add_argument("--inventory",type=Path,default=AREA/"local-assets.json")
    x=sub.add_parser("child"); x.add_argument("spec")
    a=q.parse_args()
    if a.op=="child": return child(a.spec)
    return {"prepare":prepare,"run":run}[a.op](a)
if __name__=="__main__":
    try: main()
    except Exception as e: print(str(e),file=sys.stderr); raise
