#!/usr/bin/env python3
"""Execute the frozen native/Python fixed-DEFLATE Silesia comparison."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'docs/research/2026-10-01-rust-native/silesia-plan.json'
BIN=Path(os.environ.get('CIX_NATIVE_BIN',ROOT/'dist'))
PROFILE=os.environ.get('CIX_NATIVE_PROFILE','release')

def timed(args, timeout):
    cmd=['/usr/bin/time','-f','CIXTIME:%e,%M',*map(str,args)]
    t=time.monotonic()
    p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    elapsed=time.monotonic()-t
    if p.returncode: raise RuntimeError(f'{args} exit={p.returncode}: {p.stderr.decode(errors="replace")[-2000:]}')
    lines=p.stderr.decode(errors='replace').splitlines()
    metric=next((x.split(':',1)[1] for x in reversed(lines) if x.startswith('CIXTIME:')),None)
    if metric is None: raise RuntimeError('missing GNU time record')
    sec,rss=metric.split(',')
    return {'wall_seconds':float(sec),'elapsed_wall_seconds':elapsed,'peak_rss_kib':int(rss),'stdout':p.stdout.decode(errors='replace').strip()}

def timed_pipe_encoder(src, archive, route, timeout):
    cat=subprocess.Popen(['cat',str(src)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    cmd=['/usr/bin/time','-f','CIXTIME:%e,%M',str(BIN/'cix'),'--stream','--block-size','32KiB','--memory','512MiB','--threads','1','--route',route,'-c','-']
    t=time.monotonic()
    with open(archive,'wb') as out:
        p=subprocess.run(cmd,stdin=cat.stdout,stdout=out,stderr=subprocess.PIPE,timeout=timeout)
    cat.stdout.close(); caterr=cat.wait(timeout=timeout)
    if p.returncode or caterr: raise RuntimeError(f'pipe encode failed {p.returncode}: {p.stderr.decode(errors="replace")[-2000:]}')
    metric=next((x.split(':',1)[1] for x in reversed(p.stderr.decode(errors='replace').splitlines()) if x.startswith('CIXTIME:')),None)
    sec,rss=metric.split(',')
    return {'wall_seconds':float(sec),'elapsed_wall_seconds':time.monotonic()-t,'peak_rss_kib':int(rss)}

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    plan=json.load(open(PLAN)); full='--full' in sys.argv
    selected=plan['inputs'] if full else [next(x for x in plan['inputs'] if x['name']=='dickens')]
    (ROOT/'docs/research/2026-10-01-rust-native/silesia-progress.jsonl').write_text('')
    maxsec=300
    with tempfile.TemporaryDirectory(prefix='cix-native-silesia-') as td:
        root=Path(td); rows=[]; start=time.monotonic()
        for item in selected:
            src=Path(item['path'])
            if not src.is_file(): raise RuntimeError(f"missing frozen Silesia input {src}")
            if src.stat().st_size!=item['bytes'] or sha(src)!=item['sha256']:
                raise RuntimeError(f"frozen Silesia hash/size mismatch: {src}")
            pyarc=root/f"{item['name']}.python.cix"; ruarc=root/f"{item['name']}.rust.cix"; auto=root/f"{item['name']}.auto.cix"
            pyout=root/f"{item['name']}.python.restored"; ruout=root/f"{item['name']}.rust.restored"
            receipt=root/f"{item['name']}.receipt.json"
            pycmd=[sys.executable,'-m','cix.pipeline','encode',str(src),str(pyarc),'--effort','fast','--backend','deflate','--force','deflate','--block','32768','--history','0','--receipt',str(receipt)]
            pym=timed(pycmd,maxsec); pr=json.load(open(receipt))
            rum=timed_pipe_encoder(src,ruarc,'deflate',maxsec)
            if pyarc.read_bytes()!=ruarc.read_bytes(): raise RuntimeError(f"fixed archives not canonical: {item['name']}")
            if pyarc.stat().st_size>item['bytes']+13+41*(1+(item['bytes']+32767)//32768): raise RuntimeError('archive bound exceeded')
            # Rust decodes the Python-produced archive; Python decodes Rust's archive.
            rud=timed([BIN/'uncix','-f','-o',ruout,pyarc],maxsec)
            pyd=timed([sys.executable,'-m','cix.pipeline','decode',str(ruarc),str(pyout)],maxsec)
            if sha(ruout)!=item['sha256'] or sha(pyout)!=item['sha256']: raise RuntimeError(f"restoration hash mismatch: {item['name']}")
            autom=timed_pipe_encoder(src,auto,'auto',maxsec)
            autorest=root/f"{item['name']}.auto.restored"
            autod=timed([sys.executable,'-m','cix.pipeline','decode',str(auto),str(autorest)],maxsec)
            if sha(autorest)!=item['sha256']: raise RuntimeError(f"auto route restoration mismatch: {item['name']}")
            n=item['bytes']; mib=n/(1024*1024)
            rows.append({'name':item['name'],'source_bytes':n,'source_sha256':item['sha256'],
              'python_archive_bytes':pyarc.stat().st_size,'rust_fixed_archive_bytes':ruarc.stat().st_size,
              'rust_auto_archive_bytes':auto.stat().st_size,'fixed_archive_sha256':sha(ruarc),
              'fixed_archives_byte_identical':True,
              'python_encode':{k:v for k,v in pym.items() if k!='stdout'},'python_encode_report':{k:pr[k] for k in ('encode_seconds','selection_total_seconds','search_and_launch_overhead_seconds','source_sha256','compressed_bytes')},
              'rust_fixed_encode':{k:v for k,v in rum.items() if k!='stdout'},'rust_auto_encode':{k:v for k,v in autom.items() if k!='stdout'},
              'rust_decode_python_archive':{**{k:v for k,v in rud.items() if k!='stdout'},'mib_per_second':mib/rud['wall_seconds']},
              'python_decode_rust_archive':{**{k:v for k,v in pyd.items() if k!='stdout'},'mib_per_second':mib/pyd['wall_seconds']},
              'rust_auto_python_decode':{**{k:v for k,v in autod.items() if k!='stdout'},'mib_per_second':mib/autod['wall_seconds']}})
            progress={'file':item['name'],'completed_source_bytes':sum(r['source_bytes'] for r in rows),'input_files_done':len(rows),'input_files_total':len(selected)}
            with (ROOT/'docs/research/2026-10-01-rust-native/silesia-progress.jsonl').open('a') as f:
                f.write(json.dumps(progress)+'\n')
            print(json.dumps(progress),flush=True)
        result={'experiment_id':plan['experiment_id'],'trial_only':not full,'input_names':[x['name'] for x in selected],
          'completed':True,'elapsed_seconds':time.monotonic()-start,'results':rows,
          'aggregate':{'source_bytes':sum(r['source_bytes'] for r in rows),'python_archive_bytes':sum(r['python_archive_bytes'] for r in rows),
          'rust_fixed_archive_bytes':sum(r['rust_fixed_archive_bytes'] for r in rows),'rust_auto_archive_bytes':sum(r['rust_auto_archive_bytes'] for r in rows),
          'python_search_launch_overhead_seconds':sum(r['python_encode_report']['search_and_launch_overhead_seconds'] for r in rows),
          'rust_auto_minus_fixed_seconds':sum(r['rust_auto_encode']['wall_seconds']-r['rust_fixed_encode']['wall_seconds'] for r in rows)}}
        output=ROOT/'docs/research/2026-10-01-rust-native'/(f'silesia-trial-{PROFILE}.json' if not full else f'silesia-results-{PROFILE}.json')
        output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'completed':True,'trial_only':not full,'elapsed_seconds':result['elapsed_seconds'],'aggregate':result['aggregate']},indent=2))
if __name__=='__main__': main()
