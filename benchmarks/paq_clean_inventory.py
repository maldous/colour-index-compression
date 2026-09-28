"""Recreate native transform-only logs with stdout separated from progress.

Interleaved stderr can split a block label or number. Never parse that combined
stream as an authoritative inventory. Re-encoded archives must equal the exact
archives already restored with the isolated stored-state decoder.
"""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
import re
import subprocess
import time
from benchmarks.competitive_codec import paq_binary
from benchmarks.paq_reference_run import digest


def parse(text):
    rows=[]
    pattern=r'^\s*(\d+(?:-\d+)*)\s+\|\s*([a-zA-Z0-9 _-]{1,40})\|\s*(\d+) bytes \[(\d+) - (\d+)\]'
    for m in re.finditer(pattern,text,re.M):
        key,kind,size,first,last=m.groups()
        if int(last)-int(first)+1!=int(size): raise ValueError('invalid block extent')
        rows.append(dict(key=key,kind=kind.strip(),declared_bytes=int(size),first=int(first),last=int(last)))
    if not rows or len({r['key'] for r in rows})!=len(rows):raise ValueError('missing or duplicate segmentation records')
    parents={r['key'].rsplit('-',1)[0] for r in rows if '-' in r['key']}
    counts=Counter();lengths=Counter()
    for row in rows:
        if row['key'] not in parents:counts[row['kind']]+=1;lengths[row['kind']]+=row['declared_bytes']
    return dict(blocks=len(rows),leaf_blocks=sum(counts.values()),leaf_types=dict(counts),leaf_declared_bytes=dict(lengths),records=rows,
                note='Ranges are relative to levels of the transformation tree. Some leaf lengths precede transforms. These are neither original coverage nor exact model-input byte counts.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();root=Path(args.output).resolve()
    if root.exists():raise ValueError('preserve earlier clean inventory')
    root.mkdir(parents=True);binary=Path(paq_binary('v216'));binary_hash=digest(binary);rows=[]
    for item in json.loads(Path('results/silesia-manifest.json').read_text()):
        source=Path(item['path']).resolve();name=source.name
        proof_path=Path('results/leaderboard/paq-store-state-qualified')/name/'complete.json'
        proof=json.loads(proof_path.read_text())
        if (not proof['round_trip'] or proof['input_sha256']!=item['sha256'] or proof['restored_sha256']!=item['sha256']
            or digest(source)!=item['sha256']):raise ValueError('unqualified original')
        folder=root/name;folder.mkdir();archive=folder/'stream.paq8px216';log=folder/'segmentation.log';progress=folder/'progress.log'
        start=time.perf_counter()
        with log.open('wb') as stdout,progress.open('wb') as stderr:
            subprocess.run([str(binary),'-0','-simd','AVX2',str(source),str(archive)],stdout=stdout,stderr=stderr,check=True)
        seconds=time.perf_counter()-start
        if digest(archive)!=proof['archive_sha256']:raise ValueError('repeated native stored archive differs')
        inventory=parse(log.read_text());row=dict(file=name,original=item['size'],input_sha256=item['sha256'],
            archive_sha256=digest(archive),identical_to_independently_restored_archive=True,
            original_decode_proof=str(proof_path),original_decode_proof_sha256=digest(proof_path),
            clean_stdout_sha256=digest(log),encode_seconds=seconds,inventory=inventory)
        (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps(dict(file=name,blocks=inventory['blocks'],leaf_types=inventory['leaf_types'],archive_identical=True)),flush=True)
    if digest(binary)!=binary_hash:raise ValueError('native producer changed')
    report=dict(complete=True,diagnostic_only=True,members=12,scored=False,binary_sha256=binary_hash,
        parser_sha256=digest(Path(__file__)),rows=rows,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
