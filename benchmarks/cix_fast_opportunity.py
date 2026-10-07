#!/usr/bin/env python3
"""Freeze and run native-codec cells via the existing global WaveScheduler.

Python only orchestrates immutable native executables; it never encodes or
decodes CIX. No acquisition, Python codec reference, or Actions are involved.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.cix_dickens_best_compare import gnu_time

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    p.add_argument('--artifacts', default='dist')
    p.add_argument('--source', default='benchmark-work/silesia/mr')
    p.add_argument('--variant', choices=['fast','deflate-fast','lz-fast','default','best','gipfeli'], default='fast')
    p.add_argument('--repetitions', type=int, default=2)
    p.add_argument('--run', action='store_true')
    a=p.parse_args()
    if not a.id.replace('-','').isalnum() or not 1 <= a.repetitions <= 3: p.error('Invalid identity or repetitions')
    source=(ROOT/a.source).resolve(); artifacts=(ROOT/a.artifacts).resolve()
    if ROOT not in source.parents or ROOT not in artifacts.parents: p.error('Inputs/artifacts must be inside canonical repository')
    native = a.variant != 'gipfeli'
    encoder=artifacts/('cix' if native else 'gipfeli-reference')
    decoder=artifacts/('uncix' if native else 'gipfeli-reference')
    metadata=artifacts/'native-release.json'
    declared=json.loads(metadata.read_text())
    if digest(encoder)!=declared['binaries'][encoder.name]['sha256'] or digest(decoder)!=declared['binaries'][decoder.name]['sha256']:
        raise RuntimeError('Immutable binary metadata does not match')
    area=ROOT/'docs/research/2026-10-02-fast-opportunity'/a.id
    area.mkdir(parents=True,exist_ok=False)
    (area/'.gitignore').write_text('runs/**/work/\nruns/**/build/\n')
    flags={'fast':['--fast'],'deflate-fast':['--fast','--route','deflate'],'lz-fast':['--fast','--route','lz'],'default':[],'best':['--best']}.get(a.variant,[])
    source_hash=digest(source)
    cells=[]
    for rep in range(1,a.repetitions+1):
        command=([str(encoder),*flags,'--verbose','-o','{workdir}/archive.cix','{source}'] if native else [str(encoder),'encode','{source}','{workdir}/archive.cix'])
        decode=([str(decoder),'-o','{workdir}/restored.bin','{workdir}/archive.cix'] if native else [str(decoder),'decode','{workdir}/archive.cix','{workdir}/restored.bin'])
        builds=[str(x.relative_to(ROOT)) for x in {encoder,decoder,metadata}]+['benchmarks/cix_fast_opportunity.py','benchmarks/hutter_bounded_runner.py','benchmarks/hutter_experiment_scheduler.py']
        manifest={'hypothesis':'Compact greedy matching and bounded cheap search can improve native FAST throughput; quantify current baseline and same-input codec controls before attribution.',
          'matched_control':'Same original input bytes, host, CPUs16–19 and GNU time method. Imported Squash times are descriptive, never the local speed control.',
          'input':{'path':str(source),'offset':0,'length':source.stat().st_size,'sha256':source_hash},
          'configuration':{'variant':a.variant,'flags':flags,'repetition':rep,'source_revision':declared['source_revision'],'encoder_sha256':digest(encoder),'decoder_sha256':digest(decoder),'codec_metadata':declared},
          'mechanism':'Complete physical archive, selection/discarded-trial time included for automatic CIX; separate standalone reference when explicitly labelled. No filename/content-identity dispatch.',
          'budget':{'cpu':[16,17,18,19],'max_rss_bytes':3000000000,'max_temp_bytes':512000000,'swap_bytes':0,'wall_seconds':300},
          'promotion_criteria':'Fresh archive-only native restoration exact length and SHA-256, complete archive cost, no loss hidden. Candidate must pass CCA and pipe regressions before Silesia deployment; two repetitions are local screening, not statistical speed qualification.',
          'encode_command':['/usr/bin/time','-v','-o','{workdir}/encode.time.txt',*command],
          'decode_command':['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',*decode],
          'artifacts':{'archive':'{workdir}/archive.cix','restored':'{workdir}/restored.bin'},'build_paths':builds,'initial_state':'Fresh processes; uncontrolled cache and host load; repeated experiments run serially'}
        path=area/f'manifest-r{rep}.json';path.write_bytes(canonical(manifest)+b'\n')
        frozen,sha=load_manifest(path)
        cells.append({'cell_id':f'{a.id}-r{rep}','owner':'/root','manifest_path':str(path.relative_to(ROOT)),'output_dir':str((area/f'runs/r{rep}').relative_to(ROOT)),'cpu':[16,17,18,19],'expected_manifest_sha256':sha,'expected_build_sha256':build_identity(frozen,ROOT),'fresh_justification':'Predeclared fixed repetitions, no selection between repetitions.'})
    (area/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
    if not a.run:
        print(json.dumps({'prepared':len(cells),'area':str(area)}));return
    scheduler=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12000000000,max_temp_bytes=4000000000)
    rows=[]
    for cell in cells:
        result=scheduler.run_wave([cell])[0]
        receipt_name=result.get('runner_result',{}).get('receipt') or result.get('receipt')
        receipt_path=Path(receipt_name) if receipt_name else None
        if receipt_path and receipt_path.is_file():
            receipt=json.loads(receipt_path.read_text());work=Path(receipt['artifacts']['archive']).parent
            row={'cell_id':cell['cell_id'],'variant':a.variant,'receipt':str(receipt_path.relative_to(ROOT)),'status':receipt['status'],'input_bytes':source.stat().st_size,'input_sha256':source_hash,'archive_bytes':receipt['archive_bytes'],'archive_sha256':receipt['archive_sha256'],'source_revision':declared['source_revision'],'encoder_sha256':digest(encoder),'decode_sha256':digest(decoder),'encode':gnu_time(work/'encode.time.txt'),'decode':gnu_time(work/'decode.time.txt'),'verification':receipt['verification'],'completed_at':receipt['completed_at']}
        else: row=result
        rows.append(row)
        (area/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if row.get('status')!='VERIFIED_SCREENING': raise RuntimeError('Stop on failed exact restoration or experiment budget')

if __name__=='__main__':main()
