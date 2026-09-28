"""Strict complete prerequisite report for experimental CIX stream portfolios."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def report(manifest, results, baseline, *, verify_decode=True):
    items = json.loads(Path(manifest).read_text())
    counts = {c:sum(i['corpus']==c for i in items) for c in ('canterbury','calgary','artificial')}
    if counts != dict(canterbury=11,calgary=14,artificial=4) or len(items)!=29:
        raise ValueError('requires complete 29-member prerequisite manifest')
    names = [i['corpus']+'-'+Path(i['path']).name for i in items]
    if len(set(names))!=29:
        raise ValueError('duplicate manifest member')
    missing = [n for n in names if not (Path(results)/(n+'.json')).exists()]
    if missing:
        raise ValueError('incomplete experiment: '+', '.join(missing))
    rows=[];policies=set()
    for item,name in zip(items,names):
        data=Path(item['path']).read_bytes()
        if len(data)!=item['size'] or digest(data)!=item['sha256']:
            raise ValueError('input mismatch: '+name)
        r=json.loads((Path(results)/(name+'.json')).read_text())
        b=json.loads((Path(baseline)/(name+'.json')).read_text())
        candidate=(Path(results)/(name+'.cixm')).read_bytes()
        old=(Path(baseline)/(name+'.cixm')).read_bytes()
        if (r['file']!=Path(item['path']).name or r['corpus']!=item['corpus']
            or r['original']!=len(data) or r['input_sha256']!=item['sha256']
            or b['identity']['input_sha256']!=item['sha256']
            or r['policy']['core_sha256']!=b['identity']['source_tree_sha256']
            or r['policy']['level']!=b['identity']['level']):
            raise ValueError('identity mismatch: '+name)
        for record,blob in ((r,candidate),(b,old)):
            if not record['round_trip'] or len(blob)!=record['size'] or digest(blob)!=record['compressed_sha256']:
                raise ValueError('artifact mismatch: '+name)
        if r['baseline_size']!=len(old) or r['selected_size']!=min(len(old),len(candidate)):
            raise ValueError('selection mismatch: '+name)
        if verify_decode:
            from cix.multinomial import decompress
            if decompress(candidate)!=data or decompress(old)!=data:
                raise ValueError('fresh decode mismatch: '+name)
        policies.add(json.dumps(r['policy'],sort_keys=True))
        rows.append(r)
    if len(policies)!=1:
        raise ValueError('mixed experimental policies')
    aggregates={}
    for corpus in ('canterbury','calgary'):
        subset=[r for r in rows if r['corpus']==corpus]
        aggregates[corpus]={key:sum(r[key] for r in subset) for key in ('original','baseline_size','size','selected_size')}
    return dict(complete=True,member_count=29,fresh_decode=verify_decode,policy=json.loads(policies.pop()),
                aggregates=aggregates,artificial=[r for r in rows if r['corpus']=='artificial'],members=rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--results',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--manifest',default='results/corpus-manifest.json')
    parser.add_argument('--baseline',default='results/leaderboard/tier1')
    args=parser.parse_args()
    from benchmarks.fast_runtime import enable
    enable()
    result=report(args.manifest,args.results,args.baseline)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['aggregates'],indent=2))


if __name__=='__main__':
    main()
