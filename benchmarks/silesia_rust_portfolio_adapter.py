#!/usr/bin/env python3
"""Invoke packaged Rust CLI portfolio from an immutable read-only build snapshot."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.silesia_rust_client import executable, invoke


def main():
    p=argparse.ArgumentParser(); p.add_argument('operation',choices=('encode','decode')); p.add_argument('source',type=Path); p.add_argument('destination',type=Path); p.add_argument('--profile',choices=('fast','current','size'),required=True); p.add_argument('--workdir',type=Path,required=True); a=p.parse_args()
    a.workdir.mkdir(parents=True,exist_ok=True)
    cix,cix_hash=executable('cix',a.workdir); uncix,uncix_hash=executable('uncix',a.workdir)
    if a.operation=='encode':
        command=[str(cix),'--portfolio',a.profile,'--memory','512MiB','-f','-o',str(a.destination),str(a.source)]
    else:
        command=[str(uncix),'-f','-o',str(a.destination),str(a.source)]
    stdout,stderr=invoke(command)
    print(json.dumps({'operation':a.operation,'profile':a.profile,'cix_sha256':cix_hash,'uncix_sha256':uncix_hash,'command':command,'stdout':stdout.strip(),'stderr':stderr.strip()},sort_keys=True),flush=True)

if __name__=='__main__':main()
