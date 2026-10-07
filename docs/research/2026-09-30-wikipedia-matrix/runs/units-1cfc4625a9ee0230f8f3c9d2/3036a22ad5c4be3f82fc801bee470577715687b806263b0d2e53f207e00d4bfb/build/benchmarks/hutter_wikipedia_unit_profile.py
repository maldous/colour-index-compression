#!/usr/bin/env python3
"""Read-only unit-boundary eligibility profile for future body representations."""
from __future__ import annotations
import argparse, hashlib, json, os, re, statistics, time
from collections import Counter, defaultdict
from pathlib import Path
from benchmarks import hutter_wikipedia_body_lines as body

RANGES=((0,4*1024*1024),(100_000_000,4*1024*1024),(400_000_000,4*1024*1024))
LEX=re.compile(body.TOKEN.pattern+br"|[A-Za-z][A-Za-z'\-]{0,127}",re.I)

def _stats(xs):
    return {"count":len(xs),"min":min(xs) if xs else None,"median":statistics.median(xs) if xs else None,"max":max(xs) if xs else None,"mean":sum(xs)/len(xs) if xs else None}

def complete_bodies(data):
    pos=bid=0
    while True:
        m=body.TEXT_OPEN.search(data,pos)
        if not m:return
        close=data.find(b"</text>",m.end())
        if close<0:return
        yield bid,m.end(),close
        bid+=1;pos=close+7

def newline4096(data):
    for bid,start,end in complete_bodies(data):
        at=start
        for raw in data[start:end].splitlines(keepends=True):
            stop=at+len(raw); core=raw.rstrip(b"\r\n")
            if raw.endswith(b"\n") and 48<=len(core)<=4096: yield at,stop,bid,raw
            at=stop

def paragraphs16384(data):
    for bid,start,end in complete_bodies(data):
        value=data[start:end]; at=0
        for chunk in value.split(b"\n\n"):
            stop=at+len(chunk)
            if 48<=len(chunk)<=16384: yield start+at,start+stop,bid,chunk
            at=stop+2

def sentence_clauses(data):
    boundary=re.compile(br"(?<=[.!?;:])\s+")
    for bid,start,end in complete_bodies(data):
        value=data[start:end]; at=0
        for m in boundary.finditer(value):
            stop=m.end(); raw=value[at:stop]
            if 48<=len(raw)<=16384: yield start+at,start+stop,bid,raw
            at=stop
        raw=value[at:]
        if 48<=len(raw)<=16384: yield start+at,end,bid,raw

def lexical_windows(data, width):
    for bid,start,end in complete_bodies(data):
        value=data[start:end]
        cursor=0
        for line in value.splitlines(keepends=True):
            line_start=cursor; cursor+=len(line)
            tokens=list(LEX.finditer(line))
            for at in range(0,len(tokens)-width+1,width):
                group=tokens[at:at+width]; raw=line[group[0].start():group[-1].end()]
                if len(raw)>=48: yield start+line_start+group[0].start(),start+line_start+group[-1].end(),bid,raw

def _profile(generator,data):
    families=defaultdict(list); units=0;unitbytes=0
    for start,stop,bid,raw in generator(data):
        units+=1;unitbytes+=len(raw); split=body._skeleton(raw)
        if split is not None: families[split[0]].append((start,stop,bid,raw))
    selected=[]; family_sizes=[];distances=[];literal=holes=0
    for sk,members in families.items():
        if len(members)<3 or len({m[2] for m in members})<2 or len({m[3] for m in members})<2:continue
        selected.extend(members);family_sizes.append(len(members)); offsets=sorted(m[0] for m in members);distances.extend(b-a for a,b in zip(offsets,offsets[1:]))
        literal+=sum(len(v) for kind,v in sk if kind==body.LITERAL);holes+=sum(kind!=body.LITERAL for kind,_ in sk)
    return {"segmented_units":units,"segmented_source_bytes":unitbytes,"candidate_families":len(families),"selected_families":len(family_sizes),"selected_members":len(selected),"selected_source_bytes":sum(m[1]-m[0] for m in selected),"family_member_sizes":_stats(family_sizes),"family_distance_bytes":_stats(distances),"dictionary_literal_bytes_preencoding":literal,"dictionary_hole_slots_preencoding":holes,"metadata_and_payload":"NOT_MEASURED_PREENCODING_NOT_GAIN"}

def profile(data):
    specs={"newline_4096":newline4096,"paragraph_blankline_16384":paragraphs16384,"sentence_clause_16384":sentence_clauses,"lexical_window_32":lambda x:lexical_windows(x,32),"lexical_window_64":lambda x:lexical_windows(x,64)}
    return {name:{**_profile(fn,data),"overlap_policy":"units are non-overlapping within each segmentation; categories are alternative views and must not be added"} for name,fn in specs.items()}

def run(input_path,output,budget_seconds=300):
    os.sched_setaffinity(0,{0});started=time.monotonic();rows=[]
    with Path(input_path).open('rb') as f:
        for offset,n in RANGES:
            f.seek(offset);data=f.read(n)
            if len(data)!=n:raise ValueError('input too short')
            rows.append({"offset":offset,"bytes":n,"sha256":hashlib.sha256(data).hexdigest(),"profile":profile(data)})
            if time.monotonic()-started>budget_seconds:raise TimeoutError('budget exhausted')
    root=Path(__file__).resolve().parents[1]
    result={"schema":"cix-hutter-wikipedia-unit-eligibility-v1","status":"READ_ONLY_PREENCODING_PROFILE","input":str(Path(input_path).resolve()),"ranges":[{"offset":x,"bytes":n} for x,n in RANGES],"holdouts_read":False,"backend":"NONE","paq":"NOT_RUN","actual_cpu_affinity":sorted(os.sched_getaffinity(0)),"budget_seconds":budget_seconds,"elapsed_seconds":time.monotonic()-started,"dependencies_sha256":{"benchmarks/hutter_wikipedia_unit_profile.py":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"benchmarks/hutter_wikipedia_body_lines.py":hashlib.sha256((root/'benchmarks/hutter_wikipedia_body_lines.py').read_bytes()).hexdigest()},"regions":rows,"limitations":["No unit was encoded.","Pre-encoding dictionary literal counts exclude descriptors, rules, holes, framing and backend payload.","Alternative segmentations overlap across views and cannot be combined."]}
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--budget-seconds',type=int,default=300);a=p.parse_args();print(json.dumps(run(a.input,a.output,a.budget_seconds),sort_keys=True))
if __name__=='__main__':main()
