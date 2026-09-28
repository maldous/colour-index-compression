"""Discriminate combined CIX structure and PAQ reversible filter pipelines."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import resource
import subprocess
import time
import brotli
import _brotli
from benchmarks import ecoff_filtered as codec, competitive_pdata_symbols as profile
from benchmarks.competitive_codec import sha, paq_binary


def worker(spec):
    path,mode,output,whole=spec;source=Path(path);data=source.read_bytes();folder=Path(output)/f'{source.stem}-{mode}'
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'stream.cixb').exists():raise ValueError('preserve existing filtered trial')
    paths=[__file__,codec.__file__,codec.native.__file__,*profile.SOURCES,'cix/multinomial.py',
           'benchmarks/build_paq_store_state.py',codec.FORK,paq_binary('v216'),_brotli.__file__,
           codec.ROOT/'benchmark-work/references/paq8px-cix-store-state/provenance.json']
    hashes={str(Path(p)):sha(Path(p).read_bytes()) for p in paths}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    start=time.perf_counter();frame,stats=codec.encode(data,mode);enc=time.perf_counter()-start
    (folder/'stream.cixb').write_bytes(frame);start=time.perf_counter();restored=codec.decode((folder/'stream.cixb').read_bytes());dec=time.perf_counter()-start
    if restored!=data:raise ValueError('filtered combination did not restore')
    if source.read_bytes()!=data or any(sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('filtered dependency changed')
    row=dict(stats,input_path=str(source),physical_bytes=len(frame),round_trip=True,complete_silesia_member=whole,
             input_sha256=sha(data),restored_sha256=sha(restored),frame_sha256=sha(frame),source_hashes=hashes,
             revision=revision,brotli_version=brotli.__version__,encode_seconds=enc,decode_seconds=dec,
             peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['input_path','mode','physical_bytes','round_trip']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--whole',action='store_true')
    p.add_argument('--manifest',default='results/leaderboard/ecoff-got-cohorts-v2/manifest.json')
    p.add_argument('--modes',nargs='+',type=int,default=[0,1,2]);p.add_argument('--jobs',type=int,default=3);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    if args.whole:
        source=Path('benchmark-work/silesia/mozilla');manifest=dict(rows=[dict(path=str(source),sha256=sha(source.read_bytes()))])
    else:manifest=json.loads(Path(args.manifest).read_text())
    specs=[]
    for row in manifest['rows']:
        if sha(Path(row['path']).read_bytes())!=row['sha256']:raise ValueError('filtered cohort source changed')
        specs.extend((row['path'],mode,str(root),args.whole) for mode in args.modes)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    report=dict(complete=True,diagnostic_only=not args.whole,fixture=manifest,rows=rows)
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
