"""Qualify adaptive joint regions against their exact retained four-arm controls."""
import argparse
import json
from pathlib import Path
import zlib
from benchmarks import paq_joint_log_probe as new, paq_joint_feedback_probe as old
from benchmarks.paq_joint_log_collect import verified_rows
from cix.multinomial import vdecode


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True); args=parser.parse_args()
    output=Path(args.output)
    if output.exists(): raise ValueError('preserve existing regional proof')
    root=Path('results/leaderboard/paq-joint-log-cohorts'); report_path=root/'complete.json'
    report=json.loads(report_path.read_text()); manifest=json.loads(Path('results/leaderboard/ecoff-got-cohorts-v2/manifest.json').read_text())
    if not report['complete'] or len(report['rows'])!=3: raise ValueError('incomplete regional batch')
    groups=[]; seen=set()
    for r in report['rows']:
        source=Path(r['input_path']); seed=source.stem; data=source.read_bytes(); digest=new.sha(data)
        item,=[x for x in manifest['rows'] if x['path']==r['input_path']]
        if digest!=item['sha256'] or seed in seen: raise ValueError('regional input identity changed')
        seen.add(seed); framepath=root/f'{seed}-3'/'stream.cixb'; frame=framepath.read_bytes()
        if (r['mode']!=3 or r['options']!='-4' or not r['round_trip'] or r['input_sha256']!=digest
            or r['restored_sha256']!=digest or len(frame)!=r['physical_bytes'] or new.sha(frame)!=r['frame_sha256']):
            raise ValueError('new frame physical proof changed')
        for p,h in r['source_hashes'].items():
            if new.sha(Path(p).read_bytes())!=h: raise ValueError('new source or backend changed')
        if frame[:5]!=new.MAGIC or frame[5]!=3: raise ValueError('new header changed')
        n,pos=vdecode(frame,6)
        if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data) or new.sha(frame[pos+4:])!=r['paq_sha256']:
            raise ValueError('new payload changed')
        raw,_=new.transform.transform(data,4)
        if new.sha(raw)!=r['transformed_sha256'] or new.transform.inverse(raw)!=data: raise ValueError('new transform changed')
        controls,proof=verified_rows(Path('results/leaderboard/paq-joint-feedback-cohorts')/seed,old)
        if set(controls)!={1,2,3,4}: raise ValueError('missing reference arm')
        for c in controls.values():
            if c['input_sha256']!=digest or c['transformed_sha256']!=r['transformed_sha256']: raise ValueError('experimental inputs differ')
        groups.append(dict(seed=seed,adaptive_joint=dict(r,artifact=str(framepath)),retained_controls=list(controls.values()),
            control_report=proof,saved_vs_native_bytes=controls[4]['physical_bytes']-r['physical_bytes'],
            saved_vs_memory_bytes=controls[1]['physical_bytes']-r['physical_bytes'],
            saved_vs_fixed_joint_bytes=controls[3]['physical_bytes']-r['physical_bytes']))
    result=dict(complete=True,diagnostic_only=True,scored=False,groups=groups,
        report=str(report_path),report_sha256=new.sha(report_path.read_bytes()),collector_sha256=new.sha(Path(__file__).read_bytes()),
        verification='Three new independent restorations; twelve retained control archives checked against source/input/frame/backend proofs and transform inversion. Same transforms and framing. No adaptive-register-only regional arm. Exploratory overlapping cohorts, no whole-file projection or identical-information entropy-coder advantage.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in g.items() if k not in ('adaptive_joint','retained_controls')} for g in groups],indent=2))


if __name__=='__main__': main()
