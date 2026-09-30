"""Run and retain one full parallel PAQ research encode/decode, never a Prize claim."""
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--python',required=True)
    ap.add_argument('--cpus',required=True)
    ap.add_argument('--workers',type=int,default=16)
    a=ap.parse_args();a.run.mkdir(exist_ok=False,parents=True)
    status={'policy':'independent-chunk PAQ v216 -8, 32 MiB chunks','same_as_serial_p26':False,'prize_qualified':False,'timing_scope':'concurrent research workload','started_at':datetime.now(timezone.utc).isoformat(),'workers':a.workers,'cpus':a.cpus,'phases':[]}
    def save(): (a.run/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    try:
        status['input_bytes']=a.source.stat().st_size;status['input_sha256']=sha(a.source)
        if status['input_bytes']!=1000000000 or status['input_sha256']!='159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc':raise ValueError('not canonical enwik9')
        archive=a.run/'enwik9.cixparq';restored=a.run/'enwik9.restored'
        for operation,src,dst in [('encode',a.source,archive),('decode',archive,restored)]:
            command=[a.python,'-m','benchmarks.hutter_parallel_paq',operation,str(src),str(dst),'--workers',str(a.workers),'--cpus',a.cpus,'--chunk-mib','32','--options=-8','--temporary',str(a.run)]
            if operation=='encode':command+=['--no-verify']
            status['status']=operation.upper()+'_RUNNING';phase={'operation':operation,'command':command,'started_at':datetime.now(timezone.utc).isoformat()};status['phases'].append(phase);save();start=time.monotonic()
            with (a.run/(operation+'.json')).open('xb') as out,(a.run/(operation+'.stderr')).open('xb') as err:
                p=subprocess.Popen(['/usr/bin/time','-v','-o',str(a.run/(operation+'.time')),*command],stdout=out,stderr=err)
                while p.poll() is None:
                    phase['elapsed_seconds']=time.monotonic()-start;phase['pid']=p.pid;save()
                    try: p.wait(timeout=10)
                    except subprocess.TimeoutExpired: pass
            phase['exit_code']=p.returncode;phase['wall_seconds']=time.monotonic()-start;save()
            if p.returncode:raise RuntimeError(operation+' failed')
            phase['output_bytes']=dst.stat().st_size;phase['output_sha256']=sha(dst);save()
        if restored.stat().st_size!=status['input_bytes'] or sha(restored)!=status['input_sha256']:raise ValueError('full restoration mismatch')
        status.update(status='COMPLETE_VERIFIED',compressed_bytes=archive.stat().st_size,archive_sha256=sha(archive),restored_sha256=sha(restored),full_round_trip=True,completed_at=datetime.now(timezone.utc).isoformat());save()
        (a.run/'complete.json').write_text(json.dumps(status,indent=2)+'\n')
    except BaseException as e:
        status.update(status='FAILED',error=repr(e));save();(a.run/'failure.json').write_text(json.dumps(status,indent=2)+'\n');raise
if __name__=='__main__':main()
