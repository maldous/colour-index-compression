"""Qualify native level-zero archives using the isolated state-only repair.

This is transform/path evidence, never a compression leaderboard candidate.
Then compare native and repaired nonzero archives on the same real object.
"""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
import re
import subprocess
from benchmarks import paq_reference_run as reference

ROOT = Path(__file__).resolve().parents[1]


def segmentation(log):
    records = []
    pattern = r'^\s*(\d+(?:-\d+)*)\s+\|\s*([^|]+?)\s*\|\s*(\d+) bytes \[(\d+) - (\d+)\]'
    for match in re.finditer(pattern,log.read_text(errors='replace'),re.M):
        key,kind,length,first,last = match.groups()
        if int(last)-int(first)+1 != int(length): raise ValueError('segmentation extent mismatch')
        records.append(dict(key=key,kind=kind.strip(),bytes=int(length),first=int(first),last=int(last)))
    if not records: raise ValueError('missing segmentation records')
    if len({r['key'] for r in records}) != len(records): raise ValueError('duplicate segmentation keys')
    parents = {r['key'].rsplit('-',1)[0] for r in records if '-' in r['key']}
    leaves = [r for r in records if r['key'] not in parents]
    return dict(records=records,leaf_blocks=len(leaves),detected_types=dict(Counter(r['kind'] for r in records)),
                leaf_model_input_bytes=dict(sum_types(leaves)),
                note='Leaf counts are post-transform model input, not original-byte coverage. Nested ranges can overlap or expand.')


def sum_types(records):
    out=Counter()
    for row in records: out[row['kind']]+=row['bytes']
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True);args=parser.parse_args()
    root=Path(args.output).resolve()
    if root.exists(): raise ValueError('preserve previous store-state qualification')
    root.mkdir(parents=True); native=ROOT/'benchmark-work/references/paq8px-v216/build-local/paq8px'
    fork=ROOT/'benchmark-work/references/paq8px-cix-store-state/build-local/paq8px'
    paths=[Path(__file__),Path(reference.__file__),native,fork,ROOT/'benchmarks/build_paq_store_state.py']
    hashes={str(path):reference.digest(path) for path in paths}; rows=[]
    manifest=json.loads((ROOT/'results/silesia-manifest.json').read_text())
    for item in manifest:
        source=ROOT/item['path']; name=source.name; folder=root/name;folder.mkdir()
        if reference.digest(source)!=item['sha256'] or source.stat().st_size!=item['size']:raise ValueError('corpus changed')
        old=ROOT/'results/leaderboard/paq-v216-segmentation'/name
        status=dict(file=name,input_sha256=item['sha256'],options='-0',diagnostic_only=True)
        if (old/'stream.paq8px216').exists():
            previous=json.loads((old/'status.json').read_text()); identity=previous['identity']
            if (identity['input_sha256']!=item['sha256'] or identity['policy']['binary_sha256']!=hashes[str(native)]
                or identity['policy']['options']!='-0' or previous.get('failed_phase')!='decode'):
                raise ValueError('unexpected previous store-mode artifact')
            archive=old/'stream.paq8px216'; log=old/'encode.log'; values=(old/'encode.metrics').read_text().split()
            enc=dict(process_elapsed_seconds=float(values[-2]),peak_rss_kib=int(values[-1]),origin='completed native encode; original native decoder crashed')
        else:
            archive=folder/'stream.paq8px216'; log=folder/'encode.log'
            enc=reference.measured([str(native),'-0','-simd','AVX2',str(source),str(archive)],folder,'encode',status)
        restored=folder/'restored.bin'
        dec=reference.measured([str(fork),'-d','-simd','AVX2',str(archive),str(restored)],folder,'decode',status)
        if not reference.equal(source,restored): raise ValueError('repaired store-mode restoration failed')
        row=dict(file=name,original=item['size'],physical_bytes=archive.stat().st_size,input_sha256=item['sha256'],
                 archive_sha256=reference.digest(archive),restored_sha256=reference.digest(restored),round_trip=True,
                 encode=enc,decode=dec,segmentation=segmentation(log),log_sha256=reference.digest(log),archive_path=str(archive))
        (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps({k:row[k] for k in ['file','original','physical_bytes','round_trip']}),flush=True)
    # This nonzero path must retain the original predictor and coded bytes.
    source=ROOT/'results/leaderboard/ecoff-call-trace/source.bin'; folder=root/'nonzero-control';folder.mkdir()
    control=[]
    for label,binary in [('native',native),('repaired',fork)]:
        out=folder/label;out.mkdir();archive=out/'stream.paq8px216';restored=out/'restored.bin';status=dict(file='qualified-object',options='-4')
        enc=reference.measured([str(binary),'-4','-simd','AVX2',str(source),str(archive)],out,'encode',status)
        dec=reference.measured([str(binary),'-d','-simd','AVX2',str(archive),str(restored)],out,'decode',status)
        if not reference.equal(source,restored):raise ValueError('nonzero regression')
        control.append(dict(label=label,physical_bytes=archive.stat().st_size,archive_sha256=reference.digest(archive),round_trip=True,encode=enc,decode=dec))
        print(json.dumps(control[-1]),flush=True)
    if control[0]['archive_sha256']!=control[1]['archive_sha256']:raise ValueError('nonzero archive changed')
    if any(reference.digest(path)!=digest for path,digest in hashes.items()):raise ValueError('qualification dependency changed')
    report=dict(complete=True,diagnostic_only=True,scored=False,members=12,all_originals_restored=True,rows=rows,
                nonzero_control=control,nonzero_archives_identical=True,source_hashes=hashes,
                completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
