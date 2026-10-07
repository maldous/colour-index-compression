"""Bounded rank/unrank microprofile on already declared development inputs."""
from __future__ import annotations
import hashlib
import json
import statistics
import time
from pathlib import Path
from cix.multinomial import _counts, permutation_rank, permutation_unrank, multinomial_cardinality
from cix.pipeline import streams,accounting

AREA=Path(__file__).resolve().parents[1]/'docs/research/2026-09-30-generic-pipeline'


def main():
    rows=[]
    for inp in json.loads((AREA/'inputs.json').read_text()):
        if inp['stratum']!='development':continue
        with Path(inp['path']).open('rb') as f:f.seek(inp['offset']);data=f.read(1024)
        for n in (128,512,1024):
            tile=data[:n];counts=_counts(tile);encode=[];decode=[]
            for _ in range(3):
                start=time.perf_counter();rank=permutation_rank(tile,counts);encode.append(time.perf_counter()-start)
                start=time.perf_counter();restored=permutation_unrank(rank,counts);decode.append(time.perf_counter()-start)
                assert restored==tile
            payload=streams([tile],'cix');cost=accounting('composition',payload,n)
            rows.append({'label':inp['label'],'n':n,'symbols':sum(c>0 for c in counts),
                'sha256':hashlib.sha256(tile).hexdigest(),'rank_bits':(multinomial_cardinality(counts)-1).bit_length(),
                'rank_seconds':encode,'unrank_seconds':decode,'rank_median_seconds':statistics.median(encode),
                'unrank_median_seconds':statistics.median(decode),'production_stream_accounting':cost,
                'note':'rank-only correctness microprofile; local stream may select raw instead of paid CIX'})
    (AREA/'rank-cost.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'max_rank_seconds':max(r['rank_median_seconds'] for r in rows),
                     'max_unrank_seconds':max(r['unrank_median_seconds'] for r in rows)}))


if __name__=='__main__':main()
