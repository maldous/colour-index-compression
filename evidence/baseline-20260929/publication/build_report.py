#!/usr/bin/env python3
"""Render an evidence-only review draft; this command never publishes a Site.

Added after measurement scheduling. Reads frozen measurements and source imports,
does not modify their content, and leaves absent/failed observations visible.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from reproduce_nnlcb_metrics import METRICS, qualify
from verify_arithmetic import check_local

ALGORITHMS = ['gzip', 'bzip2', 'zstd', 'xz', 'brotli', 'zpaq', 'paq8px', 'CIX']
CIX_SHA = 'f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6'
PROFILE = 'high-compression-v1'


def number(value, places=3):
    if value is None:
        return 'Unavailable'
    if isinstance(value, int):
        return f'{value:,}'
    return f'{value:,.{places}f}'


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows])


def validate_local(rows):
    """Never expose success from unverified, mixed-profile or duplicate evidence."""
    check_local(rows)
    seen = set()
    for row in rows:
        key = (row['dataset_id'], row['algorithm'], row['profile'])
        if key in seen or row['profile'] != PROFILE:
            raise ValueError('Duplicate or unexpected profile: ' + str(key))
        seen.add(key)
        if row.get('algorithm') == 'CIX' and row.get('cix_commit') != CIX_SHA:
            raise ValueError('CIX implementation changed')
        if row.get('status') == 'VERIFIED':
            required = 3 if row['original_bytes'] <= 1 << 30 else 1
            if row.get('repetition_count') != required or row.get('required_repetitions') != required:
                raise ValueError('Incomplete measured repetitions claimed as verified')
            if row.get('failures'):
                raise ValueError('Failed measured repetition hidden in a success')


def comparison(dataset_ids, lookup):
    """No projection from partial member coverage to a complete corpus result."""
    rows = []
    for algorithm in ALGORITHMS:
        values = [lookup.get((ident, algorithm)) for ident in dataset_ids]
        complete = all(v and v['status'] == 'VERIFIED' for v in values)
        if not complete:
            statuses = Counter(v['status'] if v else 'NOT MEASURED' for v in values)
            state = '; '.join(f'{k}: {v}' for k, v in sorted(statuses.items()))
            rows.append([algorithm, state] + ['Unavailable'] * 7)
            continue
        original = sum(v['original_bytes'] for v in values)
        compressed = sum(v['compressed_bytes'] for v in values)
        ct = sum(v['compression_seconds'] for v in values)
        dt = sum(v['decompression_seconds'] for v in values)
        rows.append([algorithm, 'VERIFIED', number(compressed), number(original/compressed),
                     number(ct), number(dt), number(original/1048576/ct),
                     number(original/1048576/dt), ', '.join(str(v['repetition_count']) for v in values)])
    return table(['Algorithm', 'Status', 'Compressed bytes', 'Ratio (original/compressed)',
                  'Compression s', 'Decompression s', 'Compression MiB/s', 'Decompression MiB/s',
                  'Measured n per input'], rows)


def build(root, output):
    inputs = {}
    def read(name):
        data = (root/name).read_bytes()
        inputs[name] = hashlib.sha256(data).hexdigest()
        return json.loads(data)
    local = read('results.json')
    validate_local(local)
    datasets = read('manifests/nnlcb-datasets.json')
    qualification = read('tables/nnlcb-qualification.json')
    if qualification != qualify(datasets, local):
        raise ValueError('Qualification table is stale or inconsistent with raw summary inputs')
    if len(qualification['matrix']) != 28 * 19:
        raise ValueError('The required qualification matrix is incomplete')
    published = read('tables/nnlcb-published-aggregates.json')
    published_dataset = read('tables/nnlcb-published-per-dataset.json')
    wiki = read('manifests/wikipedia-input.json')[0]
    environment = read('manifests/environment-preparation.json')
    compressors = read('manifests/compressor-binaries.json')
    schedule = read('raw/controlled-v1-schedule.json')
    lookup = {(r['dataset_id'], r['algorithm']): r for r in local}
    verified = [r for r in local if r['status'] == 'VERIFIED']
    missing = [(e['input']['dataset_id'], a) for e in schedule['datasets'] for a in ALGORITHMS
               if (e['input']['dataset_id'], a) not in lookup]
    blockers = []
    if missing:
        blockers.append(f'{len(missing)} scheduled dataset/algorithm summaries have no completed measured group')
    incomplete = [r for r in local if r['status'] in ('STARTED', 'INCOMPLETE', 'NOT STARTED')]
    if incomplete:
        blockers.append(f'{len(incomplete)} measured groups remain incomplete')
    if not qualification['complete_qualification']:
        blockers.append('Full exact, verified D1–D28 NNLCB qualification and aggregates are unavailable')
    blockers += ['Final adversarial review and raw invocation archive have not been release-certified',
                 'Immutable evidence release tag, archive and separate evidence Site are pending']
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    parts = [
        '# CIX Compression Evidence Baseline — 2026-09-29 / review draft',
        '**INCOMPLETE · NOT PUBLISHED · NOT A PERFORMANCE CLAIM**',
        f'Generated {timestamp}. Frozen CIX `{CIX_SHA}`; profile `{PROFILE}`.',
        '## Executive summary',
        f'{len(verified)} completed local comparison groups. NNLCB input qualification: '
        f'{qualification["exact_datasets"]}/28 exact; full verified CIX coverage: '
        f'{qualification["exact_verified_cix_datasets"]}/28. No subset aggregate replaces the required full universe.',
        'Research portfolio scores are historical research evidence and do not replace these fresh frozen measurements.',
        '## Methodology and measurement boundaries',
        '[Frozen protocol](../../BENCHMARK-METHODOLOGY.md). Normal I/O and encoder internal verification are timed. '
        'Independent artifact-only decoding and source/restored SHA-256 equality are mandatory. '
        'CPU2 affinity, one configured worker, 48 GiB memory and 36-hour per-phase limits apply to every tool. '
        'Heavy R&D and preparation acquire the same exclusive compute lock. '
        'Normal inputs require three measured repetitions after a warm-up; inputs over 1 GiB initially use one full run. '
        'Reported normal timings are medians; every repetition and min/max/MAD remain in results.json. '
        '1 GiB = 1,073,741,824 bytes; 1 MiB = 1,048,576 bytes.',
        '## Hardware and environment',
        f'Environment snapshot: {environment["captured_utc"]}. {environment["platform"]}. '
        'Intel NUC13RNGi9 / Core i9-13900K; 24 physical and 32 logical cores, approximately 62.3 GiB RAM; '
        'NVMe-backed filesystem. The benchmark is restricted to one logical performance-core CPU. '
        'The preparation snapshot is not a claim of an idle host during all later runs. '
        'Each phase records load, memory and disk state. Unrelated user services remain present. '
        '[Full environment manifest](../../manifests/environment-preparation.json).',
        '## Compressor versions and settings',
        table(['Algorithm', 'Recorded version', 'Binary SHA-256'],
              [[r['algorithm'], r['version_output'].splitlines()[0], r['sha256']] for r in compressors] +
              [['CIX', 'portfolio 25, commit '+CIX_SHA, 'Seven native binaries and isolated Python environment; see manifests']]),
        'Exact options: gzip -9 -n; bzip2 -9; zstd --ultra -22 --long=27 -T1; xz -9e -T1; '
        'Brotli -q 11 -w 24; ZPAQ method 5 / threads 1; paq8px v215 -12L -simd AVX2; '
        'CIX default competitive_cli encode/decode. This report contains only the high-compression-v1 profile. '
        '[Binary manifest](../../manifests/compressor-binaries.json), [build manifest](../../manifests/cix-fresh-build.json).',
        '## Silesia historical comparison',
        'Canonical 12 files, independently compressed. Original total: 211,938,580 bytes. '
        'A complete total requires all 12 verified results. Summed per-file median times are explicitly aggregate times, '
        'not the median of a separate whole-corpus invocation. NNLCB D19 concatenation remains a separate issue.',
        comparison([f'D{i}' for i in range(1,13)], lookup),
        '## Entire English Wikipedia — 2026-09-01 pages/articles snapshot',
        f'Original XML: **{wiki["obtained_bytes"]:,} bytes ({wiki["obtained_bytes"]/2**30:.6f} GiB)**. '
        f'SHA-256 `{wiki["sha256"]}`. {wiki["scope"]} '
        'Every compressor receives the full identical decompressed XML stream. Source download bytes are not the benchmark input. '
        '[Acquisition and preparation](../../manifests/wikipedia-input.json).',
        comparison([wiki['dataset_id']], lookup),
        'No Wikipedia compression headline or improvement percentage exists until the corresponding verified measurements exist.',
        '## CIX vs NNLCB — Independent Benchmark Compatibility',
        '[NNLCB](https://fahaihi.github.io/NNLCB/) evaluates 28 datasets using 19 metrics. '
        'Source: Sun et al., [DOI 10.1007/s11704-024-40300-5](https://doi.org/10.1007/s11704-024-40300-5); '
        'upstream commit 91eeea5094a49bd1e60fa9ee4bf3a8e50891da63; retrieved 2026-09-29. '
        'This is our compatibility investigation, not independent validation of CIX by the NNLCB authors.',
        '### View 1 — Published NNLCB reference measurements',
        'Values below are preserved as reported, on the NNLCB platform: four Xeon Silver 4310 CPUs, '
        '48 reported CPU cores, four RTX 4090 GPUs, 128 GB RAM and Ubuntu 20.04.6. '
        'The later server-memory upgrade is separately recorded by the source. '
        'Do not compare these times or memory values directly with local CIX timings.',
        table(['Algorithm','WavgCR','AvgCR','WavgSSP','AvgSSP','CRP','TotalCT h','TotalDT h','AvgCPM reported GB','AvgDPM reported GB'],
              [[r['algorithm']] + [r[k] for k in ('WavgCR','AvgCR','WavgSSP','AvgSSP','CRP','TotalCT_hours','TotalDT_hours','AvgCPM_reported_GB','AvgDPM_reported_GB')] for r in published]),
        'CR uses bits per original byte. Weighted values use compressed-byte weights. '
        'Published CRP differs from the paper equation by an inferred factor of sqrt(28) for 15/16 algorithms; '
        'Lstm-compress has additional inconsistent aggregates. Both authoritative tables are retained unchanged. '
        '[Source reconciliation](../../NNLCB-COMPATIBILITY-NOTES.md).',
        '### View 2 — Controlled local measurements',
        'All local algorithms use the same machine, byte streams, process limits and harness. '
        'CIX NNLCB aggregates: '+('available in the qualification JSON under the paper-defined formulas' if qualification['aggregates'] else '**Unavailable — full 28-dataset verified coverage is incomplete.**'),
        'The following per-dataset sections keep published reference rows separate from local rows. '
        'Published CS and resource units retain their original labels; CS numerically reconciles with binary MiB. '
        'Rounded published CS values are not exact compressed byte counts.',
    ]
    bridge = []
    for d in datasets:
        ident = d['dataset_id']
        refs = [r for r in published_dataset if r['dataset_id'] == ident]
        cix = lookup.get((ident, 'CIX'))
        bridge.append(dict(dataset=d, cix=cix, published_nnlcb=refs,
                           local=[lookup[(ident,a)] for a in ALGORITHMS if (ident,a) in lookup]))
        parts += [f'### {ident} {d["name"]}',
                  f'Published expected bytes: {d["expected_bytes"]:,}. Compatibility: **{d["compatibility"]}**. '
                  +d.get('compatibility_explanation',''),
                  f'Exact local input bytes: {number(d.get("obtained_bytes"))}; SHA-256: `{d.get("sha256", "UNRESOLVED")}`.',
                  '**Controlled local comparison — high-compression-v1**', comparison([ident], lookup),
                  '**Published NNLCB platform — not local timing**',
                  table(['Algorithm','CS reported MegaBytes','CR bits/byte','CT min','DT min','CPM reported MegaBytes','DPM reported MegaBytes'],
                        [[r['algorithm']] + [r[k] for k in ('CS_reported_MegaBytes','CR','CT_minutes','DT_minutes','CPM_reported_MegaBytes','DPM_reported_MegaBytes')] for r in refs])]
    counts = Counter(r['status'] for r in qualification['matrix'])
    parts += ['## Full 28 × 19 qualification matrix',
              table(['Status','Cells'], sorted(counts.items())),
              'All 532 statuses and explanations: [CSV](../../tables/nnlcb-qualification.csv) / '
              '[JSON](../../tables/nnlcb-qualification.json). No blank cells. '
              'GPU memory is N/A because CIX is CPU-only. Params/FLOPs/MIL are unsupported instrumentation, '
              'not zero: the implementation contains adaptive PAQ mixers and sometimes an LSTM. '
              'The vocabulary is: '+', '.join(METRICS)+'.',
              '## Synthetic scaling — separate from real-world corpus evidence',
              'Thirteen deterministic classes, each scheduled at 10 MiB, 100 MiB, 1 GiB and 10 GiB. '
              'Generators use a fixed seed and SHAKE256; the heterogeneous composite mixes classes. '
              'Public generator state is not supplied to any compressor. '
              '[Generator](../../scripts/generate_synthetic.py). Missing 10 GiB measurements are never extrapolated.']
    synthetic = [e['input'] for e in schedule['datasets'] if e['input']['dataset_id'].startswith('SYN-')]
    for d in synthetic:
        parts += [f'### {d["name"]}', comparison([d['dataset_id']], lookup)]
    parts += ['## Compression time, decompression time and memory',
              'The local comparison tables show both wall times and throughput. '
              'Peak memory is largest-process kernel RSS; sampled summed process-tree RSS is retained separately '
              'and may double-count shared pages or miss brief peaks. No cross-hardware speed ranking is implied. '
              'Input-size/resource scaling conclusions require completed size-series observations.',
              table(['Dataset','Algorithm','Compression peak RSS bytes','Decompression peak RSS bytes'],
                    [[r['dataset_id'],r['algorithm'],number(r['compression_peak_rss_bytes']),number(r['decompression_peak_rss_bytes'])] for r in verified]),
              '## Reproduction and raw evidence',
              '[CSV results](../../results.csv) · [JSON results](../../results.json) · '
              '[Frozen schedule](../../raw/controlled-v1-schedule.json) · '
              '[NNLCB dataset manifest](../../manifests/nnlcb-datasets.json) · '
              '[Reference rows](../../tables/nnlcb-published-per-dataset.json) · '
              '[Qualification/recomputation](../../scripts/reproduce_nnlcb_metrics.py). '
              'Run the documented serial harness from the evidence repository. Exact wrapped commands, versions, '
              'hashes and raw-result paths accompany every completed result. Public-source acquisitions are pinned by hash. '
              'The final downloadable invocation archive and immutable release reference remain pending.',
              '## Limitations, failures and completion blockers',
              '\n'.join('- '+b for b in blockers),
              table(['Dataset','Algorithm','Status','Reason'],
                    [[r['dataset_id'],r['algorithm'],r['status'],r.get('failure_reason','')] for r in local if r['status']!='VERIFIED']),
              'The interrupted D1 CIX warm-up is preserved separately and was repeated only after its process '
              'was confirmed absent. No timing or size was inferred. Warm-ups and smoke tests are excluded '
              'from primary comparisons. [Execution record](../../EXECUTION-STATUS.md). '
              'A preparation tag is not an evidence release; this draft does not satisfy the publication gate.']
    # Do not emit a report if an input changed while being read/rendered.
    for name, sha in inputs.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != sha:
            raise RuntimeError('Input changed during report generation: '+name)
    output.mkdir(parents=True, exist_ok=True)
    (output/'REPORT.md').write_text('\n\n'.join(parts)+'\n')
    (output/'nnlcb-comparison-bridge.json').write_text(json.dumps(bridge,indent=2)+'\n')
    receipt = dict(generated_utc=timestamp, cix_commit=CIX_SHA, profile=PROFILE,
                   publication_ready=False, completion_blockers=blockers,
                   verified_local_groups=len(verified), qualified_input_datasets=qualification['exact_datasets'],
                   exact_verified_cix_datasets=qualification['exact_verified_cix_datasets'],
                   qualification_cells=len(qualification['matrix']), source_sha256=inputs,
                   report_sha256=hashlib.sha256((output/'REPORT.md').read_bytes()).hexdigest(),
                   generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'report-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,default=ROOT/'publication/draft')
    args=parser.parse_args()
    build(args.root,args.output)
