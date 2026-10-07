"""Requalify an additive grid-only portfolio without decoding unchanged streams.

The parent must be a complete, freshly verified twelve-member portfolio. Every
source and frame hash is rechecked. Only inputs recognized by the unchanged grid
detector can reach the added candidates; all other physical streams and their
independent decode evidence are preserved exactly.
"""
import argparse
import datetime
import json
import resource
import subprocess
import time
from pathlib import Path
from benchmarks import competitive_codec as codec
from benchmarks import record_grid_feedback as feedback,record_grid_integer as integer
from benchmarks.leaderboard_position import position


def additions(data):
    if not codec.has_fixed_star_records(data):return []
    trials=[]
    for mode in (1,2,3):
        t=time.perf_counter();blob,_=feedback.encode(data,mode,1,1)
        trials.append((blob,dict(name=f'float-feedback-{mode}',size=len(blob),encode_seconds=time.perf_counter()-t)))
    for policy,block in ((1,4096),(2,4096),(3,4096),(2,1024),(2,256),(2,64)):
        t=time.perf_counter();blob,_=integer.encode(data,policy,block)
        trials.append((blob,dict(name=f'float-interval-{policy}-{block}',size=len(blob),encode_seconds=time.perf_counter()-t)))
    return trials


def encode(data,**kwargs):
    """Uncached reproducible portfolio; no file names or original-byte tables."""
    blob,selection=codec.encode(data,**kwargs)
    for candidate,row in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(blob):blob=candidate;selection['selected']=row['name']
    return blob,selection


def decode(frame):
    if frame[:5]==feedback.MAGIC:return feedback.decode(frame)
    if frame[:5]==integer.MAGIC:return integer.decode(frame)
    return codec.decode(frame)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    parent=Path(args.parent);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if list(out.glob('*.cixc')):raise ValueError('preserve existing output')
    old=json.loads((parent/'complete.json').read_text())
    if not old['complete'] or old['members']!=12:raise ValueError('incomplete parent')
    # Parent code and all its dependencies must remain byte-identical. Additive
    # dispatch lives in a separate module; it cannot alter the incumbent policy.
    for path,digest in old['policy']['sources'].items():
        if codec.sha(Path(path).read_bytes())!=digest:raise ValueError('parent source changed: '+path)
    tracked=[__file__,feedback.__file__,integer.__file__]
    sources={str(Path(path).resolve()):codec.sha(Path(path).read_bytes()) for path in tracked}
    policy=dict(name='CIX competitive spatial/volume/constrained-grid portfolio 3',parent_policy=old['policy'],
        parent_report_sha256=codec.sha((parent/'complete.json').read_bytes()),sources=sources,
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    manifest={Path(x['path']).name:x for x in json.loads(Path('results/silesia-manifest.json').read_text())};rows=[]
    if set(manifest)!={r['file'] for r in old['rows']}:raise ValueError('parent member identity mismatch')
    for previous in old['rows']:
        name=previous['file'];item=manifest[name];data=Path(item['path']).read_bytes();blob=(parent/(name+'.cixc')).read_bytes()
        if (len(data)!=item['size'] or codec.sha(data)!=item['sha256'] or previous['input_sha256']!=item['sha256']
            or previous['restored_sha256']!=item['sha256'] or not previous['round_trip']
            or len(blob)!=previous['size'] or codec.sha(blob)!=previous['frame_sha256']):raise ValueError('parent evidence mismatch')
        candidates=additions(data);selection=dict(selected=previous['selection']['selected'],trials=previous['selection']['trials']+[row for _,row in candidates])
        for candidate,row in candidates:
            if len(candidate)<len(blob):blob=candidate;selection['selected']=row['name']
        frame=out/(name+'.cixc');frame.write_bytes(blob);changed=codec.sha(blob)!=previous['frame_sha256']
        if candidates:
            t=time.perf_counter()
            restored=decode(frame.read_bytes())
            dec=time.perf_counter()-t
            if restored!=data:raise ValueError('fresh augmented frame did not restore')
        else:dec=previous['decode_seconds']
        row=dict(previous,policy=policy,size=len(blob),frame_sha256=codec.sha(blob),selection=selection,
            decode_seconds=dec,encode_seconds=sum(r['encode_seconds'] for _,r in candidates),
            verification='fresh standalone decode' if candidates else 'unchanged physical stream; prior standalone decode preserved',
            parent_measurement=previous,additional_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        frame.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps(dict(file=name,size=len(blob),changed=changed,round_trip=True)),flush=True)
    if sources!={str(Path(path).resolve()):codec.sha(Path(path).read_bytes()) for path in tracked}:raise ValueError('addition source changed')
    published=json.loads(Path('results/leaderboard/published.json').read_text());total=sum(r['size'] for r in rows)
    result=dict(old,policy=policy,total_bytes=total,bytes_above_leader=total-old['leader']['total_bytes'],
        position=position(total,published['entries']),rows=rows,
        verification='All twelve exact physical streams have independent local restoration evidence. Unchanged streams reuse their hash-validated parent decode; affected inputs are re-encoded and freshly decoded.')
    (out/'complete.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['position']),flush=True)


if __name__=='__main__':main()
