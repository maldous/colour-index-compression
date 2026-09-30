#!/usr/bin/env python3
"""Export finished local evidence to the existing Site; never run experiments."""
import argparse
import csv
import hashlib
import json
import shutil
import statistics
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/research/2026-10-01-retention-round-v2'
BACK = ROOT / 'docs/research/2026-10-01-backend-retention'
AUDIT = ROOT / 'docs/research/2026-10-01-retention-audit'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n')


def export(site, commit):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A complete Git commit SHA is required')
    from cix.backend_portfolio import coverage_table, REFERENCE_PRESETS
    data = site / 'dist/data'
    report, baseline, backend = read(AUDIT / 'report.json'), read(BASE / 'results.json'), read(BACK / 'results.json')
    assert baseline['counts'] == {'VERIFIED_SCREENING': 1127, 'FAILED': 43}
    assert backend['counts'] == {'VERIFIED_SCREENING': 120}
    assert all(r['status'] == 'VERIFIED_SCREENING' for r in backend['rows'])
    frozen = data / 'benchmarks-before-retention.json'
    if not frozen.exists():
        shutil.copyfile(data / 'benchmarks.json', frozen)
    dashboard = read(frozen)
    receipts = data / 'receipts'
    receipts.mkdir(exist_ok=True)
    base_index = {r['cell_id']: r for r in baseline['rows']}
    by_label = {r['label']: r for r in read(ROOT / 'docs/research/2026-09-30-generic-pipeline/inputs.json')}
    by_label.update({r['label']: r for r in read(BASE / 'replication-inputs.json')['inputs']})
    backend_public = []
    reference_comparison = []
    for row in backend['rows']:
        item = {k: row[k] for k in ('cell_id', 'label', 'matrix_stage', 'configuration', 'budget', 'status', 'archive_bytes', 'archive_sha256', 'verification', 'encode', 'decode', 'selected')}
        item['input'] = by_label[row['label']]
        item['receipt'] = 'data/receipts/' + row['cell_id'] + '.json'
        for key in ('portfolio_reports', 'adaptive_reports', 'diagnostic_reports', 'minimum_selection_assertion'):
            if key in row:
                item[key] = row[key]
        control = base_index.get(row.get('matched_v2_baseline_cell_id'))
        if control:
            item['baseline'] = {k: control[k] for k in ('cell_id', 'archive_bytes', 'encode', 'decode')}
        backend_public.append(item)
        shutil.copyfile(row['receipt'], receipts / (row['cell_id'] + '.json'))
        if row['matrix_stage'] != 'integrated' or row['label'] not in {d['id'] for d in dashboard['datasets']}:
            continue
        profile = 'fast' if row['configuration']['profile'] == 'speed' else row['configuration']['profile']
        old = next(r for r in dashboard['results'] if r['dataset'] == row['label'] and r['method'] == 'cix' and r.get('profile', 'current') == profile)
        n = item['input']['length']; size = row['archive_bytes']; enc = row['encode']['seconds']; dec = row['decode']['seconds']
        references = [r for r in dashboard['results'] if r['dataset'] == row['label'] and r['method'] != 'cix' and r.get('profile','current') == profile and r['status'] == 'VERIFIED']
        assert all(r['original_bytes'] == n and r['input_sha256'] == item['input']['sha256'] for r in references)
        best_ref = min(references, key=lambda r:r['compressed_bytes'])
        ref_gap = size - best_ref['compressed_bytes']
        reference_comparison.append({'label':row['label'], 'profile':row['configuration']['profile'], 'method':best_ref['method'],
            'preset':dashboard['presets'][profile][best_ref['method']], 'reference_bytes':best_ref['compressed_bytes'],
            'selected_bytes':size, 'gap_bytes':ref_gap, 'reason':
            'Best reference preset policy-excluded; not a retention defect' if best_ref['method'] in ('paq8px','brotli') and profile != 'fast' or best_ref['method']=='paq8px' else
            '47-byte wrapper cost' if ref_gap==47 else 'Native route beats the standalone reference' if ref_gap<0 else
            'Non-exhaustive fast shortlist; see framed diagnostic routes and native forced-route oracle',
            'receipt':best_ref['receipt'], 'input_sha256':item['input']['sha256']})
        for stale in ('accounting','search_overhead_seconds','completed_at'):
            old.pop(stale, None)
        old.update(compressed_bytes=size, ratio=n/size, compressed_percent=100*size/n, saving_percent=100*(1-size/n),
                   bits_per_byte=8*size/n, completed_at=backend['collected_at'], cpu=row['budget']['cpu'],
                   encode_seconds=enc, decode_seconds=dec, encode_mib_s=n/1048576/enc, decode_mib_s=n/1048576/dec,
                   encode_rss_mib=row['encode']['peak_rss_kib']/1024, decode_rss_mib=row['decode']['peak_rss_kib']/1024,
                   repetitions=3, preset=f"Integrated CIX · {profile} · {row['selected']}", configuration=row['configuration'],
                   encode_dispersion=row['encode'], decode_dispersion=row['decode'], archive_sha256=row['archive_sha256'],
                   size_range_bytes=[min(r['bytes'] for r in row['encode_repetitions']), max(r['bytes'] for r in row['encode_repetitions'])],
                   route_usage={row['selected']:n}, selection_seconds=statistics.median(row['selection_encode_wall_seconds']),
                   receipt=item['receipt'], encode_command=row['encode_repetitions'][0]['command'],
                   decode_command=row['decode_repetitions'][0]['command'],
                   source_evidence=f'https://github.com/maldous/colour-index-compression/tree/{commit}/docs/research/2026-10-01-backend-retention')
    for row in baseline['rows']:
        shutil.copyfile(row['receipt'], receipts / (row['cell_id'] + '.json'))
    for ds in dashboard['datasets']:
        for profile in ('current', 'fast', 'size'):
            measured = [r for r in dashboard['results'] if r['dataset'] == ds['id'] and r.get('profile','current') == profile and r['status'] == 'VERIFIED']
            for row in measured:
                row['size_rank'] = 1 + sum(r['compressed_bytes'] < row['compressed_bytes'] for r in measured)
                row['measured_methods'] = len(measured)
    now = datetime.now(timezone.utc).isoformat()
    dashboard.update(exported_at=now, research_commit=commit, last_measurement_at=backend['collected_at'])
    method = next(m for m in dashboard['methods'] if m['id'] == 'cix')
    method.update(version='CIXB1 portfolio / unchanged CIXG1; ceb41d6', note='Exact eligible original-byte gzip/bzip2/XZ/zstd routes; Brotli q0 in fast. PAQ and Brotli q6/q11 excluded by generic policy. Every wrapper and inverse transform counted.')
    for p in dashboard['profiles']:
        p['note'] += ' Updated CIX: three measured repetitions, full selection plus validation time. Search limits: fast 0.75s, current 3s, size 60s; independent validation additional. Reference presets unchanged; legacy n=1 timings are provisional.'
    for p in dashboard['presets']:
        dashboard['presets'][p]['cix'] = 'CIXB1 exact backend portfolio + unchanged CIXG1 · ' + p
    dashboard['limitations'].append('Retention round: new CIX backend integration; historical comparison/reference timings retained with their actual repetition counts. Six-slice regression data outside this round remains on the prior CIX build. No global best or full-corpus claim.')
    write(data / 'benchmarks.json', dashboard)
    with (data / 'results.csv').open('w', newline='') as f:
        fields = sorted({k for r in dashboard['results'] for k in r})
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in dashboard['results'])
    public = {'research_commit':commit, 'baseline_commit':'1302bd7bec130c3105181e6a23ee82c6f2a04838',
              'integration_commit':'ceb41d6442da8454c247fd3aed2b31d50c452ada', 'completed_at':backend['collected_at'],
              'counts':report['counts'], 'matrix':report['matrix'], 'ablations':report['ablation_matrix'],
              'offline_oracle':report['offline_oracle'], 'coder_pairs':report['coder_attribution_pairs'],
              'targeted':report['targeted_backend_summaries'], 'portfolio_evidence':report['portfolio_evidence'],
              'backend_rows':backend_public, 'baseline_rows':report['flat_rows'][:1170],
              'coverage':coverage_table(read(ROOT / 'docs/research/2026-09-30-codec-profiles/policy.json')),
              'reference_comparison':reference_comparison,
              'presets':REFERENCE_PRESETS, 'readback':read(BASE / 'independent-readback.json'),
              'pipeline_sha256':hashlib.sha256((ROOT/'cix/pipeline.py').read_bytes()).hexdigest(),
              'limits':{'cores':4,'memory_bytes':12000000000,'temp_bytes':4000000000,'per_cell_seconds':180},
              'policies':report['policies']}
    write(data / 'retention.json', public)
    for src, name in [(AUDIT/'REPORT.md','RETENTION-REPORT.md'),(AUDIT/'rows.csv','retention-results.csv'),
                      (AUDIT/'matrix.json','retention-matrices.json'),(AUDIT/'INVENTORY.md','RETENTION-INVENTORY.md'),
                      (BASE/'source-freeze.json','retention-baseline-freeze.json'),(BACK/'source-freeze.json','retention-backend-freeze.json'),
                      (BACK/'authorization.json','retention-authorization.json'),(BASE/'independent-readback.json','retention-readback.json'),
                      (BACK/'independent-readback.json','retention-backend-readback.json'),(BACK/'FORMAT.md','CIXB1-FORMAT.md')]:
        shutil.copyfile(src,data/name)
    print(json.dumps({'updated_selected_rows':18,'backend_evidence_cells':len(backend_public),'forced_matrix_cells':len(public['matrix']),'public_data_bytes':(data/'retention.json').stat().st_size}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('site',type=Path); parser.add_argument('--research-commit',required=True)
    args=parser.parse_args(); export(args.site,args.research_commit)
