"""Complete-member competitive tournament; fresh standalone decoding is required."""
import argparse
import concurrent.futures
import datetime
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

from benchmarks import competitive_codec as codec
from benchmarks.joint_position import report as validate_joint
from benchmarks.leaderboard_position import position
from benchmarks.local_compare import source_digest


def worker(spec):
    item,output,baseline,policy,paq_root=spec
    source=Path(item['path']);data=source.read_bytes();name=source.name
    if len(data)!=item['size'] or codec.sha(data)!=item['sha256']:raise ValueError('corpus mismatch')
    base=Path(baseline)/('silesia-'+name+'.cixt');row=json.loads(base.with_suffix('.json').read_text())
    cached=base.read_bytes()
    if codec.sha(cached)!=row['frame_sha256'] or codec.sha(data)!=row['identity']['input_sha256']:raise ValueError('cache changed')
    if policy['legacy_policy']!=row['identity']['policy']:raise ValueError('mixed cached policies')
    paq=None;paq_cache=None;paq_row=None
    if paq_root:
        folder=Path(paq_root)/name;paq_row=json.loads((folder/'result.json').read_text());p=paq_row['identity']['policy']
        paq=(p['version'],p['options']);paq_cache=(folder/('stream.paq8px'+p['version'][1:])).read_bytes()
        if (p!=policy['paq_policy'] or not paq_row['round_trip'] or codec.sha(paq_cache)!=paq_row['archive_sha256']
            or paq_row['identity']['input_sha256']!=item['sha256']):raise ValueError('invalid PAQ cache')
    t=time.perf_counter();blob,selection=codec.encode(data,legacy_cache=cached,paq=paq,paq_cache=paq_cache);enc=time.perf_counter()-t
    out=Path(output);frame=out/(name+'.cixc');frame.write_bytes(blob)
    t=time.perf_counter();restored=codec.decode(frame.read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('fresh competitive decode mismatch')
    result=dict(file=name,original=len(data),size=frame.stat().st_size,input_sha256=codec.sha(data),
        frame_sha256=codec.sha(blob),restored_sha256=codec.sha(restored),round_trip=True,complete_member=True,
        encode_seconds=enc,decode_seconds=dec,selection=selection,policy=policy,
        peak_process_rss_kib=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        cached_baseline_measurement=row, cached_paq_measurement=paq_row,
        timing_note='Encode time excludes cached baseline/reference generation; original timings retained separately.',
        completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    frame.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(file=name,size=len(blob),selected=selection['selected'],round_trip=True,decode_seconds=dec)),flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--baseline',default='results/leaderboard/joint-parallel-verified');p.add_argument('--paq-reference')
    args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if list(out.glob('*.cixc')):raise ValueError('output already has artifacts; preserve and inspect before retry')
    baseline=validate_joint('results/leaderboard/published.json',args.baseline,'benchmark-work/silesia')
    # Source identity is checked as well as the cached data and frame identities.
    source_files={'encoder_sha256':'benchmarks/joint_bounded.py','native_source_sha256':'benchmarks/native_ppm.cpp',
        'native_wrapper_sha256':'benchmarks/native_ppm.py','native_binary_sha256':'results/leaderboard/native_ppm.so',
        'mixer_source_sha256':'benchmarks/mixer_rounded_bounded.py','rounded_source_sha256':'benchmarks/rounded_mixer.py',
        'context_source_sha256':'benchmarks/contextual_mixer.py','mixer_wrapper_sha256':'benchmarks/native_contextual_mixer.py',
        'mixer_native_sha256':'benchmarks/native_mixer_rounding.cpp','mixer_binary_sha256':'results/leaderboard/native_mixer_rounding.so'}
    old_policy=baseline['policy']
    if old_policy['core_sha256']!=source_digest(Path.cwd()):raise ValueError('changed baseline core')
    for key,path in source_files.items():
        if old_policy[key]!=codec.sha(Path(path).read_bytes()):raise ValueError('changed baseline dependency: '+path)
    import imagecodecs
    tracked=['benchmarks/competitive_codec.py','benchmarks/competitive_run.py','benchmarks/spatial_image_codec.py',
             'benchmarks/volume_image_codec.py','benchmarks/native_ppm_decode.cpp','benchmarks/native_ppm_decode.py',
             'benchmarks/legacy_mixer_native.py','benchmarks/native_legacy_mixer.cpp',
             'results/leaderboard/native_ppm_decode.so','results/leaderboard/native_legacy_mixer.so']
    policy=dict(name='CIX competitive spatial/volume portfolio 1',legacy_policy=old_policy,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources={path:codec.sha(Path(path).read_bytes()) for path in tracked},
        imagecodecs_version=imagecodecs.__version__,imagecodecs_native_versions=imagecodecs.version(),paq_policy=None)
    items=json.loads(Path('results/silesia-manifest.json').read_text())
    if args.paq_reference:
        complete=json.loads((Path(args.paq_reference)/'complete.json').read_text())
        if not complete['complete'] or complete['members']!=12:raise ValueError('PAQ reference cohort incomplete')
        policy['paq_policy']=complete['policy']
    (out/'run.json').write_text(json.dumps(dict(policy=policy,jobs=args.jobs,manager_pid=os.getpid()),indent=2)+'\n')
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(item,args.output,args.baseline,policy,args.paq_reference) for item in items]))
    published=json.loads(Path('results/leaderboard/published.json').read_text())
    # Read all physical artifacts back before emitting any rank.
    for row in rows:
        data=(out/(row['file']+'.cixc')).read_bytes()
        if len(data)!=row['size'] or codec.sha(data)!=row['frame_sha256']:raise ValueError('artifact changed')
    total=sum(r['size'] for r in rows);leading=min(published['entries'],key=lambda r:r['total_bytes'])
    result=dict(complete=True,members=12,original_bytes=sum(r['original'] for r in rows),total_bytes=total,
        position=position(total,published['entries']),bytes_above_leader=total-leading['total_bytes'],leader=leading,
        comparison='Equivalent numerical position, not an official listing; source publication remains required for eligibility.',
        source_url=published['source_url'],snapshot_sha256=published['snapshot_sha256'],policy=policy,rows=rows)
    (out/'complete.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['position']),flush=True)


if __name__=='__main__':main()
