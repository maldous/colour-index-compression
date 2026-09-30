#!/usr/bin/env python3
"""Collect and independently read back the seven targeted CIX temp-limit retries."""
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path

from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.silesia_matrix import time_metrics

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "docs/research/2026-10-01-complete-benchmarks/silesia-v3/cix-resource-retries-v1"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def main() -> None:
    p=argparse.ArgumentParser();p.add_argument('--area',type=Path,default=AREA);a=p.parse_args()
    area=a.area.resolve();root=ROOT
    cells=json.loads((area/'cells.json').read_text())
    scheduler=WaveScheduler(root,max_jobs=3,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
    rows=[]
    for cell in cells:
        manifest=json.loads((root/cell['manifest_path']).read_text())
        terminal_path=scheduler._terminal_path(cell['cell_id'])
        if not terminal_path.is_file():raise RuntimeError(f"missing terminal record: {cell['cell_id']}")
        terminal=json.loads(terminal_path.read_text());result=terminal.get('runner_result') or {}
        receipt_path=Path(result['receipt']) if result.get('receipt') else None
        receipt=json.loads(receipt_path.read_text()) if receipt_path and receipt_path.is_file() else None
        status=receipt.get('status') if receipt else terminal.get('runner_status','FAILED')
        row={'cell_id':cell['cell_id'],'label':'silesia-'+Path(manifest['input']['path']).name,
             'method':'cix','profile':manifest['configuration']['profile'],'status':status,
             'input_bytes':manifest['input']['length'],'input_sha256':manifest['input']['sha256'],
             'retry_of_cell_id':manifest['retry_of_cell_id'],'budget':manifest['budget'],
             'retry_reason':manifest['retry_reason'],
             'receipt':str(receipt_path.relative_to(area)) if receipt_path else None}
        if receipt:
            artifact=receipt['artifacts'];archive=Path(artifact['archive']);restored=Path(artifact['restored'])
            source_hash=manifest['input']['sha256'];archive_hash=sha(archive);restored_hash=sha(restored)
            matched=(receipt['status']=='VERIFIED_SCREENING' and receipt['verification']['matched']
                     and archive.stat().st_size==receipt['archive_bytes']
                     and archive_hash==receipt['archive_sha256']
                     and restored.stat().st_size==manifest['input']['length'] and restored_hash==source_hash)
            if not matched:raise RuntimeError(f"independent physical readback failed: {cell['cell_id']}")
            row.update(archive_bytes=receipt['archive_bytes'],archive_sha256=archive_hash,
                       verification={'matched':True,'source_sha256':source_hash,'restored_sha256':restored_hash},
                       encode=time_metrics(archive.parent/'encode.time.txt'),
                       decode=time_metrics(archive.parent/'decode.time.txt'),
                       resource_retry={'max_temp_bytes':manifest['budget']['max_temp_bytes'],
                                       'previous_max_temp_bytes':100_000_000,
                                       'supersedes_initial_status':'RESOURCE_LIMIT'})
            phase=receipt['phases'][0]
            log=archive.parent/(phase['phase']+'.stdout.log')
            if log.is_file():
                try:row['candidate_summary']=json.loads(log.read_text().strip().splitlines()[-1])
                except (json.JSONDecodeError,IndexError):row['candidate_summary_error']='CIX portfolio log was not valid JSON'
        rows.append(row)
    counts=dict(Counter(r['status'] for r in rows))
    out={'schema':1,'collected_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
         'scope':'Only CIX cells previously stopped by the 100 MB temporary-space cap; no other method or dataset was rerun.',
         'resource_change':'max_temp_bytes 100,000,000 → 1,000,000,000; all other input, source, CIX profile, memory and wall settings frozen.',
         'counts':counts,'rows':rows}
    (area/'results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'counts':counts,'independently_verified':sum(r.get('verification',{}).get('matched',False) for r in rows)},sort_keys=True))

if __name__=='__main__':main()
