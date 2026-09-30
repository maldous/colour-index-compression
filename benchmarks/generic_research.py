"""Predeclare, run and summarize a bounded generic-pipeline experiment wave.

Uses the established scheduler/runner: immutable builds, source-inaccessible
independent decoding, physical-core leases and memory/no-swap enforcement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import zlib
from collections import Counter
from pathlib import Path

from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.hutter_bounded_runner import canonical, load_manifest, build_identity
from cix.pipeline import EFFORTS, ROUTES

ROOT=Path(__file__).resolve().parents[1]
AREA=ROOT/"docs/research/2026-09-30-generic-pipeline"


def hashed(b): return hashlib.sha256(b).hexdigest()


def prepare():
    # Source identities come only from the closed acquisition receipt. Reads
    # here select immutable local ranges; no source lookup/download is possible.
    frozen=json.loads((AREA/"acquisition-cutoff.json").read_text())
    members={Path(r['path']).name:r for r in frozen['usable_members']}
    inputs=[]
    for name,label,offset,stratum in [
        ('msg_bt_f64','fcbench-msg',0,'development'),
        ('astro_mhd_f64','fcbench-mhd',0,'development'),
        ('data.json','golf',0,'development'),
        ('astro_pt_f64','fcbench-pt-heldout',8*1048576,'heldout'),
        ('rsim_f32','fcbench-rsim-heldout',1048576,'heldout'),
        ('data.json','golf-heldout',1048576,'heldout')]:
        record=members[name]; path=Path(record['path'])
        with path.open('rb') as f: f.seek(offset); b=f.read(16384)
        assert len(b)==16384
        inputs.append(dict(label=label,stratum=stratum,path=str(path),offset=offset,length=len(b),sha256=hashed(b),
                           full_asset_sha256=record['sha256'],classification='fixed byte range; no targeted structural selection'))
    # Existing Canterbury/Calgary/Artificial gate assets are preserved local
    # regression inputs, not new acquisitions. Include every member in full.
    for corpus in ('canterbury','calgary','artificial'):
        for path in sorted((ROOT/'benchmark-work'/corpus).iterdir()):
            if path.is_file():
                b=path.read_bytes(); inputs.append(dict(label=corpus+'-'+path.name,stratum='generic-regression',
                    path=str(path),offset=0,length=len(b),sha256=hashed(b),classification='full existing gate member'))
    configuration=[]
    for item in inputs:
        configs=[]
        if item['stratum']=='generic-regression': configs=[{'mode':'pipeline','effort':'fast'}]
        else:
            configs=[{'mode':'baseline'}]+[{'mode':m} for m in ('gzip','bzip2','xz','brotli')]
            configs += [{'mode':'pipeline','effort':e} for e in EFFORTS]
            if item['stratum']=='development':
                configs += [{'mode':'pipeline','effort':'maximum','force':r,'backend':b}
                            for r in ('composition','lz','predictor','bwt','stride','phrases','ppm','mixture')
                            for b in (('cix','count-range','deflate') if r in ('lz','predictor','bwt','stride') else ('hybrid',))]
                configs += [{'mode':'pipeline','effort':'balanced','disable':[r]}
                            for r in ('runs','deflate','composition','lz','predictor','bwt','stride','phrases','ppm','mixture')]
                configs += [{'mode':'pipeline','effort':'maximum','offline':True}]
        for config in configs: configuration.append((item,config))
    # Longer samples test history/reset cost without changing the selector.
    record=members['data.json']; path=Path(record['path']); b=path.read_bytes()[:131072]
    scaling=dict(label='golf-scaling',stratum='scaling',path=str(path),offset=0,length=len(b),sha256=hashed(b))
    inputs.append(scaling)
    for history in (0,65536):
        for block in (16384,65536):
            configuration.append((scaling,{'mode':'pipeline','effort':'balanced','force':'lz','backend':'hybrid','history':history,'block':block}))
    (AREA/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    (AREA/'environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),
         'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION,'zlib_compile':zlib.ZLIB_VERSION,
         'lscpu':subprocess.check_output(['lscpu','-J'],text=True),'cache':'uncontrolled/warm',
         'repetitions':1,'limits':'four physical cores, 8 GB reserved RAM, 1 GB temporary; no swap',
         'timing':'GNU time -v around actual encoder/decoder process including reads/writes and all discarded probes'},indent=2)+'\n')
    builds=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'cix').glob('*.py'))
    builds += ['benchmarks/generic_probe.py']
    cells=[]
    cpus=[]; physical=set()
    for cpu in sorted(os.sched_getaffinity(0)):
        topology=Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        core=((topology/'physical_package_id').read_text().strip(),(topology/'core_id').read_text().strip())
        if core not in physical: cpus.append(cpu); physical.add(core)
        if len(cpus)==4: break
    if len(cpus)<4: raise RuntimeError('four available independent physical cores are required')
    for i,(inp,config) in enumerate(configuration):
        identity=hashed(canonical({'input':inp,'config':config,'build':{p:hashed((ROOT/p).read_bytes()) for p in builds}}))[:24]
        cell_id='generic-'+identity; cpu=cpus[i%4]
        base=['/usr/bin/time','-v','-o','{workdir}/encode.time.txt',sys.executable,
              str(ROOT/'benchmarks/generic_probe.py'),'encode','{source}','{workdir}/candidate.bin']
        flags=['--mode',config['mode']]
        for key in ('effort','backend','force','history','block'):
            if key in config: flags += ['--'+key,str(config[key])]
        for disabled in config.get('disable',[]): flags += ['--disable',disabled]
        if config.get('offline'): flags += ['--offline']
        enc=base+flags
        dec=['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',sys.executable,
             str(ROOT/'benchmarks/generic_probe.py'),'decode','{workdir}/candidate.bin','{workdir}/restored.bin','--mode',config['mode']]
        manifest={'hypothesis':'Bounded generic representation and complete-size selection can improve useful compression/speed over frozen CIX; each route and backend contribution is measured separately.',
          'matched_control':'same input hash/range; frozen generic CIX level-1; unmodified reference codecs; same representation with identical-count range and deflate controls',
          'input':inp,'configuration':config,'mechanism':'generic observable-byte profiling, paid reversible streams, bounded rank coding and hybrid selection',
          'budget':{'cpu':cpu,'max_rss_bytes':2_000_000_000,'max_temp_bytes':250_000_000,'wall_seconds':300},
          'promotion_criteria':'complete archive, independent archive-only exact SHA-256 decode; no full-corpus ranking from slices; selector frozen before heldout evaluation',
          'encode_command':enc,'decode_command':dec,'artifacts':{'archive':'{workdir}/candidate.bin','restored':'{workdir}/restored.bin'},
          'build_paths':builds,'stage':'screening','stratum':inp['stratum'],'initial_state':'empty; optional paid header declares bounded decoded history'}
        path=AREA/'manifests'/f'{cell_id}.json'; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(canonical(manifest)+b'\n')
        loaded,sha=load_manifest(path)
        cells.append({'cell_id':cell_id,'owner':'/root','manifest_path':str(path),'output_dir':str(AREA/'runs'/cell_id),
                      'expected_manifest_sha256':sha,'expected_build_sha256':build_identity(loaded,ROOT),
                      'label':inp['label'],'stratum':inp['stratum'],'configuration':config})
    (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
    (AREA/'selector-freeze.json').write_text(json.dumps({'pipeline_sha256':hashed((ROOT/'cix/pipeline.py').read_bytes()),
         'efforts':{k:vars(v) for k,v in EFFORTS.items()},'cells':len(cells),
         'holdouts':'predeclared byte ranges; first evaluation only after this hash freezes; no tuning from results',
         'preexisting_exposure':'full files have local identity hashes; this generic selector has not seen these heldout ranges'},indent=2)+'\n')
    print(json.dumps({'prepared_cells':len(cells),'inputs':len(inputs)}),flush=True)


def execute(stratum):
    cells=json.loads((AREA/'cells.json').read_text())
    cells=[c for c in cells if c['stratum']==stratum]
    scheduler=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000)
    # The modulo CPU assignment is retained; pick at most one cell per CPU.
    while cells:
        wave=[]; cpus=set()
        for c in cells:
            cpu=json.loads(Path(c['manifest_path']).read_text())['budget']['cpu']
            if cpu not in cpus: wave.append(c); cpus.add(cpu)
            if len(wave)==4: break
        results=scheduler.run_wave(wave)
        for c in wave: cells.remove(c)
        print(json.dumps({'stratum':stratum,'finished_wave':[{'label':c['label'],'config':c['configuration']} for c in wave],
                          'status':[r.get('runner_status',r.get('status')) for r in results],'remaining':len(cells)}),flush=True)


def prepare_ordering():
    cells=json.loads((AREA/'cells.json').read_text())
    if any(c['stratum']=='coder-control' for c in cells): raise RuntimeError('ordering controls already declared')
    basecells=[c for c in cells if c['stratum']=='development' and c['configuration']=={'mode':'baseline'}]
    for base in basecells:
        template=json.loads(Path(base['manifest_path']).read_text())
        for route in ('lz','predictor','bwt','stride'):
            for coder in ('exact','count-range'):
                manifest=json.loads(json.dumps(template))
                manifest['configuration']={'mode':'forced-ordering','route':route,'coder':coder}
                manifest['build_paths'] += ['benchmarks/generic_coder_audit.py']
                manifest['stratum']='coder-control'
                manifest['hypothesis']='Exact ranks and same-count range ordering receive identical transforms, paid counts and stream boundaries with no raw/run/eligibility fallback.'
                manifest['mechanism']='only the ordering encoder changes; count-range construction includes incumbent rank CPU cost'
                manifest['encode_command']=['/usr/bin/time','-v','-o','{workdir}/encode.time.txt',sys.executable,
                    str(ROOT/'benchmarks/generic_coder_audit.py'),'{source}','{workdir}/candidate.bin','--route',route,'--coder',coder]
                manifest['decode_command']=['/usr/bin/time','-v','-o','{workdir}/decode.time.txt',sys.executable,
                    str(ROOT/'benchmarks/generic_probe.py'),'decode','{workdir}/candidate.bin','{workdir}/restored.bin','--mode','pipeline']
                identity=hashed(canonical({'manifest':manifest,'build':build_identity(manifest,ROOT)}))[:24]
                cell_id='generic-order-'+identity
                path=AREA/'manifests'/f'{cell_id}.json';path.write_bytes(canonical(manifest)+b'\n')
                loaded,sha=load_manifest(path)
                cells.append({'cell_id':cell_id,'owner':'/root','manifest_path':str(path),'output_dir':str(AREA/'runs'/cell_id),
                    'expected_manifest_sha256':sha,'expected_build_sha256':build_identity(loaded,ROOT),
                    'label':base['label'],'stratum':'coder-control','configuration':manifest['configuration']})
    (AREA/'cells.json').write_text(json.dumps(cells,indent=2)+'\n')
    print(json.dumps({'new_ordering_cells':24,'selector_changed':False}),flush=True)


def _timing(path):
    if not path.exists(): return {}
    result={}
    for line in path.read_text().splitlines():
        if 'Elapsed (wall clock)' in line:
            value=line.split('):',1)[1].strip(); fields=list(map(float,value.split(':')))
            result['seconds']=sum(v*60**(len(fields)-i-1) for i,v in enumerate(fields))
        elif 'Maximum resident set size' in line: result['peak_rss_kib']=int(line.rsplit(':',1)[1])
        elif 'User time (seconds)' in line: result['user_seconds']=float(line.rsplit(':',1)[1])
        elif 'System time (seconds)' in line: result['system_seconds']=float(line.rsplit(':',1)[1])
    return result


def summarize():
    rows=[]
    for cell in json.loads((AREA/'cells.json').read_text()):
        outputs=Path(cell['output_dir'])
        terminal=next(iter(outputs.glob('*/receipt.json')),None) or next(iter(outputs.glob('*/failed.json')),None)
        row={'label':cell['label'],'stratum':cell['stratum'],'config':cell['configuration'],'status':'NOT_RUN','cell_id':cell['cell_id']}
        if terminal:
            receipt=json.loads(terminal.read_text()); work=terminal.parent/'work'
            row.update(status=receipt['status'],bytes=receipt['archive_bytes'],original_bytes=receipt['identity']['input']['length'],
                       input_sha256=receipt['identity']['input']['sha256'],verification=receipt['verification'],
                       archive_sha256=receipt['archive_sha256'],receipt=str(terminal),
                       encode=_timing(work/'encode.time.txt'),decode=_timing(work/'decode.time.txt'))
            if row['status']=='FAILED':
                errors='\n'.join(p.read_text() for p in terminal.parent.glob('*.stderr.log'))
                row['failure_reason']='ROUTE_TIME_BUDGET' if 'TIME_BUDGET' in errors else 'COMMAND_OR_VERIFICATION_FAILURE'
            if (work/'encode.codec.json').exists():
                codec=json.loads((work/'encode.codec.json').read_text())
                row['codec']= {k:v for k,v in codec.items() if k!='blocks'}
                all_blocks=[json.loads(line) for line in (work/'blocks.jsonl').read_text().splitlines()]
                row['trial_statuses']=dict(Counter(t['status'] for b in all_blocks for t in b['trials']))
                row['accounting']=dict(Counter({k:sum(b['accounting'][k] for b in all_blocks)
                    for k in ('framing_bytes','structural_bytes','stream_descriptor_bytes','count_table_bytes','coded_payload_bytes')}))
                assert sum(row['accounting'].values())+54 == row['bytes']
            if (work/'ordering-audit.json').exists():
                row['ordering_audit']=json.loads((work/'ordering-audit.json').read_text())
            if row['status']=='VERIFIED_SCREENING':
                if hashed((work/'candidate.bin').read_bytes()) != row['archive_sha256'] or hashed((work/'restored.bin').read_bytes()) != row['input_sha256']:
                    raise RuntimeError('independent readback failed')
        rows.append(row)
    (AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    import csv
    with (AREA/'results.csv').open('w',newline='') as f:
        fields=['label','stratum','configuration','status','original_bytes','complete_bytes','encode_seconds','decode_seconds','encode_rss_kib','decode_rss_kib','source_sha256']
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); writer.writeheader()
        for r in rows:
            writer.writerow(dict(label=r['label'],stratum=r['stratum'],configuration=json.dumps(r['config'],sort_keys=True),status=r['status'],
                original_bytes=r.get('original_bytes'),complete_bytes=r.get('bytes'),encode_seconds=r.get('encode',{}).get('seconds'),
                decode_seconds=r.get('decode',{}).get('seconds'),encode_rss_kib=r.get('encode',{}).get('peak_rss_kib'),
                decode_rss_kib=r.get('decode',{}).get('peak_rss_kib'),source_sha256=r.get('input_sha256')))
    print(json.dumps(dict(statuses=dict(Counter(r['status'] for r in rows)),report=str(AREA/'results.json'))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('operation',choices=('prepare','prepare-ordering','run','summarize'));p.add_argument('--stratum',default='development');a=p.parse_args()
    if a.operation=='prepare':prepare()
    elif a.operation=='prepare-ordering':prepare_ordering()
    elif a.operation=='run':execute(a.stratum)
    else:summarize()
