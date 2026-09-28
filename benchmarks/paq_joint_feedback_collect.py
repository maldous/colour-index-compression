"""Collect completed regional joint trials with immutable ablation checks."""
import argparse
import json
from pathlib import Path
from benchmarks.competitive_codec import sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='results/leaderboard/paq-joint-feedback-cohorts')
    parser.add_argument('--output',required=True);args=parser.parse_args();root=Path(args.root);out=Path(args.output)
    if out.exists():raise ValueError('preserve existing joint summary')
    old_path=Path('results/leaderboard/paq-memory-feedback-cohorts/complete.json');old=json.loads(old_path.read_text())
    if not old['complete']:raise ValueError('incomplete memory controls')
    checked={};groups=[]
    for seed in (4274176,35383296,47712256):
        manifest_path=root/f'manifest-{seed}.json';manifest=json.loads(manifest_path.read_text())
        item,=manifest['rows'];data=Path(item['path']).read_bytes();digest=sha(data)
        if digest!=item['sha256']:raise ValueError('regional source changed')
        report_path=root/str(seed)/'complete.json';report=json.loads(report_path.read_text())
        if not report['complete'] or sorted(r['mode'] for r in report['rows'])!=[1,2,3,4]:raise ValueError('incomplete joint controls')
        bymode={}
        for r in report['rows']:
            framepath=root/str(seed)/f'{Path(item["path"]).stem}-{r["mode"]}'/'stream.cixb';frame=framepath.read_bytes()
            if (not r['round_trip'] or r['input_sha256']!=digest or r['restored_sha256']!=digest
                or len(frame)!=r['physical_bytes'] or sha(frame)!=r['frame_sha256']):raise ValueError('joint physical evidence changed')
            for path,expected in r['source_hashes'].items():
                if path not in checked:checked[path]=sha(Path(path).read_bytes())
                if checked[path]!=expected:raise ValueError('joint dependency changed')
            if r['mode'] in (4,1):
                matching=[x for x in old['rows'] if x['input_sha256']==digest and x['mode']==(4 if r['mode']==4 else 2)]
                if len(matching)!=1 or matching[0]['paq_sha256']!=r['paq_sha256']:raise ValueError('individual ablation payload changed')
            bymode[r['mode']]=r
        groups.append(dict(seed=seed,input_sha256=digest,rows=report['rows'],
            saved_vs_native_bytes=bymode[4]['physical_bytes']-bymode[3]['physical_bytes'],
            saved_vs_memory_bytes=bymode[1]['physical_bytes']-bymode[3]['physical_bytes'],
            saved_vs_register_bytes=bymode[2]['physical_bytes']-bymode[3]['physical_bytes'],
            report=str(report_path),report_sha256=sha(report_path.read_bytes()),native_and_memory_payloads_match_previous=True))
    result=dict(complete=True,diagnostic_only=True,physical_trials=12,groups=groups,
        prior_memory_report=str(old_path),prior_memory_report_sha256=sha(old_path.read_bytes()),
        collector_sha256=sha(Path(__file__).read_bytes()),disabled_control_in_this_batch=False,
        disabled_control_evidence='docs/research/2026-09-28-paq-joint-feedback-pilot.json',
        conclusion='All twelve actual regional frames restored. Native and memory-only payloads match the prior tournament exactly. Compare like-for-like sizes within each region; no complete-member score or projection.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in group.items() if k!='rows'} for group in groups],indent=2))


if __name__=='__main__':main()
