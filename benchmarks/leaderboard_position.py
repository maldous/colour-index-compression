#!/usr/bin/env python3
"""Require a complete verified Silesia cohort before calculating equivalent rank."""
import argparse
import hashlib
import json
from pathlib import Path


def position(total, entries):
    ordered = sorted(entries, key=lambda row: row['total_bytes'])
    better = [r for r in ordered if r['total_bytes'] < total]
    worse = [r for r in ordered if r['total_bytes'] > total]
    tied = [r for r in ordered if r['total_bytes'] == total]
    return dict(total_bytes=total, equivalent_position=len(better)+1,
                published_entries=len(ordered), tied_entries=tied,
                nearest_better=better[-3:], nearest_worse=worse[:3])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--published', default='results/leaderboard/published.json')
    p.add_argument('--results', default='results/leaderboard/silesia')
    p.add_argument('--output', default='results/leaderboard/position.json')
    args = p.parse_args()
    published = json.loads(Path(args.published).read_text())
    expected = {r['name']: r for r in published['verified_corpus']}
    root = Path(args.results)
    rows = []
    for name, spec in expected.items():
        result_path = root / ('silesia-'+name+'.json')
        if not result_path.exists():
            raise SystemExit(f'Incomplete cohort: missing {name}; no rank calculated')
        row = json.loads(result_path.read_text())
        blob = root / ('silesia-'+name+'.cixm')
        if not row.get('round_trip') or row['original'] != spec['size']:
            raise SystemExit('unverified or mismatched corpus member')
        if not blob.exists() or blob.stat().st_size != row['size']:
            raise SystemExit('missing or mismatched physical compressed artifact')
        if hashlib.sha256(blob.read_bytes()).hexdigest() != row['compressed_sha256']:
            raise SystemExit('compressed artifact hash mismatch')
        wrapped = blob.with_suffix('.cix')
        if (not wrapped.exists() or wrapped.stat().st_size != row['cli_wrapper_size']
                or hashlib.sha256(wrapped.read_bytes()).hexdigest() != row['cli_wrapper_sha256']):
            raise SystemExit('CLI artifact missing or hash mismatch')
        source_path = Path('benchmark-work/silesia') / name
        source = source_path.read_bytes()
        if (hashlib.md5(source).hexdigest() != spec['md5']
                or hashlib.sha256(source).hexdigest() != row['identity']['input_sha256']):
            raise SystemExit('source bytes do not match published corpus or measured input')
        rows.append(row)
    if len(rows) != 12:
        raise SystemExit('expected exactly 12 corpus members')
    policies = {json.dumps({k:r['identity'][k] for k in ('source_tree_sha256','level','config')},sort_keys=True) for r in rows}
    if len(policies) != 1:
        raise SystemExit('mixed encoder policies; no rank calculated')
    entries = published['entries']
    report = dict(
        comparison='equivalent numerical insertion among published compressor/version/option rows; not an official listing',
        source_url=published['source_url'], snapshot_sha256=published['snapshot_sha256'],
        policy=json.loads(policies.pop()), original_bytes=sum(r['original'] for r in rows),
        members=rows,
        stream=position(sum(r['size'] for r in rows),entries),
        cli_wrapper=position(sum(r['cli_wrapper_size'] for r in rows),entries),
    )
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('members','policy')},indent=2))


if __name__ == '__main__':
    main()
