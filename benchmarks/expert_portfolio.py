#!/usr/bin/env python3
"""Physical expert-portfolio benchmark on the canonical Canterbury corpus.

CIX-Expert is a container/search concept: it may choose among reversible
prediction transforms and entropy/dictionary backends. XZ/LZMA is comparison
only and is never eligible for CIX selection.

Every selected payload is a real byte string and is round-trip verified.
A small estimated CIX framing overhead is charged to every candidate.
"""

import bz2, gzip, lzma, math, tarfile, urllib.request
from pathlib import Path
from dataclasses import dataclass

import brotli
import pyppmd
import zstandard as zstd

CORPUS_URL = "https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED = {
    "alice29.txt": 152089, "asyoulik.txt": 125179, "cp.html": 24603,
    "fields.c": 11150, "grammar.lsp": 3721, "kennedy.xls": 1029744,
    "lcet10.txt": 426754, "plrabn12.txt": 481861, "ptt5": 513216,
    "sum": 38240, "xargs.1": 4227,
}
# Conservative physical framing estimate per independently coded member:
# codec/transform IDs, params, original length, payload length, checksum.
FRAME_BYTES = 24

@dataclass
class Candidate:
    name: str
    payload: bytes
    decoder: callable

    @property
    def size(self):
        return len(self.payload) + FRAME_BYTES

def identity(data):
    return data

def xor_lag(data, lag):
    if len(data) <= lag:
        return data
    return data[:lag] + bytes(data[i] ^ data[i-lag] for i in range(lag, len(data)))

def sub_lag(data, lag):
    if len(data) <= lag:
        return data
    return data[:lag] + bytes((data[i] - data[i-lag]) & 255 for i in range(lag, len(data)))

def undo_sub_lag(data, lag):
    if len(data) <= lag:
        return data
    out = bytearray(data)
    for i in range(lag, len(out)):
        out[i] = (out[i] + out[i-lag]) & 255
    return bytes(out)

def undo_xor_lag(data, lag):
    if len(data) <= lag:
        return data
    out = bytearray(data)
    for i in range(lag, len(out)):
        out[i] ^= out[i-lag]
    return bytes(out)

def delta32_shuffle(data):
    usable=(len(data)//4)*4
    if usable < 8:
        return data
    vals=[int.from_bytes(data[i:i+4],"little") for i in range(0,usable,4)]
    ds=[vals[0]]
    for a,b in zip(vals,vals[1:]):
        ds.append((b-a)&0xffffffff)
    raw=b"".join(x.to_bytes(4,"little") for x in ds)
    lanes=b"".join(raw[j::4] for j in range(4))
    return lanes+data[usable:]

def undo_delta32_shuffle(data, original_len):
    usable=(original_len//4)*4
    if usable < 8:
        return data[:original_len]
    n=usable//4
    lanes=data[:usable]
    lane_len=n
    raw=bytearray(usable)
    for j in range(4):
        raw[j::4]=lanes[j*lane_len:(j+1)*lane_len]
    ds=[int.from_bytes(raw[i:i+4],"little") for i in range(0,usable,4)]
    vals=[ds[0]]
    for d in ds[1:]:
        vals.append((vals[-1]+d)&0xffffffff)
    restored=b"".join(x.to_bytes(4,"little") for x in vals)+data[usable:]
    return restored[:original_len]

def transforms(data):
    yield ("identity", data, lambda x: x)

    # Cheap lag candidates. Keep enough range to discover short records/periods.
    for lag in (1,2,3,4,5,6,7,8,12,16,24,32,48,64,96,128,192,256):
        if lag < len(data):
            x=xor_lag(data,lag)
            yield (f"xor{lag}",x,lambda y,lag=lag: undo_xor_lag(y,lag))
    for lag in (1,2,4,8,16,32):
        if lag < len(data):
            x=sub_lag(data,lag)
            yield (f"sub{lag}",x,lambda y,lag=lag: undo_sub_lag(y,lag))

    d=delta32_shuffle(data)
    if d != data:
        yield ("delta32-shuffle",d,lambda y,n=len(data): undo_delta32_shuffle(y,n))

def backend_candidates(name, transformed):
    # Built-in/general backends.
    raw = Candidate(f"{name}+raw", transformed, identity)
    yield raw

    g = gzip.compress(transformed, compresslevel=9)
    yield Candidate(f"{name}+gzip9", g, gzip.decompress)

    b = bz2.compress(transformed, compresslevel=9)
    yield Candidate(f"{name}+bzip2-9", b, bz2.decompress)

    # Brotli: generic and text mode, widest RFC-compatible window.
    for mode_name, mode in (("generic",brotli.MODE_GENERIC),("text",brotli.MODE_TEXT)):
        try:
            p=brotli.compress(transformed, mode=mode, quality=11, lgwin=24)
            yield Candidate(f"{name}+brotli11-{mode_name}", p, brotli.decompress)
        except brotli.error:
            pass

    # PPMd: model order and memory are genuine compression parameters.
    for variant in ("H","I"):
        for order in (4,6,8,12):
            for mem in (16<<20, 64<<20):
                try:
                    p=pyppmd.compress(transformed,max_order=order,mem_size=mem,variant=variant)
                    def dec(x, order=order, mem=mem, variant=variant):
                        return pyppmd.decompress(x,max_order=order,mem_size=mem,variant=variant)
                    yield Candidate(f"{name}+ppmd{variant}-o{order}-m{mem>>20}",p,dec)
                except Exception:
                    pass

    # Zstd ultra as another genuinely different LZ/entropy model.
    for level in (19,22):
        c=zstd.ZstdCompressor(level=level,write_checksum=True)
        p=c.compress(transformed)
        yield Candidate(f"{name}+zstd{level}",p,zstd.ZstdDecompressor().decompress)

def base_search(data):
    candidates=[]
    # Pre-screen transforms using a cheap physical backend to avoid the full
    # Cartesian product on obviously bad representations.
    ts=list(transforms(data))
    scored=[]
    for name,t,undo in ts:
        score=min(len(gzip.compress(t,9)),len(bz2.compress(t,9)))
        scored.append((score,name,t,undo))
    scored.sort(key=lambda x:x[0])

    # identity is mandatory; plus best seven preconditioners.
    chosen=[]
    seen=set()
    for item in sorted(scored, key=lambda x:(x[1]!="identity",x[0])):
        if item[1] in seen:
            continue
        chosen.append(item)
        seen.add(item[1])
        if len(chosen)>=8:
            break

    for _,tname,tdata,undo_transform in chosen:
        for backend in backend_candidates(tname,tdata):
            try:
                decoded_transform=backend.decoder(backend.payload)
                restored=undo_transform(decoded_transform)
                if restored != data:
                    continue
            except Exception:
                continue
            candidates.append((backend.size,backend.name,backend.payload,backend.decoder,undo_transform))

    return sorted(candidates,key=lambda x:x[0])

def recursion_search(data, best_base):
    """Optional codec recursion.

    Try a second physical entropy/dictionary layer on the best base payload.
    This tests whether recursion adds value after a mature first-stage model.
    """
    base_size,name,payload,decoder,undo=best_base
    options=[best_base]

    wrappers=[]
    wrappers.append(("brotli11",brotli.compress(payload,quality=11,lgwin=24),brotli.decompress))
    wrappers.append(("bzip2-9",bz2.compress(payload,9),bz2.decompress))
    wrappers.append(("zstd22",zstd.ZstdCompressor(level=22,write_checksum=True).compress(payload),zstd.ZstdDecompressor().decompress))
    for variant in ("H","I"):
        try:
            pp=pyppmd.compress(payload,max_order=8,mem_size=64<<20,variant=variant)
            wrappers.append((f"ppmd{variant}-o8",pp,lambda x,v=variant: pyppmd.decompress(x,max_order=8,mem_size=64<<20,variant=v)))
        except Exception:
            pass

    # Additional chain metadata: 8 bytes.
    for wname,wrapped,wdec in wrappers:
        try:
            inner=wdec(wrapped)
            if inner != payload:
                continue
            transformed=decoder(inner)
            if undo(transformed) != data:
                continue
            options.append((len(wrapped)+FRAME_BYTES+8,name+"->"+wname,wrapped,None,None))
        except Exception:
            pass
    return min(options,key=lambda x:x[0])

def pct(n,d): return 100.0*n/d

def main():
    work=Path("benchmark-work")
    work.mkdir(exist_ok=True)
    archive=work/"cantrbry.tar.gz"
    urllib.request.urlretrieve(CORPUS_URL,archive)
    dest=work/"canterbury"
    with tarfile.open(archive,"r:gz") as tf:
        tf.extractall(dest,filter="data")

    files={}
    for p in dest.rglob("*"):
        if p.is_file() and p.name in EXPECTED:
            files[p.name]=p
    missing=sorted(set(EXPECTED)-set(files))
    if missing:
        raise RuntimeError(f"missing {missing}")

    rows=[]
    totals={"orig":0,"gzip":0,"bzip2":0,"xz":0,"expert":0,"expert_rec":0}
    recursion_wins=0
    for fname in EXPECTED:
        data=files[fname].read_bytes()
        assert len(data)==EXPECTED[fname]
        gz=len(gzip.compress(data,9))
        bz=len(bz2.compress(data,9))
        xz=len(lzma.compress(data,preset=9))
        ranked=base_search(data)
        if not ranked:
            raise RuntimeError(f"no valid candidates for {fname}")
        base=ranked[0]
        rec=recursion_search(data,base)
        if rec[0] < base[0]:
            recursion_wins += 1

        rows.append((fname,len(data),gz,bz,xz,base[0],base[1],rec[0],rec[1]))
        totals["orig"]+=len(data); totals["gzip"]+=gz; totals["bzip2"]+=bz
        totals["xz"]+=xz; totals["expert"]+=base[0]; totals["expert_rec"]+=rec[0]

    out=["# CIX expert physical Canterbury benchmark","",
         "All CIX-Expert entries are real, round-trip-verified byte payloads. "
         "XZ is comparison-only and is never a selectable backend.","",
         "| file | gzip-9 | bzip2-9 | xz-9 | CIX expert | selected | CIX + recursion | recursion chain |",
         "|---|---:|---:|---:|---:|---|---:|---|"]
    for fname,orig,gz,bz,xz,ex,ename,rec,rname in rows:
        out.append(f"| {fname} | {pct(gz,orig):.2f}% | {pct(bz,orig):.2f}% | {pct(xz,orig):.2f}% | "
                   f"{pct(ex,orig):.2f}% | {ename} | {pct(rec,orig):.2f}% | {rname} |")
    out += ["",
            f"- Aggregate gzip-9: {pct(totals['gzip'],totals['orig']):.2f}%",
            f"- Aggregate bzip2-9: {pct(totals['bzip2'],totals['orig']):.2f}%",
            f"- Aggregate xz-9 target: {pct(totals['xz'],totals['orig']):.2f}%",
            f"- Aggregate CIX expert: {pct(totals['expert'],totals['orig']):.2f}%",
            f"- Aggregate CIX expert + recursion: {pct(totals['expert_rec'],totals['orig']):.2f}%",
            f"- Files where recursion paid: {recursion_wins}/{len(rows)}",
            "",
            "## Notes",
            "- Per-member CIX framing is conservatively charged at 24 bytes.",
            "- Recursion, where selected, is charged an additional 8 bytes of chain metadata.",
            "- PPMd, Brotli, zstd and bzip2 are candidate coding families; LZMA/xz is not.",
            "- The next phase can replace winning mature backends one-by-one with native CIX models while preserving the expert search/container architecture."
           ]
    Path("expert-results.md").write_text("\n".join(out)+"\n")
    print("\n".join(out))

if __name__=="__main__":
    main()
