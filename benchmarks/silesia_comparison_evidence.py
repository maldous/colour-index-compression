"""One best complete result per selected family; speed must match that result."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re


def sha(data): return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cix',default='results/leaderboard/competitive-filtered-v19/complete.json')
    parser.add_argument('--output',required=True);args=parser.parse_args()
    pub_path=Path('docs/research/2026-09-28-silesia-comparison-source.json'); pub=json.loads(pub_path.read_text())
    families={'PAQ':lambda s:bool(re.search(r'(^|\|\s*)paq',s)), 'cmix':lambda s:'cmix' in s,
        'ZPAQ':lambda s:'zpaq' in s, 'LZMA':lambda s:s.startswith(('7zip','plzip')),
        'Brotli':lambda s:s.startswith('brotli'), 'Zstandard':lambda s:s.startswith('zstd'),
        'bzip2':lambda s:s.startswith('bzip2'), 'gzip':lambda s:s.startswith('gzip')}
    original=sum(r['size'] for r in pub['verified_corpus']); candidates={key:[] for key in families}
    for key,accept in families.items():
        r=min((r for r in pub['entries'] if accept(r['compressor'].lower())),key=lambda r:r['total_bytes'])
        candidates[key].append(dict(algorithm=key,configuration=r['compressor'],physical_bytes=r['total_bytes'],
            source_kind='published',source_url=pub['source_url'],compression_MBps=None,decompression_MBps=None,
            speed_status='The published Silesia result does not include compression or decompression times.'))
    mapping={'gzip':'gzip','bzip2':'bzip2','zstd':'Zstandard','xz':'LZMA','brotli':'Brotli'}
    paths=list(Path('results/leaderboard/silesia-speed-reference-20260928').glob('*/complete.json'))
    native=Path('results/leaderboard/silesia-gzip-speed-native-20260928/complete.json')
    if native.exists():paths.append(native)
    local_proofs=[]
    for path in paths:
        report=json.loads(path.read_text())
        if not report['complete'] or len(report['rows'])!=12 or report['original_bytes']!=original: raise ValueError('incomplete local speed result')
        total=0
        for row in report['rows']:
            data=(Path('benchmark-work/silesia')/row['file']).read_bytes(); suffix='.gz' if path==native else '.bin'
            frame=(path.parent/(row['file']+suffix)).read_bytes()
            if (not row['round_trip'] or sha(data)!=row['input_sha256'] or sha(data)!=row['restored_sha256']
                or sha(frame)!=row['frame_sha256'] or len(frame)!=row['physical_bytes']): raise ValueError('speed artifact changed')
            total+=len(frame)
        if total!=report['physical_bytes']: raise ValueError('local physical sum mismatch')
        key=mapping[report['algorithm']]
        candidates[key].append(dict(algorithm=key,configuration=report['options'],physical_bytes=total,
            source_kind='local',compression_MBps=report['compression_MBps'],decompression_MBps=report['decompression_MBps'],
            speed_status='Complete local Silesia measurement, concurrent research workload.',proof_path=str(path),proof_sha256=sha(path.read_bytes())))
        local_proofs.append(dict(path=str(path),sha256=sha(path.read_bytes()),report=report))
    # Equal size prefers an actual local speed measurement, never borrows one from a different stream.
    selected=[min(rows,key=lambda r:(r['physical_bytes'],r['source_kind']!='local')) for rows in candidates.values()]
    path=Path(args.cix); cix=json.loads(path.read_text())
    if not cix['complete'] or cix['members']!=12 or cix['original_bytes']!=original: raise ValueError('incomplete CIX score')
    total=0;decode=0
    for row in cix['rows']:
        frame=(path.parent/(row['file']+'.cixc')).read_bytes(); data=(Path('benchmark-work/silesia')/row['file']).read_bytes()
        if (not row['round_trip'] or not row['complete_member'] or sha(data)!=row['input_sha256'] or sha(data)!=row['restored_sha256']
            or len(frame)!=row['size'] or sha(frame)!=row['frame_sha256'] or row['decode_seconds']<=0): raise ValueError('CIX score proof changed')
        total+=len(frame);decode+=row['decode_seconds']
    if total!=cix['total_bytes']: raise ValueError('CIX physical sum mismatch')
    selected.append(dict(algorithm='CIX',configuration=cix['policy']['name'],physical_bytes=total,source_kind='local',
        compression_MBps=None,decompression_MBps=original/1e6/decode,decode_timing_kind='historical_aggregate',decode_seconds=decode,
        speed_status='Compression has not been timed end-to-end without research caches. Decode throughput aggregates the recorded verification times for the selected12 streams; mixed CPU placement and system load, not a fresh uniform speed benchmark.',
        proof_path=str(path),proof_sha256=sha(path.read_bytes())))
    for row in selected:row['ratio_percent']=100*row['physical_bytes']/original;row['compression_factor']=original/row['physical_bytes']
    selected.sort(key=lambda r:r['physical_bytes'])
    result=dict(complete=True,captured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_bytes=original,rows=selected,
        cix_equivalent_position=1+sum(r['total_bytes']<total for r in pub['entries']),published_entries=len(pub['entries']),
        leader_bytes=min(r['total_bytes'] for r in pub['entries']),bytes_above_leader=total-min(r['total_bytes'] for r in pub['entries']),
        published_source=dict(path=str(pub_path),sha256=sha(pub_path.read_bytes()),url=pub['source_url'],checked_at=pub['checked_at']),
        candidates=candidates,local_proofs=local_proofs,
        selection='Nine selected families. Versions/options collapsed by smallest complete physical output, including locally measured candidates. PAQ branches grouped; LZMA includes7-Zip/plzip/XZ. Precomp retained when used by the best published entry. Speed never transferred from a larger or differently configured stream. This table is not a new official ranking.',
        units='Ratio is compressed/original percentage (lower is better). Speed is original decimal MB per second (higher is better).')
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r.get(k) for k in ('algorithm','physical_bytes','ratio_percent','compression_MBps','decompression_MBps','source_kind')} for r in selected],indent=2))


if __name__=='__main__':main()
