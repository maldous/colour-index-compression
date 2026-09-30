"""Forced identical-information ordering control, without substream eligibility gates.

Only the encoder's stream materializer is replaced for this explicit audit.
The physical output is normal CIXG1 and the unmodified decoder reconstructs it.
No raw/run selection can obscure the exact-versus-range ordering comparison.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cix import pipeline


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--route',choices=('lz','predictor','bwt','stride'),required=True)
    p.add_argument('--coder',choices=('exact','count-range'),required=True);a=p.parse_args()
    data=a.source.read_bytes()
    if not 1<=len(data)<=pipeline.MAX_BLOCK:raise ValueError('audit must be one bounded block')
    coder=2 if a.coder=='exact' else 5
    function=pipeline._cix if coder==2 else pipeline._count_range
    def forced_groups(parts, _backend):
        out=bytearray((len(parts),))
        for part in parts:
            payload=function(part)
            out+=pipeline.STREAM.pack(coder,len(part),len(payload));out+=payload
        return bytes(out)
    pipeline.streams=forced_groups
    payload=pipeline.route_encode(a.route,data,'cix')
    digest=hashlib.sha256(data).digest()
    rid=next(i for i,r in pipeline.ROUTES.items() if r==a.route)
    blob=(pipeline.HEADER.pack(pipeline.MAGIC,pipeline.MAX_BLOCK,0)
          +pipeline.FRAME.pack(rid,len(data),len(payload),digest)+payload
          +pipeline.FRAME.pack(pipeline.END,0,0,digest))
    a.destination.write_bytes(blob)
    (a.destination.parent/'ordering-audit.json').write_text(json.dumps({
        'route':a.route,'coder':a.coder,'complete_bytes':len(blob),'input_sha256':digest.hex(),
        'accounting':pipeline.accounting(a.route,payload,len(data)),
        'attribution':'identical transform, stream boundaries, alphabet/count information; no eligibility/raw/run fallback',
        'timing_caveat':'count-range construction also computes exact ranks; speed comparison is not a native range-only implementation'},indent=2)+'\n')


if __name__=='__main__':main()
