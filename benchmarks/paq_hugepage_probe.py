"""Paired local PAQ allocation experiment with exact native archive controls.

Never changes a live job, global VM setting, reference binary or codec source.
All modified-allocation archives must equal native archives byte for byte, and
every extraction must match the qualified original. No speed claim before that.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from benchmarks.competitive_codec import sha, paq_binary

ROOT = Path(__file__).resolve().parents[1]


def vmstats():
    keys = ('pswpin', 'pswpout', 'pgmajfault')
    return {k:int(v) for k,v in (s.split() for s in Path('/proc/vmstat').read_text().splitlines()) if k in keys}


def monitored(command, env, log, cpu):
    maximum = dict(Rss=0, Swap=0, AnonHugePages=0)
    before = vmstats(); start = time.perf_counter()
    with log.open('wb') as output:
        proc = subprocess.Popen(['taskset','-c',str(cpu),*command], env=env, stdout=output, stderr=subprocess.STDOUT)
        while proc.poll() is None:
            try:
                text = Path(f'/proc/{proc.pid}/smaps_rollup').read_text()
                for line in text.splitlines()[1:]:
                    key, value = line.split(':',1)
                    if key in maximum: maximum[key] = max(maximum[key], int(value.split()[0]))
            except (FileNotFoundError, ProcessLookupError): pass
            time.sleep(0.5)
        if proc.returncode: raise RuntimeError('native probe failed: '+str(log))
    after = vmstats()
    return dict(seconds=time.perf_counter()-start, sampled_peak_kib=maximum,
                system_vmstat_delta={k:after[k]-before[k] for k in before})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output',required=True)
    p.add_argument('--cpu',type=int,default=16); args=p.parse_args(); out=Path(args.output).resolve()
    if out.exists(): raise ValueError('preserve previous hugepage experiment')
    out.mkdir(parents=True)
    source = ROOT/'results/leaderboard/ecoff-call-trace/source.bin'
    evidence = json.loads(source.with_name('complete.json').read_text()); original=source.read_bytes()
    if not evidence['round_trip'] or sha(original)!=evidence['input_sha256']: raise ValueError('unqualified source')
    binary=Path(paq_binary('v215')); library=out/'calloc_hugepage.so'; c_source=ROOT/'benchmarks/calloc_hugepage.c'
    subprocess.run(['gcc','-shared','-fPIC','-O2','-fno-builtin-calloc',str(c_source),'-o',str(library)],check=True)
    provenance={str(path):sha(path.read_bytes()) for path in (Path(__file__),c_source,binary,source,library)}
    rows=[]; archives={}; environment={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','CIX_GP_FEEDBACK','CIX_TRACE_OUT','CIX_RESIDUAL_IN')}
    for variant in ('native','hugepage'):
        env=dict(environment)
        if variant=='hugepage': env['LD_PRELOAD']=str(library)
        archive=out/(variant+'.paq8px215'); restored=out/(variant+'.bin')
        enc=monitored([str(binary),'-4','-simd','AVX2',str(source),str(archive)],env,out/(variant+'-encode.log'),args.cpu)
        dec=monitored([str(binary),'-d','-simd','AVX2',str(archive),str(restored)],env,out/(variant+'-decode.log'),args.cpu)
        payload=archive.read_bytes(); archives[variant]=payload
        if restored.read_bytes()!=original: raise ValueError('allocation experiment did not restore')
        row=dict(variant=variant,physical_bytes=len(payload),archive_sha256=sha(payload),restored_sha256=sha(restored.read_bytes()),round_trip=True,encode=enc,decode=dec)
        rows.append(row);print(json.dumps(row),flush=True)
    if archives['native']!=archives['hugepage']: raise ValueError('allocation advice changed coded bytes')
    if archives['native']!=source.with_name('baseline.paq8px215').read_bytes(): raise ValueError('native source no longer matches prior archive')
    if any(sha(Path(path).read_bytes())!=digest for path,digest in provenance.items()): raise ValueError('probe dependency changed')
    report=dict(complete=True,diagnostic_only=True,cpu=args.cpu,source_bytes=len(original),source_sha256=sha(original),
                identical_archives=True,rows=rows,provenance=provenance,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                kernel_reference='https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html',
                note='Paired sequential observations under concurrent local workload; sampled RSS is not a full process high-water metric. No global VM policy or existing job changed.')
    (out/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
