"""Independently recheck recorded physical results and generate review tables."""
from __future__ import annotations
import hashlib
import json
from collections import Counter
from pathlib import Path
from cix import pipeline

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/'docs/research/2026-09-30-generic-pipeline'


def main():
    rows=json.loads((AREA/'results.json').read_text()); verified=0; byte_compared=0
    for row in rows:
        if row['status']!='VERIFIED_SCREENING':continue
        receipt=json.loads(Path(row['receipt']).read_text())
        original=receipt['identity']['input']; restored=Path(receipt['artifacts']['restored'])
        with Path(original['path']).open('rb') as src, restored.open('rb') as dst:
            src.seek(original['offset']); remaining=original['length']
            while remaining:
                length=min(1048576,remaining);a=src.read(length);b=dst.read(length)
                assert a==b and len(a)==length, row['cell_id'];remaining-=length
            assert not dst.read(1)
        byte_compared+=original['length']
        archive=Path(receipt['artifacts']['archive']);blob=archive.read_bytes()
        assert len(blob)==row['bytes']
        assert hashlib.sha256(blob).hexdigest()==row['archive_sha256']
        if blob.startswith(pipeline.MAGIC):
            p=pipeline.HEADER.size;seen=0
            while True:
                mode,n,size,digest=pipeline.FRAME.unpack_from(blob,p);p+=pipeline.FRAME.size
                if mode==pipeline.END:
                    assert p==len(blob) and seen==row['original_bytes'];break
                seen+=n;p+=size
            if row['config'].get('force') is None and row['config']['mode']=='pipeline':
                block=row['codec']['block_bytes']
                assert len(blob)<=row['original_bytes']+54+41*((row['original_bytes']+block-1)//block)
        verified+=1
    # Every pure ordering pair restores exactly the same transformed streams,
    # not just the same original at the end of inverse transformation.
    pairs=[]
    for label in ('fcbench-msg','fcbench-mhd','golf'):
        for route in ('lz','predictor','bwt','stride'):
            pair={r['config']['coder']:r for r in rows if r['stratum']=='coder-control' and r['label']==label and r['config']['route']==route}
            parts=[]
            for coder in ('exact','count-range'):
                row=pair[coder];receipt=json.loads(Path(row['receipt']).read_text())
                blob=Path(receipt['artifacts']['archive']).read_bytes()
                _,n,size,_=pipeline.FRAME.unpack_from(blob,pipeline.HEADER.size)
                payload=blob[pipeline.HEADER.size+pipeline.FRAME.size:][:size]
                prefix=4 if route=='bwt' else 1 if route=='stride' else 0
                parts.append((payload[:prefix],pipeline.unstreams(payload[prefix:],4*n)))
            assert parts[0]==parts[1]
            exact,control=pair['exact'],pair['count-range']
            assert exact['ordering_audit']['accounting']['count_table_bytes']==control['ordering_audit']['accounting']['count_table_bytes']
            pairs.append(dict(input=label,route=route,exact_bytes=exact['bytes'],range_bytes=control['bytes'],
                              saving_bytes=control['bytes']-exact['bytes'],same_transformed_streams=True,
                              count_table_bytes=exact['ordering_audit']['accounting']['count_table_bytes']))
    report={'verified_complete_archives':verified,'byte_for_byte_compared_total':byte_compared,
            'all_source_comparisons':'full byte equality after independent archive-only decode',
            'ordering_pairs':pairs,'selector_sha256_matches_freeze':hashlib.sha256((ROOT/'cix/pipeline.py').read_bytes()).hexdigest()==json.loads((AREA/'selector-freeze.json').read_text())['pipeline_sha256']}
    assert report['selector_sha256_matches_freeze']
    (AREA/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Complete candidate table','',
      'All sizes include the completed physical stream and framing. Failed partial archives have no qualified size.','',
      '| Input / stratum | Configuration | Complete bytes | Encode / decode s | RSS KiB E/D | Status |',
      '|---|---|---:|---:|---:|---|']
    for row in rows:
        success=row['status']=='VERIFIED_SCREENING'
        size=str(row['bytes']) if success else '—'
        times=f"{row.get('encode',{}).get('seconds','—')} / {row.get('decode',{}).get('seconds','—')}"
        rss=f"{row.get('encode',{}).get('peak_rss_kib','—')} / {row.get('decode',{}).get('peak_rss_kib','—')}"
        lines.append(f"| {row['label']} ({row['stratum']}) | `{json.dumps(row['config'],sort_keys=True)}` | {size} | {times} | {rss} | {row.get('failure_reason',row['status'])} |")
    (AREA/'CANDIDATES.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
