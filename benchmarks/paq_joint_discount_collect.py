"""Verify discounted joint regions against immutable persistent/native controls."""
import argparse
import json
from pathlib import Path
import zlib
from benchmarks import paq_joint_discount_probe as new, paq_joint_log_probe as prior
from cix.multinomial import vdecode


def check(row,framepath,codec,data):
    digest=new.sha(data);frame=framepath.read_bytes()
    if (not row['round_trip'] or row['input_sha256']!=digest or row['restored_sha256']!=digest
        or row['options']!='-4' or len(frame)!=row['physical_bytes'] or new.sha(frame)!=row['frame_sha256']):
        raise ValueError('regional physical proof changed')
    for path,h in row['source_hashes'].items():
        if new.sha(Path(path).read_bytes())!=h: raise ValueError('source/backend changed')
    if frame[:5]!=codec.MAGIC or frame[5]!=row['mode']: raise ValueError('frame header changed')
    n,pos=vdecode(frame,6)
    if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data) or new.sha(frame[pos+4:])!=row['paq_sha256']:
        raise ValueError('frame payload changed')
    raw,_=new.transform.transform(data,4)
    if new.sha(raw)!=row['transformed_sha256'] or new.transform.inverse(raw)!=data: raise ValueError('transform changed')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args()
    output=Path(args.output)
    if output.exists(): raise ValueError('preserve existing qualification')
    root=Path('results/leaderboard/paq-joint-discount-cohorts');old_path=Path('docs/research/2026-09-28-paq-joint-log-cohorts.json')
    old=json.loads(old_path.read_text())
    if not old['complete'] or len(old['groups'])!=3: raise ValueError('missing complete controls')
    groups=[]
    for g in old['groups']:
        seed=g['seed'];r=g['adaptive_joint'];data=Path(r['input_path']).read_bytes()
        check(r,Path(r['artifact']),prior,data)
        source=root/seed/'complete.json';report=json.loads(source.read_text())
        if not report['complete'] or len(report['rows'])!=1: raise ValueError('incomplete new comparison')
        row,=report['rows']
        if row['mode']!=2: raise ValueError('wrong discount profile')
        framepath=root/seed/f'{seed}-2'/'stream.cixb';check(row,framepath,new,data)
        # Native controls remain linked to their separately qualified evidence.
        native,=[x for x in g['retained_controls'] if x['mode']==4]
        from benchmarks import paq_joint_feedback_probe as native_wrapper
        check(native,Path(native['artifact']),native_wrapper,data)
        groups.append(dict(seed=seed,discounted=dict(row,artifact=str(framepath)),persistent=r,native=native,
            saved_vs_persistent_bytes=r['physical_bytes']-row['physical_bytes'],
            saved_vs_native_bytes=native['physical_bytes']-row['physical_bytes'],
            report=str(source),report_sha256=new.sha(source.read_bytes())))
    result=dict(complete=True,diagnostic_only=True,scored=False,groups=groups,
        previous_report=str(old_path),previous_report_sha256=new.sha(old_path.read_bytes()),collector_sha256=new.sha(Path(__file__).read_bytes()),
        interpretation='Three new discounted frames independently restored. Persistent and native controls retained after full identity checks. Matched section4 transforms and framing. No whole-file projection; overlapping exploratory regions.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in g.items() if k not in ('discounted','persistent','native')} for g in groups],indent=2))


if __name__=='__main__':main()
