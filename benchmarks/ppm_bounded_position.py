"""Calculate a bounded-PPM equivalent Silesia rank only from a complete cohort."""
import argparse
import hashlib
import json
from pathlib import Path
from benchmarks.leaderboard_position import position


def report(published_path, results_path, corpus_path):
    published = json.loads(Path(published_path).read_text())
    expected = published['verified_corpus']
    if len(expected) != 12 or len({r['name'] for r in expected}) != 12:
        raise ValueError('expected exactly 12 distinct Silesia members')
    rows = []
    policies = set()
    for spec in expected:
        name = spec['name']
        result = Path(results_path) / ('silesia-' + name + '.json')
        if not result.exists():
            raise ValueError('incomplete cohort: missing ' + name + '; no rank calculated')
        row = json.loads(result.read_text())
        data = (Path(corpus_path) / name).read_bytes()
        if (len(data) != spec['size'] or hashlib.md5(data).hexdigest() != spec['md5']
                or hashlib.sha256(data).hexdigest() != row['identity']['input_sha256']
                or row['original'] != len(data) or not row.get('round_trip')
                or row['file'] != name or row['corpus'] != 'silesia'):
            raise ValueError('input or verification mismatch: ' + name)
        blob = Path(results_path) / ('silesia-' + name + '.cixp')
        if not blob.exists() or blob.stat().st_size != row['size']:
            raise ValueError('missing or mismatched physical frame: ' + name)
        if hashlib.sha256(blob.read_bytes()).hexdigest() != row['frame_sha256']:
            raise ValueError('physical frame hash mismatch: ' + name)
        policies.add(json.dumps(row['identity']['policy'], sort_keys=True))
        rows.append(row)
    if len(policies) != 1:
        raise ValueError('mixed policies; no rank calculated')
    total = sum(row['size'] for row in rows)
    leading = min(published['entries'], key=lambda row: row['total_bytes'])
    return dict(complete=True, experimental=True,
        comparison='Equivalent numerical insertion among published rows; not an official listing or an integrated CIX production decoder.',
        source_url=published['source_url'], snapshot_sha256=published['snapshot_sha256'],
        original_bytes=sum(row['original'] for row in rows), policy=json.loads(policies.pop()),
        position=position(total, published['entries']), leading=leading,
        bytes_above_leader=total-leading['total_bytes'], members=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', default='results/leaderboard/published.json')
    parser.add_argument('--results', default='results/leaderboard/ppm-bounded-silesia')
    parser.add_argument('--corpus', default='benchmark-work/silesia')
    parser.add_argument('--output', default='results/leaderboard/ppm-bounded-position.json')
    args = parser.parse_args()
    result = report(args.published, args.results, args.corpus)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('members', 'policy')}, indent=2))


if __name__ == '__main__':
    main()
