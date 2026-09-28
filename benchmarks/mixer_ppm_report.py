"""Verify the complete 29-member Q5 prerequisite cohort against retained R3."""
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def report(root=Path('.')):
    manifest=json.loads((root/'results/corpus-manifest.json').read_text())
    counts={c:sum(x['corpus']==c for x in manifest) for c in ('canterbury','calgary','artificial')}
    if counts!={'canterbury':11,'calgary':14,'artificial':4} or len(manifest)!=29:
        raise ValueError('incomplete canonical manifest')
    results=root/'results/leaderboard';rows=[];policies={}
    for item in manifest:
        path=root/item['path'];data=path.read_bytes()
        if len(data)!=item['size'] or sha(data)!=item['sha256']:raise ValueError('input mismatch')
        label=item['corpus']+'-'+path.name;records={}
        for name,folder in (('incumbent','mixer-extended-tier1'),('candidate','mixer-ppm-tier1')):
            record=json.loads((results/folder/(label+'.json')).read_text())
            frame=(results/folder/(label+'.cixr')).read_bytes()
            identity=record['identity']
            if (not record['round_trip'] or identity['input_sha256']!=item['sha256']
                    or identity['original']!=len(data) or record['original']!=len(data)
                    or len(frame)!=record['size'] or sha(frame)!=record['frame_sha256']):
                raise ValueError('invalid verified artifact: '+label)
            if name in policies and identity['policy']!=policies[name]:raise ValueError('mixed policy')
            policies[name]=identity['policy'];records[name]=record['size']
        if records['candidate']>records['incumbent']:raise ValueError('retained portfolio grew')
        rows.append(dict(corpus=item['corpus'],file=path.name,**records,
                         saved=records['incumbent']-records['candidate']))
    aggregates={c:{k:sum(r[k] for r in rows if r['corpus']==c)
                   for k in ('incumbent','candidate','saved')} for c in ('canterbury','calgary')}
    return dict(complete_members=29,verification='Artifact/input hashes and completed independent Python decode records; no second decode in this report',
                policies=policies,aggregates=aggregates,members=rows)


if __name__=='__main__':
    print(json.dumps(report(),indent=2))
