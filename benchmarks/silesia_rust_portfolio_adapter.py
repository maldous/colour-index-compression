#!/usr/bin/env python3
"""Invoke packaged Rust CLI portfolio from an immutable read-only build snapshot."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def executable(name,workdir):
    source=ROOT/'dist'/name; dest=workdir/name
    if not dest.exists(): shutil.copyfile(source,dest); dest.chmod(0o555)
    if sha(source)!=sha(dest): raise RuntimeError(f'binary hash mismatch: {name}')
    return dest,sha(dest)

def main():
    p=argparse.ArgumentParser(); p.add_argument('operation',choices=('encode','decode')); p.add_argument('source',type=Path); p.add_argument('destination',type=Path); p.add_argument('--profile',choices=('fast','current','size'),required=True); p.add_argument('--workdir',type=Path,required=True); a=p.parse_args()
    a.workdir.mkdir(parents=True,exist_ok=True)
    cix,cix_hash=executable('cix',a.workdir); uncix,uncix_hash=executable('uncix',a.workdir)
    if a.operation=='encode': command=[str(cix),'--portfolio',a.profile,'--memory','512MiB','-f','-o',str(a.destination),str(a.source)]
    else: command=[str(uncix),'-f','-o',str(a.destination),str(a.source)]
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if result.returncode: raise RuntimeError(f'{command[0]} exited {result.returncode}: {result.stderr.decode(errors="replace")[-4000:]}')
    print(json.dumps({'operation':a.operation,'profile':a.profile,'cix_sha256':cix_hash,'uncix_sha256':uncix_hash,'command':command,'stdout':result.stdout.decode(errors='replace').strip(),'stderr':result.stderr.decode(errors='replace').strip()},sort_keys=True),flush=True)
if __name__=='__main__':main()
