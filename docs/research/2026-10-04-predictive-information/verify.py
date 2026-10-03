"""Independent streaming recomputation of the frozen held-out decision."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
BASE = ROOT / 'benchmark-work/predictive-information'


def main():
    results = json.loads((AREA / 'results.json').read_text())
    trained = json.loads((AREA / 'trained.json').read_text())
    freeze = json.loads((AREA / 'freeze.json').read_text())
    assert hashlib.sha256((AREA / 'trained.json').read_bytes()).hexdigest() == freeze['trained_sha256_before_heldout']
    names = trained['names']
    totals = [0.0] * len(names)
    oracle = 0.0
    selected = 0.0
    count = 0
    costs = {}
    per_file = []
    for record in json.loads((AREA / 'inputs.json').read_text()):
        if record['split'] != 'heldout' or record['family'] == 'artificial' or record.get('exclude_from_primary'):
            continue
        trace = BASE / 'traces' / (record['label'] + '.tsv.gz')
        receipt = next(row for row in results['files'] if row['label'] == record['label'])
        assert hashlib.sha256(trace.read_bytes()).hexdigest() == receipt['trace_sha256']
        current_file = 0.0
        previous = None
        run = 0
        with gzip.open(trace, 'rt') as stream:
            for position, row in enumerate(csv.DictReader(stream, delimiter='\t')):
                assert int(row['position']) == position
                assert int(row['run_length']) == run
                probabilities = [float(row[name + '__p_actual']) for name in names]
                actual = int(row['actual'])
                bucket = (2 if run >= 8 else 1 if run >= 2 else 0) * 2 + int(row['match_available'])
                weights = trained['gate_weights'][bucket] if trained['selected_causal'] == 'context_gate' else trained['static']
                mixed = math.fsum(weight * probability for weight, probability in zip(weights, probabilities))
                current_file -= math.log2(mixed)
                oracle -= math.log2(max(probabilities))
                for index, probability in enumerate(probabilities):
                    totals[index] -= math.log2(probability)
                run = run + 1 if previous == actual else 1
                previous = actual
                count += 1
        assert abs(current_file - receipt['selected_causal_bits']) < 1e-6
        selected += current_file
        per_file.append(dict(label=record['label'], selected_bits=current_file))
        summary = BASE / 'traces' / (record['label'] + '.tsv.summary.tsv')
        with summary.open() as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                if row['eligible_normalized_byte_distribution'] != 'yes':
                    continue
                expert = row['expert']
                cost = costs.setdefault(expert, dict(predict_group_seconds=0, update_group_seconds=0,
                            maximum_estimated_group_state_bytes=0, note=row['note']))
                cost['predict_group_seconds'] += int(row['predict_group_nanos']) / 1e9
                cost['update_group_seconds'] += int(row['observe_group_nanos']) / 1e9
                cost['maximum_estimated_group_state_bytes'] = max(cost['maximum_estimated_group_state_bytes'], int(row['estimated_group_state_bytes']))
    assert count == results['real_heldout_bytes']
    assert abs(min(totals) - results['best_single_bits']) < 1e-6
    assert abs(min(totals) - selected - results['captured_bits']) < 1e-6
    assert abs(min(totals) - oracle - results['oracle_gap_bits']) < 1e-6
    nulls = json.loads((AREA / 'null-controls.json').read_text())
    assert abs(nulls['duplicate']['oracle_gap']) < 1e-6
    assert not results['material_gate_pass']
    for path in ['complementarity.json', 'null-controls.json', 'marginal-information.json', 'residual-attribution.json']:
        assert (AREA / path).read_bytes() == (AREA / 'failed-evaluation-v1' / path).read_bytes(), 'report-key repair altered earlier computed evidence'
    evidence = dict(status='PASS', independent_streaming_bytes=count, best_single_bits=min(totals),
                    selected_bits=selected, oracle_bits=oracle, captured_bits=min(totals)-selected,
                    checks=['trained weights unchanged since pre-held-out freeze', 'trace hashes', 'all pretarget run lengths',
                            'independent scalar log-loss aggregation', 'duplicate oracle gap zero', 'material gate failed',
                            'analysis output-key repair leaves all earlier calculations byte-identical'])
    (AREA / 'verification.json').write_text(json.dumps(evidence, indent=2) + '\n')
    (AREA / 'costs.json').write_text(json.dumps(dict(experts=costs, caveats=[
        'Costs are wall-clock instrumentation nanos, one observation per file, not isolated production CPU benchmarks.',
        'Context and FixedMix family costs are shared, repeated per expert and not additive.',
        'Estimated state is a heuristic container estimate, not measured allocated or peak bytes.',
        'Exact standalone component state/update costs and mixed physical decoder costs remain unmeasured.',
        'Prefix-tree enumeration visits all byte branches; a native bit decoder follows only one branch.'
    ]), indent=2) + '\n')
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__':
    main()
