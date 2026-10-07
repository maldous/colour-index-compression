"""Frozen CPI1 diagnostic calculations; never an archive-size estimator."""
import argparse
import csv
import hashlib
import gzip
import json
import math
import os
from pathlib import Path
import time

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
BASE = ROOT / 'benchmark-work/predictive-information'
ORACLE = 'HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(split):
    records = json.loads((AREA / 'inputs.json').read_text())
    loaded = []
    names = None
    for record in records:
        if record['split'] != split:
            continue
        path = BASE / 'traces' / (record['label'] + '.tsv.gz')
        with gzip.open(path, 'rt') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            current = [key[:-10] for key in reader.fieldnames if key.endswith('__p_actual')]
            if names is None:
                names = current
            assert names == current and names
            rows = list(reader)
        probabilities = np.array([[float(row[name + '__p_actual']) for name in names] for row in rows])
        entropy = np.array([[float(row[name + '__entropy_bits']) for name in names] for row in rows])
        confidence = np.array([[float(row[name + '__max_probability']) for name in names] for row in rows])
        tops = np.array([[int(row[name + '__top_symbol']) for name in names] for row in rows])
        actual = np.array([int(row['actual']) for row in rows])
        run = np.array([int(row['run_length']) for row in rows])
        match = np.array([int(row['match_available']) for row in rows])
        buckets = np.where(run >= 8, 2, np.where(run >= 2, 1, 0)) * 2 + match
        noise = [np.array([[float(row[name + '__noise' + str(seed)]) for name in names] for row in rows]) for seed in range(4)]
        assert len(rows) == record['bytes'] and np.all(probabilities > 0) and np.all(probabilities <= 1 + 1e-12)
        loaded.append(dict(record=record, probability=probabilities, entropy=entropy,
                           confidence=confidence, top=tops, actual=actual, buckets=buckets,
                           noise=noise, trace_sha256=digest(path)))
    return names, loaded


def fit(probabilities, prior=None, pseudo=0):
    weights = np.ones(probabilities.shape[1]) / probabilities.shape[1]
    if prior is None:
        prior = weights.copy()
    for iteration in range(500):
        responsibility = probabilities * weights / (probabilities @ weights)[:, None]
        weights = (responsibility.sum(axis=0) + pseudo * prior) / (len(probabilities) + pseudo)
        weights = np.maximum(weights, 1e-12)
        weights /= weights.sum()
    return weights


def online(probabilities, eta=1.0, alpha=0.0):
    count, experts = probabilities.shape
    weights = np.ones(experts) / experts
    predictions = np.empty(count)
    for position, observed in enumerate(probabilities):
        predictions[position] = weights @ observed
        log_weights = np.log(np.maximum(weights, 1e-300)) + eta * np.log(observed)
        log_weights -= log_weights.max()
        weights = np.exp(log_weights)
        weights /= weights.sum()
        weights = (1 - alpha) * weights + alpha / experts
    return -np.log2(predictions)


def switching(probabilities, alpha):
    losses = -np.log2(probabilities)
    experts = probabilities.shape[1]
    costs = np.ones(experts) * math.log2(experts)
    changes = np.zeros(experts, dtype=int)
    stay = -math.log2(1 - alpha + alpha / experts)
    change = -math.log2(alpha / experts) if alpha else float('inf')
    for position, row in enumerate(losses):
        if position:
            best = int(costs.argmin())
            switched = costs[best] + change < costs + stay
            changes = np.where(switched, changes[best] + 1, changes)
            costs = np.minimum(costs + stay, costs[best] + change)
        costs += row
    chosen = int(costs.argmin())
    return dict(bits=float(costs[chosen]), switches=int(changes[chosen]),
                label='NON-CAUSAL penalized switching path; predictive loss plus initial/transition complexity')


def method_losses(probabilities, buckets, frozen):
    static = np.array(frozen['static'])
    output = {'equal_static': -np.log2(probabilities.mean(axis=1)),
              'optimized_static': -np.log2(probabilities @ static)}
    if frozen['online_enabled']:
        output['bayesian'] = online(probabilities)
        output['hedge'] = online(probabilities, frozen['eta'])
        output['fixed_share'] = online(probabilities, frozen['share_eta'], frozen['alpha'])
    if frozen['gate_enabled']:
        weights = np.array(frozen['gate_weights'])
        output['context_gate'] = -np.log2((probabilities * weights[buckets]).sum(axis=1))
    return output


def validate():
    duplicate = np.full((16, 2), 0.75)
    assert np.allclose(online(duplicate), -np.log2(duplicate[:, 0]))
    regimes = np.array([[0.9, 0.1]] * 16 + [[0.1, 0.9]] * 16)
    individual = -np.log2(regimes).sum(axis=0)
    oracle = -np.log2(regimes.max(axis=1)).sum()
    assert np.isclose(oracle, -32 * math.log2(0.9))
    bayes = online(regimes).sum()
    reference = -math.log2((np.prod(regimes[:, 0]) + np.prod(regimes[:, 1])) / 2)
    assert np.isclose(bayes, reference)
    assert oracle < 32 < individual.min()
    alternating = np.array([[0.9, 0.1], [0.1, 0.9]] * 16)
    predeclared_context_prediction = alternating[np.arange(32), np.arange(32) % 2]
    assert np.allclose(predeclared_context_prediction, 0.9)
    assert switching(regimes, 1 / 16)['switches'] == 1
    prefix = online(regimes[:20], 0.5, 1 / 16)
    assert np.array_equal(prefix, online(regimes, 0.5, 1 / 16)[:20])
    write(AREA / 'analysis-validation.json', dict(status='PASS', duplicate_bits=float(online(duplicate).sum()),
          regime_individual_bits=individual.tolist(), oracle_bits=float(oracle), bayesian_bits=float(bayes),
          static_bits=32, context_identifiable_bits=float(-np.log2(predeclared_context_prediction).sum()),
          switching=switching(regimes, 1 / 16), checks=['closed-form duplicate', 'closed-form oracle',
          'Bayesian evidence identity', 'known regime switch', 'causal alternating context', 'online suffix invariance']))


def train():
    validate()
    names, files = load('development')
    real = [item for item in files if item['record']['family'] != 'artificial' and not item['record'].get('exclude_from_primary')]
    probability = np.concatenate([item['probability'] for item in real])
    buckets = np.concatenate([item['buckets'] for item in real])
    static = fit(probability)
    best = int((-np.log2(probability).sum(axis=0)).argmin())
    static_gain = float((-np.log2(probability[:, best]).sum() + np.log2(probability @ static).sum()) / len(probability))
    frozen = dict(names=names, static=static.tolist(), best_development=best,
                  online_enabled=static_gain >= 0.01, gate_enabled=False,
                  development_static_gain_bits_per_byte=static_gain)
    tuning = []
    if frozen['online_enabled']:
        for eta in [0.25, 0.5, 1.0]:
            for alpha in [0, 1 / 1024, 1 / 128, 1 / 16]:
                total = sum(online(item['probability'], eta, alpha).sum() for item in real)
                tuning.append(dict(eta=eta, alpha=alpha, bits=float(total)))
        chosen_hedge = min((row for row in tuning if row['alpha'] == 0), key=lambda row: row['bits'])
        chosen_share = min(tuning, key=lambda row: row['bits'])
        frozen.update(eta=chosen_hedge['eta'], share_eta=chosen_share['eta'], alpha=chosen_share['alpha'])
        oracle = -np.log2(probability.max(axis=1)).sum()
        if (chosen_share['bits'] - oracle) / len(probability) >= 0.1:
            gate = np.array([fit(probability[buckets == bucket], static, 256) if np.any(buckets == bucket) else static for bucket in range(6)])
            gate_loss = float(-np.log2((probability * gate[buckets]).sum(axis=1)).sum())
            frozen['gate_development_bits'] = gate_loss
            frozen['gate_enabled'] = chosen_share['bits'] - gate_loss >= 0.01 * len(probability)
            frozen['gate_weights'] = gate.tolist()
    totals = {}
    for item in real:
        for name, loss in method_losses(item['probability'], item['buckets'], frozen).items():
            totals[name] = totals.get(name, 0.0) + float(loss.sum())
    frozen['selected_causal'] = min(totals, key=totals.get)
    frozen['development_method_bits'] = totals
    frozen['tuning'] = tuning
    frozen['training_trace_hashes'] = {item['record']['label']: item['trace_sha256'] for item in files}
    frozen['leave_one_out_static'] = [fit(np.delete(probability, index, axis=1)).tolist() for index in range(len(names))]
    assert not (AREA / 'trained.json').exists(), 'training freeze already exists'
    write(AREA / 'trained.json', frozen)
    print(json.dumps({key: frozen[key] for key in ['selected_causal', 'online_enabled', 'gate_enabled', 'development_method_bits']}), flush=True)


def oracle_summary(probability):
    totals = -np.log2(probability).sum(axis=0)
    oracle = float(-np.log2(probability.max(axis=1)).sum())
    best = float(totals.min())
    return dict(best_single_bits=best, oracle_bits=oracle, oracle_gap=best - oracle,
                oracle_gap_percent=100 * (best - oracle) / best if best else 0, label=ORACLE)


def evaluate():
    start = time.perf_counter()
    frozen = json.loads((AREA / 'trained.json').read_text())
    names, files = load('heldout')
    assert names == frozen['names']
    real = [item for item in files if item['record']['family'] != 'artificial' and not item['record'].get('exclude_from_primary')]
    probability = np.concatenate([item['probability'] for item in real])
    losses = -np.log2(probability)
    entropy = np.concatenate([item['entropy'] for item in real])
    confidence = np.concatenate([item['confidence'] for item in real])
    tops = np.concatenate([item['top'] for item in real])
    actual = np.concatenate([item['actual'] for item in real])
    nbytes, experts = probability.shape
    methods = {key: np.concatenate([method_losses(item['probability'], item['buckets'], frozen)[key] for item in real]) for key in method_losses(real[0]['probability'], real[0]['buckets'], frozen)}
    best = int(losses.sum(axis=0).argmin())
    oracle_loss = losses.min(axis=1)
    rows = []
    for index, name in enumerate(names):
        rows.append(dict(name=name, ideal_bits=float(losses[:, index].sum()), bits_per_input_byte=float(losses[:, index].mean()),
                         highest_probability_positions=int(np.sum(np.isclose(losses[:, index], oracle_loss, atol=1e-12, rtol=0))),
                         mean_entropy=float(entropy[:, index].mean()), mean_confidence=float(confidence[:, index].mean()),
                         top_accuracy=float(np.mean(tops[:, index] == actual))))
    for name, loss in methods.items():
        rows.append(dict(name=name, ideal_bits=float(loss.sum()), bits_per_input_byte=float(loss.mean())))
    rows.append(dict(name=ORACLE, ideal_bits=float(oracle_loss.sum()), bits_per_input_byte=float(oracle_loss.mean())))
    selected = methods[frozen['selected_causal']]
    gap = float(losses[:, best].sum() - oracle_loss.sum())
    captured = float(losses[:, best].sum() - selected.sum())
    file_rows = []
    for item in files:
        single = -np.log2(item['probability']).sum(axis=0)
        method = method_losses(item['probability'], item['buckets'], frozen)
        file_rows.append(dict(label=item['record']['label'], family=item['record']['family'], exclude_from_primary=item['record'].get('exclude_from_primary'), bytes=len(item['probability']),
                              best_single=names[int(single.argmin())], best_single_bits=float(single.min()),
                              selected_causal_bits=float(method[frozen['selected_causal']].sum()),
                              captured_bits=float(single.min() - method[frozen['selected_causal']].sum()),
                              methods={key: float(value.sum()) for key, value in method.items()},
                              trace_sha256=item['trace_sha256']))
    pairs = []
    for first in range(experts):
        for second in range(first + 1, experts):
            delta = losses[:, second] - losses[:, first]
            covariance = float(np.corrcoef(losses[:, first], losses[:, second])[0, 1])
            if not math.isfinite(covariance):
                covariance = None
            tail = losses[:, second] > 8
            uncertain = entropy[:, second] > 6
            pairs.append(dict(first=names[first], second=names[second], correlation=covariance,
                              first_wins_1bit=int(np.sum(delta > 1)), second_wins_1bit=int(np.sum(delta < -1)),
                              first_wins_4bit=int(np.sum(delta > 4)), second_wins_4bit=int(np.sum(delta < -4)),
                              disagreement_fraction=float(np.mean(tops[:, first] != tops[:, second])),
                              mean_absolute_loss_difference=float(np.mean(np.abs(delta))),
                              first_gain_when_second_loss_above8=float(delta[tail].sum()), tail_positions=int(tail.sum()),
                              first_gain_when_second_entropy_above6=float(delta[uncertain].sum()), uncertain_positions=int(uncertain.sum()),
                              second_gain_when_first_loss_above8=float(-delta[losses[:, first] > 8].sum())))
    write(AREA / 'complementarity.json', pairs)
    nulls = {}
    baseline = probability[:, frozen['best_development']]
    null_sets = {'duplicate': np.repeat(baseline[:, None], 4, axis=1),
                 'redundant_uniform_smoothing': np.column_stack([baseline] + [(1 - epsilon) * baseline + epsilon / 256 for epsilon in [0.01, 0.05, 0.1]]),
                 'weak': np.column_stack([np.full(nbytes, 1 / 256), probability[:, names.index('adaptive_o0')]])}
    for name, matrix in null_sets.items():
        summary = oracle_summary(matrix)
        summary['equal_static_bits'] = float(-np.log2(matrix.mean(axis=1)).sum())
        offset = 0
        causal_bits = 0.0
        for item in real:
            causal_bits += float(online(matrix[offset:offset + len(item['probability'])]).sum())
            offset += len(item['probability'])
        summary['causal_bayesian_bits'] = causal_bits
        summary['causal_captured_bits'] = summary['best_single_bits'] - causal_bits
        nulls[name] = summary
    rng = np.random.default_rng(20261004)
    shuffled = []
    for repeat in range(16):
        broken = np.concatenate([np.column_stack([rng.permutation(item['probability'][:, index]) for index in range(experts)]) for item in real])
        shuffled.append(oracle_summary(broken))
    nulls['alignment_broken'] = dict(label='INVALID aligned forecasts; oracle selection-bias diagnostic only', repetitions=shuffled)
    noise_results = []
    noise_duplicate_results = []
    for seed in range(4):
        matrix = np.concatenate([item['noise'][seed] for item in real])
        summary = oracle_summary(matrix)
        summary['mean_absolute_individual_loss_change_bits_per_byte'] = float(np.mean(np.abs(-np.log2(matrix).sum(axis=0) - losses.sum(axis=0))) / nbytes)
        summary['selected_causal_bits'] = float(sum(method_losses(item['noise'][seed], item['buckets'], frozen)[frozen['selected_causal']].sum() for item in real))
        summary['captured_bits'] = summary['best_single_bits'] - summary['selected_causal_bits']
        noise_results.append(summary)
    noisy_copies = np.column_stack([np.concatenate([item['noise'][seed][:, frozen['best_development']] for item in real]) for seed in range(4)])
    nulls['normalized_noise_around_each_expert'] = noise_results
    nulls['independent_noisy_copies_of_one_expert'] = oracle_summary(noisy_copies)
    nulls['independent_noisy_copies_of_one_expert']['causal_bayes_bits'] = float(sum(online(np.column_stack([item['noise'][seed][:, frozen['best_development']] for seed in range(4)])).sum() for item in real))
    random_matrix = np.where(rng.random((nbytes, experts)) < 1 / 256, 0.5, 0.5 / 255)
    nulls['independent_random_symbol_weak'] = oracle_summary(random_matrix)
    nulls['independent_random_symbol_weak']['quality_warning'] = 'Independent uniform-symbol forecasts cannot match informative experts below 8 bits/byte; fixed confidence 0.5, no matched-quality claim.'
    write(AREA / 'null-controls.json', nulls)
    marginal = []
    full_static = methods['optimized_static'].sum()
    for index, name in enumerate(names):
        matrix = np.delete(probability, index, axis=1)
        static_loss = float(-np.log2(matrix @ np.array(frozen['leave_one_out_static'][index])).sum())
        row = dict(expert=name, static_removal_cost_bits=static_loss - full_static)
        if frozen['online_enabled']:
            reduced = sum(online(np.delete(item['probability'], index, axis=1), frozen['share_eta'], frozen['alpha']).sum() for item in real)
            row['fixed_share_removal_cost_bits'] = float(reduced - methods['fixed_share'].sum())
        marginal.append(row)
    write(AREA / 'marginal-information.json', marginal)
    regret = np.maximum(selected - oracle_loss, 0)
    cumulative = np.cumsum(np.sort(regret)[::-1])
    fractions = {str(percent): float((np.searchsorted(cumulative, regret.sum() * percent / 100) + 1) / nbytes) for percent in [50, 90]}
    winners = losses.argmin(axis=1)
    attribution = {name: float(regret[winners == index].sum()) for index, name in enumerate(names)}
    buckets = np.concatenate([item['buckets'] for item in real])
    residual = dict(reference=ORACLE, excess_bits=float(regret.sum()), positions_fraction_for_excess=fractions,
                    rescuer_identity_bits=attribution, interpretation='Predictor identity attribution, not proof of a structural cause; ties use frozen expert order.',
                    pretarget_bucket_bits={str(bucket): float(regret[buckets == bucket].sum()) for bucket in range(6)},
                    loss_above8_positions=int(np.sum(selected > 8)), loss_above8_bits=float(selected[selected > 8].sum()))
    clusters = []
    for item in real:
        local = method_losses(item['probability'], item['buckets'], frozen)[frozen['selected_causal']] + np.log2(item['probability'].max(axis=1))
        starts = np.flatnonzero(np.r_[True, ~(local[:-1] > 1)] & (local > 1))
        for begin in starts:
            end = int(begin)
            while end < len(local) and local[end] > 1:
                end += 1
            clusters.append(dict(label=item['record']['label'], start=int(begin), length=end-int(begin), excess_bits=float(local[begin:end].sum())))
    residual['largest_contiguous_over1bit_clusters'] = sorted(clusters, key=lambda row: row['excess_bits'], reverse=True)[:20]
    write(AREA / 'residual-attribution.json', residual)
    switch = [dict(file=item['record']['label'], **switching(item['probability'], frozen.get('alpha', 0))) for item in real]
    real_file_rows = [row for row in file_rows if row['family'] != 'artificial' and not row.get('exclude_from_primary')]
    majority = sum(row['captured_bits'] > 0 for row in real_file_rows)
    noisy_null = nulls['independent_noisy_copies_of_one_expert']
    null_capture = noisy_null['best_single_bits'] - noisy_null['causal_bayes_bits']
    material = captured / nbytes >= 0.05 and captured / losses[:, best].sum() >= 0.01 and majority > len(real_file_rows) / 2 and captured > max(0, null_capture)
    result = dict(schema='CPI1', ideal_only=True, real_heldout_bytes=nbytes, expert_count=experts,
                  rows=rows, best_single=names[best], best_single_bits=float(losses[:, best].sum()),
                  development_selected_single=names[frozen['best_development']],
                  development_selected_single_bits=float(losses[:, frozen['best_development']].sum()),
                  per_file_best_sum_bits=sum(row['best_single_bits'] for row in real_file_rows),
                  selected_causal=frozen['selected_causal'], captured_bits=captured,
                  captured_bits_per_byte=captured / nbytes, gain_percent=100 * captured / float(losses[:, best].sum()),
                  oracle_gap_bits=gap, captured_gap_percent=100 * captured / gap if gap else None,
                  remaining_oracle_gap_bits=float(selected.sum() - oracle_loss.sum()),
                  real_files_beating_per_file_best=majority, real_files=len(real_file_rows),
                  independent_noise_null_capture_bits=null_capture, material_gate_pass=bool(material),
                  files=file_rows, switching=switch, analysis_seconds=time.perf_counter() - start,
                  trained_sha256=digest(AREA / 'trained.json'))
    write(AREA / 'results.json', result)
    print(json.dumps({key: result[key] for key in ['best_single', 'selected_causal', 'gain_percent', 'captured_gap_percent', 'real_files_beating_per_file_best', 'material_gate_pass']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['validate', 'train', 'evaluate'])
    args = parser.parse_args()
    {'validate': validate, 'train': train, 'evaluate': evaluate}[args.phase]()
