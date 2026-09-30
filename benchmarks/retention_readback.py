#!/usr/bin/env python3
"""Read-only reproduction of the independent baseline artifact audit."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / 'docs/research/2026-10-01-retention-round-v2'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    results_path = AREA / 'results.json'
    results = json.loads(results_path.read_text())
    rows = [r for r in results['rows'] if r['status'] == 'VERIFIED_SCREENING']
    counts = Counter()
    for row in rows:
        receipt = json.loads(Path(row['receipt']).read_text())
        inp = receipt['identity']['input']
        with Path(inp['path']).open('rb') as source:
            source.seek(inp['offset'])
            canonical = source.read(inp['length'])
        assert len(canonical) == inp['length'] and digest(canonical) == inp['sha256']
        assert len(row['encode_repetitions']) == len(row['decode_repetitions']) == 3
        for encoded in row['encode_repetitions']:
            data = Path(encoded['archive']).read_bytes()
            assert len(data) == encoded['bytes'] and digest(data) == encoded['sha256']
            counts['archives'] += 1
            counts['archive_bytes_checked'] += len(data)
        for decoded in row['decode_repetitions']:
            data = Path(decoded['restored']).read_bytes()
            assert data == canonical and digest(data) == decoded['sha256'] == inp['sha256']
            assert len(data) == decoded['bytes']
            counts['decoded_files'] += 1
            counts['decoded_bytes_checked'] += len(data)
        if row['configuration']['kind'] == 'adaptive':
            for encoded in row['encode_repetitions']:
                trace = [json.loads(line) for line in Path(encoded['trace']).read_text().splitlines() if line.strip()]
                assert len(trace) == 1
                block = trace[0]
                costs = [block['source_bytes'] + 41]
                costs += [t['bytes'] for t in block['trials'] if t.get('status') == 'COMPLETE' and t.get('bytes') is not None]
                assert block['complete_block_bytes'] == min(costs)
                assert encoded['bytes'] == block['complete_block_bytes'] + 54
                numeric = [v for k, v in block['accounting'].items() if isinstance(v, int)]
                assert sum(numeric) + 54 == encoded['bytes']
                counts['adaptive_minimum_checks'] += 1
    return {'verified_rows': len(rows), 'counts': dict(counts), 'mismatches': 0,
            'results_sha256': digest(results_path.read_bytes()),
            'source_freeze': results['source_freeze'],
            'pipeline_sha256': digest((ROOT / 'cix/pipeline.py').read_bytes()),
            'method': 'Physical archive rehash; every decoded file byte-equal to canonical input range; all three adaptive traces checked',
            'independent_review': '/root/route_inventory repeated these checks read-only; reproduction script materialized by root'}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
