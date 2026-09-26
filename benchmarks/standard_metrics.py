#!/usr/bin/env python3
"""Reproducible Canterbury ratio/time benchmark.

Measures all methods on the same runner and same 11 files. Standard codecs use
three repetitions and report the median. Slow ZPAQ-5 uses one repetition.
"""
import bz2, gzip, lzma, statistics, tarfile, time, urllib.request
from pathlib import Path
import zpaq

URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,"grammar.lsp":3721,"kennedy.xls":1029744,"lcet10.txt":426754,"plrabn12.txt":481861,"ptt5":513216,"sum":38240,"xargs.1":4227}

def load():
    w=Path("benchmark-work"); w.mkdir(exist_ok=True)
    a=w/"cantrbry.tar.gz"; urllib.request.urlretrieve(URL,a)
    d=w/"metrics-canterbury"
    with tarfile.open(a,"r:gz") as tf: tf.extractall(d,filter="data")
    files={p.name:p.read_bytes() for p in d.rglob("*") if p.is_file() and p.name in EXPECTED}
    for name,n in EXPECTED.items(): assert len(files[name])==n
    return [(name,files[name]) for name in EXPECTED]

def trial(items,compress,decompress):
    compressed=[]
    t0=time.perf_counter()
    for _,data in items: compressed.append(compress(data))
    ct=time.perf_counter()-t0
    t0=time.perf_counter()
    for (_,data),blob in zip(items,compressed):
        restored=decompress(blob)
        assert restored==data
    dt=time.perf_counter()-t0
    return sum(map(len,compressed)),ct,dt

def measure(items,name,compress,decompress,repeats):
    runs=[trial(items,compress,decompress) for _ in range(repeats)]
    # Size is deterministic; median timing resists runner noise.
    size=runs[0][0]
    return {"name":name,"bytes":size,
            "compress_s":statistics.median(x[1] for x in runs),
            "decompress_s":statistics.median(x[2] for x in runs),
            "repeats":repeats}

def main():
    items=load(); original=sum(len(x) for _,x in items)
    methods=[]
    methods.append(measure(items,"gzip-9",lambda d:gzip.compress(d,9),gzip.decompress,3))
    methods.append(measure(items,"bzip2-9",lambda d:bz2.compress(d,9),bz2.decompress,3))
    methods.append(measure(items,"xz-9",lambda d:lzma.compress(d,preset=9),lzma.decompress,3))
    methods.append(measure(items,"ZPAQ-5 reference",lambda d:zpaq.compress(d,level=5,threads=1),zpaq.decompress,1))
    out=["# Canterbury standard ratio/time metrics","",
         "Same GitHub Actions runner; each file compressed independently. Standard codecs use median of 3 runs; ZPAQ-5 uses 1 run.","",
         "| method | compressed bytes | % original | compression s | decompression s | repeats |",
         "|---|---:|---:|---:|---:|---:|"]
    for m in methods:
        out.append(f"| {m['name']} | {m['bytes']:,} | {100*m['bytes']/original:.2f}% | {m['compress_s']:.3f} | {m['decompress_s']:.3f} | {m['repeats']} |")
    out+=["",f"- Original bytes: {original:,}",
          "- Timing is runner-specific and intended for relative comparisons, not universal throughput claims."]
    Path("standard-metrics.md").write_text("\n".join(out)+"\n")
    print("\n".join(out))
if __name__=="__main__":main()
