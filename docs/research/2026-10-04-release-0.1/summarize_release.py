#!/usr/bin/env python3
"""Summarize an already-frozen release benchmark; never execute benchmark work."""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROFILES=("fast","default","best")
def dump(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
def load(p): return json.loads(Path(p).read_text())
def norm(cell, result, scheduler):
    a=cell["asset"]; r=result or {}; arc=r.get("archive",{}); enc=r.get("encode_gnu_time") or {}; dec=r.get("decode_gnu_time") or {}
    child_status=r.get("status","PENDING"); status=child_status
    # A child hash is useful diagnostic evidence only.  Ranking requires the
    # enclosing scheduler receipt to prove a clean, cgroup-verified phase.
    if child_status=="VERIFIED":
      if scheduler is None: status="PENDING"
      elif not (scheduler.get("exit_code")==0 and scheduler.get("cgroup_verified") is True and scheduler.get("stop_reason") is None): status="SCHEDULER_UNVERIFIED"
    ranked=status=="VERIFIED"
    n=a["bytes"]; b=arc.get("bytes") if ranked else None
    return {"dataset":a["label"].split("/",1)[0],"label":a["label"],"aliases":a.get("aliases",[]),"original_bytes":n,
      "status":status,"child_status":child_status,"ranked":ranked,"archive_bytes":b,"percent":(b*100/n if b is not None else None),"archive_sha256":arc.get("sha256") if ranked else None,
      "encode_wall":enc.get("Elapsed (wall clock) time (h:mm:ss or m:ss)"),"encode_user":enc.get("User time (seconds)"),"encode_system":enc.get("System time (seconds)"),"encode_rss_kib":enc.get("Maximum resident set size (kbytes)"),
      "decode_wall":dec.get("Elapsed (wall clock) time (h:mm:ss or m:ss)"),"decode_user":dec.get("User time (seconds)"),"decode_system":dec.get("System time (seconds)"),"decode_rss_kib":dec.get("Maximum resident set size (kbytes)"),"scheduler_receipt":scheduler,"child_diagnostics":{"status":child_status,"scheduler_child_status":(scheduler or {}).get("child_status")}}
def num(x):
 try:return float(x)
 except (TypeError,ValueError):return None
def wall(x):
 try:
  q=[float(v) for v in str(x).split(":")]; return sum(v*60**i for i,v in enumerate(reversed(q)))
 except (TypeError,ValueError): return None
def main():
 p=argparse.ArgumentParser();p.add_argument("--benchmark",type=Path);p.add_argument("--output",type=Path);p.add_argument("--public-records",type=Path,default=HERE/"public-records.json");p.add_argument("--selfcheck",action="store_true");a=p.parse_args()
 if a.selfcheck:
  c={"asset":{"label":"fixture/x","aliases":[],"bytes":100}}; r={"status":"VERIFIED","archive":{"bytes":25,"sha256":"x"},"encode_gnu_time":{},"decode_gnu_time":{}}
  z=norm(c,r,{"exit_code":0,"cgroup_verified":True,"stop_reason":None})
  bad=norm(c,r,{"exit_code":1,"cgroup_verified":True,"stop_reason":None}); missing=norm(c,r,None)
  assert z["percent"]==25 and z["status"]=="VERIFIED" and bad["status"]=="SCHEDULER_UNVERIFIED" and bad["archive_bytes"] is None and missing["status"]=="PENDING"; return
 if not a.benchmark or not a.output: p.error("--benchmark and --output are required unless --selfcheck")
 plan=load(a.benchmark/"plan.json"); records={x["dataset_id"]:x for x in load(a.public_records)["records"]}; rows=[]
 for c in plan["cells"]:
  rp=a.benchmark/"results"/c["id"] / "work" / "result.json"; sp=HERE/"raw"/c["id"] / "result.json"
  rows.append((c["profile"],norm(c,load(rp) if rp.is_file() else None,load(sp) if sp.is_file() else None)))
 grouped=defaultdict(dict)
 for prof,row in rows: grouped[row["label"]][prof]=row
 flat=[]
 for label,by in sorted(grouped.items()):
  first=next(iter(by.values()))
  # One physical result expands to each official corpus member label.  This is
  # required for byte-identical ptt5/pic while preserving 11- and 14-member totals.
  for logical in [label,*first["aliases"]]:
   dataset=logical.split("/",1)[0]
   entry={"dataset":dataset,"label":logical,"physical_label":label,"physical_input_count":1,"original_bytes":first["original_bytes"],"profiles":{q:by.get(q,{"status":"PENDING"}) for q in PROFILES}}
   if logical.endswith("/enwik8"): entry["public_record"]=records.get("enwik8")
   if logical.endswith("/enwik9"): entry["public_record"]=records.get("enwik9")
   flat.append(entry)
 totals=[]
 for dataset in sorted({x["dataset"] for x in flat}):
  if dataset=="canterbury-artificial-4": continue
  members=[x for x in flat if x["dataset"]==dataset]
  for prof in PROFILES:
   states=[x["profiles"][prof]["status"] for x in members]
   verified=all(x=="VERIFIED" for x in states)
   t={"dataset":dataset,"profile":prof,"members":len(members),"original_bytes":sum(x["original_bytes"] for x in members),"status":"VERIFIED" if verified else "INCOMPLETE", "archive_bytes":sum(x["profiles"][prof]["archive_bytes"] for x in members) if verified else None}
   if dataset in records: t["public_record"]=records[dataset]
   if verified:
    rows_for_profile=[x["profiles"][prof] for x in members]
    for key,out,fn in (("encode_user","encode_user_seconds",sum),("encode_system","encode_system_seconds",sum),("decode_user","decode_user_seconds",sum),("decode_system","decode_system_seconds",sum),("encode_rss_kib","encode_peak_rss_kib",max),("decode_rss_kib","decode_peak_rss_kib",max)):
     vals=[num(x.get(key)) for x in rows_for_profile]
     if all(v is not None for v in vals): t[out]=fn(vals)
    for key,out in (("encode_wall","encode_wall_seconds"),("decode_wall","decode_wall_seconds")):
     vals=[wall(x.get(key)) for x in rows_for_profile]
     if all(v is not None for v in vals): t[out]=sum(vals)
   totals.append(t)
 for x in totals:
  if x["archive_bytes"] is not None:x["percent"]=x["archive_bytes"]*100/x["original_bytes"]
 physical=len(grouped); logical=len(flat)
 output={"schema":"cix.release-0.1.summary.v1","benchmark_schema":plan.get("schema"),"release":plan.get("release"),"counts":{"physical_inputs":physical,"logical_members":logical},"policy":"Rows are physical deduplicated measurements expanded to logical corpus memberships for totals. Artificial is per-file only. Public Silesia aggregate is attached only to the Silesia total, never member rows. Hutter totals include program plus archive and are not direct archive comparisons.","runtime_references":plan.get("release",{}).get("runtime_dsos"),"rows":flat,"totals":totals}
 a.output.mkdir(parents=True,exist_ok=True);dump(a.output/"results.json",output)
 fields=["dataset","label","original_bytes","status","archive_bytes","percent","archive_sha256","record_winner","record_archive_bytes","record_total_bytes","record_scope","record_source","encode_wall","encode_user","encode_system","encode_rss_kib","decode_wall","decode_user","decode_system","decode_rss_kib"]
 with (a.output/"results.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=["profile",*fields]);w.writeheader()
  for x in flat:
    for q in PROFILES:
     r=x.get("public_record",{}); row={k:x["profiles"][q].get(k) if k not in ("dataset","label","original_bytes") else x.get(k) for k in fields}
     row.update({"record_winner":r.get("winner"),"record_archive_bytes":r.get("archive_bytes"),"record_total_bytes":r.get("total_bytes"),"record_scope":r.get("method_scope"),"record_source":r.get("record_source")}); w.writerow({"profile":q,**row})
 with (a.output/"totals.csv").open("w",newline="") as f:
  fields=["dataset","profile","members","original_bytes","status","archive_bytes","percent","encode_wall_seconds","encode_user_seconds","encode_system_seconds","encode_peak_rss_kib","decode_wall_seconds","decode_user_seconds","decode_system_seconds","decode_peak_rss_kib","record_winner","record_archive_bytes","record_total_bytes","record_scope","record_source"]
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader()
  for x in totals:
   r=x.get("public_record",{}); w.writerow({k:v for k,v in {**x,"record_winner":r.get("winner"),"record_archive_bytes":r.get("compressed_bytes",r.get("archive_bytes")),"record_total_bytes":r.get("total_bytes"),"record_scope":r.get("method_scope"),"record_source":r.get("record_source")}.items() if k in fields})
 lines=["# Release benchmark results","",f"Physical inputs: {physical}; logical corpus members: {logical}. Rows remain **PENDING** until a frozen cell receipt exists. Archive sizes are complete CIX bytes; timing is GNU `time -v` evidence. Time fields have 0.01-second reporting resolution; 0.00 does not imply zero runtime. Corpus times sum rounded member observations.","","## Aggregate corpus results","","| Dataset | Record winner / bytes / scope | Original | Profile | CIX bytes (%) | Encode wall seconds / CPU user+sys seconds / RSS KiB | Decode wall seconds / CPU user+sys seconds / RSS KiB |","| --- | --- | ---: | --- | --- | --- | --- |"]
 for x in totals:
  r=x.get("public_record",{}); rb=r.get("compressed_bytes",r.get("total_bytes")); record="—" if not r else f"{r.get('winner','unavailable')} / {rb or 'n/a'} / {r.get('method_scope','')}"
  cix=f"{x['archive_bytes']} ({x.get('percent',0):.3f}%)" if x.get("status")=="VERIFIED" else x["status"]
  enc=f"{x.get('encode_wall_seconds','n/a')} / {x.get('encode_user_seconds','n/a')}+{x.get('encode_system_seconds','n/a')} / {x.get('encode_peak_rss_kib','n/a')} KiB"
  dec=f"{x.get('decode_wall_seconds','n/a')} / {x.get('decode_user_seconds','n/a')}+{x.get('decode_system_seconds','n/a')} / {x.get('decode_peak_rss_kib','n/a')} KiB"
  lines.append(f"| {x['dataset']} | {record} | {x['original_bytes']} | {x['profile']} | {cix} | {enc} | {dec} |")
 lines += ["","## Per-input results","","| Dataset | Input | Public record (archive / total) | Bytes | FAST | DEFAULT | BEST |","| --- | --- | --- | ---: | --- | --- | --- |"]
 for x in flat:
  def cell(q):
   z=x["profiles"][q];return f"{z['archive_bytes']} ({z['percent']:.3f}%)" if z.get("status")=="VERIFIED" else z.get("status","PENDING")
  r=x.get("public_record",{}); rec="—" if not r else f"{r.get('winner','unavailable')} ({r.get('archive_bytes','—')} / {r.get('total_bytes','—')})"
  lines.append(f"| {x['dataset']} | {x['label']} | {rec} | {x['original_bytes']} | {cell('fast')} | {cell('default')} | {cell('best')} |")
 (a.output/"RESULTS.md").write_text("\n".join(lines)+"\n")
if __name__=="__main__":main()
