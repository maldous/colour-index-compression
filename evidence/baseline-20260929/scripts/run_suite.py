#!/usr/bin/env python3
"""Serial, resumable frozen evidence schedule; never runs research or CI.

Dataset preparation is outside timers. The recorded schedule is immutable once
created, and every algorithm receives its prescribed repetitions or an explicit
failure/skip record. Missing authoritative NNLCB inputs are retained separately.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from generate_synthetic import CLASSES, VERSION, SEED, generate
from run_benchmark import ROOT, benchmark, digest, quiet_research

ALGORITHMS=['gzip','bzip2','zstd','xz','brotli','zpaq','paq8px','CIX']
ORDER_SEED='cix-frozen-evidence-20260929-order-v1'
SIZES=[10<<20,100<<20,1<<30,10<<30]
FINISHED={'VERIFIED','FAILED','TIMEOUT','RESOURCE LIMIT','HASH MISMATCH','NOT RUN'}


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.writing')
    tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)


def order(dataset_id,round_number):
    base=sorted(ALGORITHMS,key=lambda a:hashlib.sha256((ORDER_SEED+'\0'+dataset_id+'\0'+a).encode()).digest())
    offset=(round_number*3)%len(base)
    return base[offset:]+base[:offset]


def schedule_dataset(dataset):
    n=dataset['obtained_bytes']
    rounds=range(4) if n<=1<<30 else [1]
    return [dict(algorithm=a,repetition=r,warmup=r==0) for r in rounds for a in order(dataset['dataset_id'],r)]


def busy_preparation():
    busy=[]
    roles=('acquire.py','acquire_plan.py','prepare_public_inputs.py','inventory_sources.py')
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=(p/'cmdline').read_bytes().split(b'\0')
            if any(Path(a.decode(errors='replace')).name in roles for a in args):
                busy.append(dict(pid=int(p.name),role=next(Path(a.decode(errors='replace')).name for a in args if Path(a.decode(errors='replace')).name in roles)))
        except (OSError,StopIteration):pass
    return busy


def wait_for_compute(output):
    """User-authorized parallel R&D may use time between atomic timed runs."""
    while True:
        active=quiet_research();preparation=busy_preparation()
        if not active and not preparation:return
        write(output/'suite-state.json',dict(status='WAITING FOR SHARED COMPUTE',updated_utc=now(),
            active_research=active,active_preparation=preparation))
        time.sleep(5)


def create_plan(storage):
    wiki=json.loads((ROOT/'manifests/wikipedia-input.json').read_text())
    nnlcb=json.loads((ROOT/'manifests/nnlcb-datasets.json').read_text())
    exact=[r for r in nnlcb if r['compatibility']=='EXACT']
    silesia=[r for r in exact if int(r['dataset_id'][1:])<=12]
    other=[r for r in exact if int(r['dataset_id'][1:])>12]
    datasets=silesia+wiki+other
    for size in SIZES:
        for kind in CLASSES:
            ident=f'SYN-{kind}-{size}'
            datasets.append(dict(dataset_id=ident,name=f'Synthetic {kind}, {size} bytes',
                obtained_bytes=size,path=str(storage/'synthetic'/ident),
                synthetic_kind=kind,evidence_layer='synthetic scaling',generator=VERSION,
                seed_hex=SEED.hex(),compatibility='Not an NNLCB dataset'))
    scripts={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'scripts').glob('*.py'))}
    return dict(created_utc=now(),order_seed=ORDER_SEED,cix_commit='f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6',
        profile='high-compression-v1',scripts=scripts,
        compressor_manifest_sha256=digest(ROOT/'manifests/compressor-binaries.json'),
        python_manifest_sha256=digest(ROOT/'manifests/frozen-python-environment.json'),
        methodology_sha256=digest(ROOT/'BENCHMARK-METHODOLOGY.md'),
        qualification_gaps=[r for r in nnlcb if r['compatibility']!='EXACT'],
        datasets=[dict(input=d,schedule=schedule_dataset(d)) for d in datasets])


def validate_plan(plan):
    for relative,sha in plan['scripts'].items():
        if digest(ROOT/relative)!=sha:raise ValueError('Frozen harness changed: '+relative)
    if digest(ROOT/'manifests/compressor-binaries.json')!=plan['compressor_manifest_sha256']:
        raise ValueError('Frozen binary manifest changed')
    if digest(ROOT/'manifests/frozen-python-environment.json')!=plan['python_manifest_sha256']:
        raise ValueError('Frozen Python manifest changed')
    if digest(ROOT/'BENCHMARK-METHODOLOGY.md')!=plan['methodology_sha256']:
        raise ValueError('Frozen methodology changed')


def skip(dataset,job,path,reason):
    path.mkdir(parents=True,exist_ok=False)
    row=dict(dataset_id=dataset['dataset_id'],dataset_name=dataset['name'],input_manifest=dataset,
        algorithm=job['algorithm'],profile='high-compression-v1',**{k:job[k] for k in ('repetition','warmup')},
        status='NOT RUN',failure_reason=reason,started_utc=now(),finished_utc=now(),
        original_bytes=dataset['obtained_bytes'],cix_commit='f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6' if job['algorithm']=='CIX' else None)
    write(path/'result.json',row)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--wait',action='store_true',help='Wait for research and acquisition/preparation to finish')
    parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'suite.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            active=quiet_research();preparation=busy_preparation()
            wiki_ready=(ROOT/'manifests/wikipedia-input.json').is_file()
            if not active and not preparation and wiki_ready:break
            state=dict(status='WAITING FOR SAFE MEASUREMENT CHECKPOINT',updated_utc=now(),
                active_research=active,active_preparation=preparation,wikipedia_prepared=wiki_ready)
            write(args.output/'suite-state.json',state)
            if not args.wait:raise RuntimeError('Not ready; see suite-state.json')
            time.sleep(30)
        plan_path=args.output/'schedule.json'
        if plan_path.exists():plan=json.loads(plan_path.read_text())
        else:
            plan=create_plan(args.storage);write(plan_path,plan)
        validate_plan(plan)
        if args.plan_only:
            print(json.dumps(dict(datasets=len(plan['datasets']),jobs=sum(len(x['schedule']) for x in plan['datasets']),qualification_gaps=len(plan['qualification_gaps']))));return
        for entry in plan['datasets']:
            dataset=dict(entry['input']);ident=dataset['dataset_id']
            dataset_dir=args.output/ident
            dataset_dir.mkdir(exist_ok=True)
            jobs=entry['schedule']
            def job_dir(j):return dataset_dir/f"{j['algorithm']}-r{j['repetition']}"
            if all((job_dir(j)/'result.json').exists() and json.loads((job_dir(j)/'result.json').read_text())['status'] in FINISHED for j in jobs):continue
            validate_plan(plan)
            wait_for_compute(args.output)
            generated=dataset.get('synthetic_kind')
            if generated:
                path=Path(dataset['path']);record=dataset_dir/'synthetic-input.json'
                if not path.exists():
                    if shutil.disk_usage(args.storage).free<dataset['obtained_bytes']+(5<<30):
                        raise RuntimeError('Insufficient disk to materialise the next synthetic input')
                    proof=generate(generated,dataset['obtained_bytes'],path);write(record,proof)
                else:
                    if not record.exists():raise RuntimeError('Existing synthetic input lacks preparation proof')
                    proof=json.loads(record.read_text())
                    if digest(path)!=proof['sha256']:raise ValueError('Synthetic input changed')
                dataset.update(sha256=proof['sha256'],synthetic_preparation=proof)
            write(dataset_dir/'input.json',dataset)
            env_path=dataset_dir/'environment.json'
            if not env_path.exists():
                subprocess.run([sys.executable,str(ROOT/'scripts/capture_environment.py'),str(env_path),'--storage',str(args.storage)],check=True)
            failed={}
            for job in jobs:
                path=job_dir(job)
                write(args.output/'suite-state.json',dict(status='MEASURING',updated_utc=now(),dataset_id=ident,job=job))
                validate_plan(plan)
                if path.exists():
                    result_path=path/'result.json'
                    if not result_path.exists():raise RuntimeError('Interrupted run directory requires review: '+str(path))
                    row=json.loads(result_path.read_text())
                    if row['status'] not in FINISHED:raise RuntimeError('Interrupted run requires review: '+str(path))
                elif job['algorithm'] in failed:
                    row=skip(dataset,job,path,'Earlier prescribed invocation failed; not retried to conceal or multiply that failure: '+failed[job['algorithm']])
                else:
                    wait_for_compute(args.output)
                    row=benchmark(dataset,job['algorithm'],path,repetition=job['repetition'],warmup=job['warmup'])
                if row['status']!='VERIFIED':failed[job['algorithm']]=row.get('failure_reason',row['status'])
                if row.get('storage_recovery_error'):raise RuntimeError('Storage recovery requires review; preserve result and stop suite')
                subprocess.run([sys.executable,str(ROOT/'scripts/aggregate_results.py'),str(args.output),'--output',str(ROOT/'results.json')],check=True)
                subprocess.run([sys.executable,str(ROOT/'scripts/reproduce_nnlcb_metrics.py'),
                    '--manifest',str(ROOT/'manifests/nnlcb-datasets.json'),'--results',str(ROOT/'results.json'),
                    '--output',str(ROOT/'tables/nnlcb-qualification.json')],check=True,stdout=subprocess.DEVNULL)
            if generated:
                Path(dataset['path']).unlink()
                write(dataset_dir/'synthetic-retention.json',dict(removed_utc=now(),reason='All prescribed runs completed or explicitly failed. Deterministic generator, seed, size and SHA-256 are preserved; remove only this suite-generated input.'))
        write(args.output/'suite-state.json',dict(status='SCHEDULE FINISHED; PUBLICATION GATES STILL REQUIRED',updated_utc=now(),qualification_gaps=len(plan['qualification_gaps'])))


if __name__=='__main__':main()
