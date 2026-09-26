#!/usr/bin/env python3
import gzip, bz2, lzma, tarfile, urllib.request
from pathlib import Path
import zpaq

CORPUS_URL="https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED={
"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,
"grammar.lsp":3721,"kennedy.xls":1029744,"lcet10.txt":426754,
"plrabn12.txt":481861,"ptt5":513216,"sum":38240,"xargs.1":4227,
}
FRAME=24

def pct(a,b): return 100*a/b

def main():
    w=Path("benchmark-work"); w.mkdir(exist_ok=True)
    a=w/"cantrbry.tar.gz"; urllib.request.urlretrieve(CORPUS_URL,a)
    d=w/"canterbury-zpaq"
    with tarfile.open(a,"r:gz") as tf: tf.extractall(d,filter="data")
    files={p.name:p for p in d.rglob("*") if p.is_file() and p.name in EXPECTED}
    rows=[]; totals={"o":0,"xz":0,"zpaq":0,"zpaq4":0}
    for name,size in EXPECTED.items():
        data=files[name].read_bytes(); assert len(data)==size
        xz=lzma.compress(data,preset=9)
        z5=zpaq.compress(data,level=5,threads=1)
        z4=zpaq.compress(data,level=4,threads=1)
        assert zpaq.decompress(z5)==data
        assert zpaq.decompress(z4)==data
        rows.append((name,size,len(xz),len(z5)+FRAME,len(z4)+FRAME))
        totals["o"]+=size;totals["xz"]+=len(xz);totals["zpaq"]+=len(z5)+FRAME;totals["zpaq4"]+=len(z4)+FRAME
    out=["# Context-mixing Canterbury reference","",
         "ZPAQ is an external reference/optional expert backend, not a native CIX result.","",
         "| file | xz-9 | ZPAQ-5 | ZPAQ-4 |","|---|---:|---:|---:|"]
    for n,o,x,z5,z4 in rows:
        out.append(f"| {n} | {pct(x,o):.2f}% | {pct(z5,o):.2f}% | {pct(z4,o):.2f}% |")
    out+=["",
          f"- Aggregate xz-9: {pct(totals['xz'],totals['o']):.2f}%",
          f"- Aggregate ZPAQ-5 (+ CIX frame): {pct(totals['zpaq'],totals['o']):.2f}%",
          f"- Aggregate ZPAQ-4 (+ CIX frame): {pct(totals['zpaq4'],totals['o']):.2f}%"]
    Path("contextmix-results.md").write_text("\n".join(out)+"\n")
    print("\n".join(out))
if __name__=="__main__": main()
