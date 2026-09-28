"""Hash-qualified incremental measurement for strictly additive portfolios."""
import argparse
import datetime
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks.competitive_codec import sha
from benchmarks.leaderboard_position import position


def check_sources(policy):
    for path,digest in policy.get('sources',{}).items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('parent source changed: '+path)
    if 'parent_policy' in policy:check_sources(policy['parent_policy'])
    if 'legacy_policy' in policy:
        from benchmarks.local_compare import source_digest
        if source_digest(Path.cwd())!=policy['legacy_policy']['core_sha256']:raise ValueError('legacy core changed')


def main(profile):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    parent=Path(args.parent);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if list(out.glob('*.cixc')):raise ValueError('preserve existing output')
    old=json.loads((parent/'complete.json').read_text())
    if not old['complete'] or old['members']!=12:raise ValueError('parent cohort incomplete')
    check_sources(old['policy']);sources={str(Path(p).resolve()):sha(Path(p).read_bytes()) for p in [__file__,*profile.SOURCES]}
    import brotli
    policy=dict(name=profile.NAME,parent_policy=old['policy'],parent_report_sha256=sha((parent/'complete.json').read_bytes()),
        sources=sources,brotli_version=brotli.__version__,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    manifest={Path(x['path']).name:x for x in json.loads(Path('results/silesia-manifest.json').read_text())};rows=[]
    if set(manifest)!={r['file'] for r in old['rows']}:raise ValueError('parent member identity mismatch')
    for previous in old['rows']:
        name=previous['file'];item=manifest[name];data=Path(item['path']).read_bytes();blob=(parent/(name+'.cixc')).read_bytes()
        if (len(data)!=item['size'] or sha(data)!=item['sha256'] or previous['input_sha256']!=item['sha256']
            or previous['restored_sha256']!=item['sha256'] or not previous['round_trip']
            or len(blob)!=previous['size'] or sha(blob)!=previous['frame_sha256']):raise ValueError('parent physical evidence mismatch')
        candidates=profile.additions(data)
        selection=dict(selected=previous['selection']['selected'],trials=previous['selection']['trials']+[r for _,r in candidates])
        for candidate,trial in candidates:
            if len(candidate)<len(blob):blob=candidate;selection['selected']=trial['name']
        frame=out/(name+'.cixc');frame.write_bytes(blob);changed=sha(blob)!=previous['frame_sha256']
        if candidates:
            t=time.perf_counter();restored=profile.decode(frame.read_bytes());dec=time.perf_counter()-t
            if restored!=data:raise ValueError('fresh augmented frame did not restore')
        else:dec=previous['decode_seconds']
        row=dict(previous,policy=policy,size=len(blob),frame_sha256=sha(blob),selection=selection,
            decode_seconds=dec,encode_seconds=sum(r['encode_seconds'] for _,r in candidates),
            verification='fresh standalone decode' if candidates else 'unchanged physical stream; prior standalone decode preserved',
            parent_measurement=previous,additional_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        frame.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps(dict(file=name,size=len(blob),changed=changed,round_trip=True)),flush=True)
    check_sources(old['policy'])
    for path,digest in sources.items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('addition changed during run')
    published=json.loads(Path('results/leaderboard/published.json').read_text());total=sum(r['size'] for r in rows)
    result=dict(old,policy=policy,total_bytes=total,bytes_above_leader=total-old['leader']['total_bytes'],
        position=position(total,published['entries']),rows=rows,
        verification='All twelve exact physical streams have independent local restoration evidence. Unchanged streams reuse their hash-validated parent decode; affected inputs are re-encoded and freshly decoded.')
    for row in rows:
        blob=(out/(row['file']+'.cixc')).read_bytes()
        if len(blob)!=row['size'] or sha(blob)!=row['frame_sha256']:raise ValueError('output changed')
    (out/'complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['position']),flush=True)
