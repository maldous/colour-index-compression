#!/usr/bin/env python3
"""Recompute the paper-defined metrics, preserving incomplete qualifications.

CR is Eq. (1), bits per original BYTE, consistent with supplementary CS/CR.
Wavg uses compressed-byte weights, explicitly printed on p.8 of the paper.
CRP is the population coefficient of variation in Eq. (3). The extra
CRP_table_bridge column is an explicitly inferred diagnostic: paper CRP/sqrt(N),
which reproduces 15 of 16 published aggregate values within rounded precision.
Lstm-compress also has inconsistent dataset-level and aggregate values.
It must not be silently substituted for the published formula.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics

METRICS = ['CR','SSP','CRP','AvgCR','WavgCR','AvgSSP','WavgSSP','CT','DT','CPM','DPM','GPM',
           'AvgCPM','AvgDPM','TotalCT','TotalDT','Params','FLOPs','MIL']
AGGREGATES = ['AvgCR','WavgCR','AvgSSP','WavgSSP','CRP','TotalCT','TotalDT','AvgCPM','AvgDPM']


def aggregate(rows):
    """Only callers with an explicitly qualified universe may expose this."""
    if not rows or any(r['original_bytes'] <= 0 or r['compressed_bytes'] <= 0 for r in rows):
        raise ValueError('Nonempty positive sizes required')
    cr = [8*r['compressed_bytes']/r['original_bytes'] for r in rows]
    ssp = [100*(1-r['compressed_bytes']/r['original_bytes']) for r in rows]
    weights = [r['compressed_bytes']/sum(x['compressed_bytes'] for x in rows) for r in rows]
    mean = statistics.mean(cr)
    out = dict(AvgCR=mean, WavgCR=sum(w*c for w,c in zip(weights, cr)),
               AvgSSP=statistics.mean(ssp), WavgSSP=sum(w*s for w,s in zip(weights, ssp)),
               CRP=statistics.pstdev(cr)/mean*100,
               TotalCT=sum(r['compression_seconds'] for r in rows),
               TotalDT=sum(r['decompression_seconds'] for r in rows),
               AvgCPM=statistics.mean(r['compression_peak_rss_bytes'] for r in rows),
               AvgDPM=statistics.mean(r['decompression_peak_rss_bytes'] for r in rows))
    out['CRP_table_bridge_inferred'] = out['CRP']/math.sqrt(len(rows))
    out['N'] = len(rows)
    return out


def qualify(manifest, measured):
    assert len(manifest) == 28 and {x['dataset_id'] for x in manifest} == {f'D{i}' for i in range(1,29)}
    selected = {r['dataset_id']: r for r in measured if r.get('algorithm') == 'CIX'}
    if len(selected) != sum(r.get('algorithm') == 'CIX' for r in measured):
        raise ValueError('Duplicate CIX dataset/profile result: select one frozen profile')
    qualified = []
    reasons = {}
    for dataset in manifest:
        key = dataset['dataset_id']; row = selected.get(key)
        if dataset.get('compatibility') != 'EXACT':
            reasons[key] = dataset.get('compatibility_explanation', 'Exact NNLCB byte representation has not been established')
        elif row is None:
            reasons[key] = 'No completed local CIX measurement'
        elif row.get('status') != 'VERIFIED':
            reasons[key] = row.get('failure_reason', row.get('status', 'Unverified result'))
        elif row.get('original_sha256') != dataset.get('sha256') or row.get('original_bytes') != dataset.get('obtained_bytes'):
            raise ValueError(f'{key}: measured input differs from qualified input manifest')
        elif row.get('decompressed_sha256') != row.get('original_sha256'):
            raise ValueError(f'{key}: failed reconstruction must not be counted')
        else:
            qualified.append(row)
    complete = len(qualified) == 28
    aggregates = aggregate(qualified) if complete else None
    matrix = []
    dataset_rows = []
    for dataset in manifest:
        key = dataset['dataset_id']; row = selected.get(key)
        dataset_rows.append(dict(dataset, measurement=row))
        for metric in METRICS:
            status, value, explanation = 'NOT REPRODUCIBLE', None, reasons.get(key, '')
            if metric in ('Params','FLOPs','MIL'):
                status = 'UNSUPPORTED'
                explanation = 'Frozen CIX uses adaptive PAQ mixers and sometimes an LSTM; model-operation instrumentation and a dataset-level model accounting definition are not implemented. No artificial zero or N/A is assigned.'
            elif metric == 'GPM':
                status, value = 'NOT APPLICABLE', None
                explanation = 'Frozen CIX executes on the CPU and allocates no GPU model/device memory. This is an architectural fact, not a GPU measurement.'
            elif metric in AGGREGATES:
                if complete:
                    status, value, explanation = 'DERIVED', aggregates[metric], ''
                else:
                    explanation = 'The full 28-dataset exact verified universe is incomplete; no subset aggregate is substituted.'
            elif key not in reasons:
                value = {'CR': 8*row['compressed_bytes']/row['original_bytes'],
                         'SSP': 100*(1-row['compressed_bytes']/row['original_bytes']),
                         'CT': row['compression_seconds'], 'DT': row['decompression_seconds'],
                         'CPM': row['compression_peak_rss_bytes'], 'DPM': row['decompression_peak_rss_bytes']}[metric]
                status, explanation = ('DERIVED' if metric in ('CR','SSP') else 'MEASURED'), ''
            elif row and row.get('status') in ('FAILED','TIMEOUT','RESOURCE LIMIT','HASH MISMATCH') and dataset.get('compatibility') == 'EXACT':
                status = 'FAILED'
            matrix.append(dict(dataset_id=key, metric=metric, status=status, value=value, explanation=explanation))
    assert len(matrix) == 28*19
    assert all(r['explanation'] or r['status'] in ('MEASURED','DERIVED') for r in matrix)
    return dict(exact_datasets=sum(d.get('compatibility')=='EXACT' for d in manifest),
                exact_verified_cix_datasets=len(qualified), complete_qualification=complete,
                aggregate_units=dict(TotalCT='seconds', TotalDT='seconds', AvgCPM='bytes', AvgDPM='bytes', CR='bits/original byte'),
                metric_definition='Paper equations 1–5; compressed-byte weights; CRP=population CV. Table bridge is an explicitly inferred additional metric.',
                aggregates=aggregates, unresolved=reasons, datasets=dataset_rows, matrix=matrix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = qualify(json.loads(args.manifest.read_text()), json.loads(args.results.read_text()))
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    with args.output.with_suffix('.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['dataset_id','metric','status','value','explanation'])
        writer.writeheader(); writer.writerows(report['matrix'])
    print(json.dumps({k:v for k,v in report.items() if k not in ('datasets','matrix')}))


if __name__ == '__main__':
    main()
