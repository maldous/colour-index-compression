"""RELEASE-PREDICTIVE-1 ideal-loss analysis.  Never estimates archive bytes."""
import argparse, csv, hashlib, json, math, subprocess
from pathlib import Path
import numpy as np

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
WORK = ROOT / 'benchmark-work' / 'release-opportunities'
FREEZE = AREA / 'prediction-freeze.json'
TRAINED = AREA / 'prediction-trained.json'
RESULTS = AREA / 'PREDICTION-RESULTS.md'
RESULTS_JSON = AREA / 'prediction-results.json'
EXPERTS = ['fixedmix_v1', 'fixedmix_v3_n1', 'fixedmix_v3_n2']

def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2) + '\n')
def loss(probabilities): return sum(-math.log2(max(p, 1e-300)) for p in probabilities)
def trace_path(sample): return WORK / 'traces' / (sample['id'] + '.tsv')
def dirichlet_actual(sample_id, position, actual, seed):
    """The full Q is generated before target use; return only Q[actual]."""
    state = int.from_bytes(hashlib.sha256(f'{sample_id}:{position}:{seed}'.encode()).digest()[:8], 'little') or 1
    values=[]
    for _ in range(256):
        state ^= state << 13; state ^= state >> 7; state ^= state << 17; state &= (1 << 64) - 1
        values.append(-math.log((state + 1) / ((1 << 64) + 1)))
    return values[actual] / sum(values)

def freeze():
    if TRAINED.exists() or RESULTS.exists(): raise SystemExit('cannot replace freeze after training or heldout analysis')
    if FREEZE.exists() and json.loads(FREEZE.read_text()).get('status') != 'PRE_DATA_TEMPLATE — predictive.py freeze must replace this before any trace run':
        raise SystemExit('prediction freeze already exists')
    inventory = json.loads((AREA / 'local-assets.json').read_text())['inventory']
    rows, seen = [], set()
    for group in inventory:
        if group['id'].startswith('silesia') or group['kind'] not in {'standard-corpus', 'pathology-corpus'}: continue
        for member in group.get('members', []):
            path = Path(group['root']) / member
            if not path.is_file() or path.stat().st_size < 8192 + 256: continue
            data = path.read_bytes(); chunk = data[8192:8192 + min(4096, len(data) - 8192)]
            digest = sha(chunk)
            if digest in seen: continue
            seen.add(digest)
            rows.append({'id': f"{group['id']}--{member}", 'path': str(path), 'family': group['kind'],
                         'offset': 8192, 'bytes': len(chunk), 'sample_sha256': digest,
                         'split': None})
    if not rows: raise SystemExit('no eligible local CCA samples')
    rows.sort(key=lambda row: row['id'])
    for index, row in enumerate(rows): row['split'] = 'development' if index % 2 == 0 else 'heldout'
    write_json(FREEZE, {'identity':'RELEASE-PREDICTIVE-1', 'status':'FROZEN_BEFORE_DATA',
        'source_hashes': {name: sha((ROOT / name).read_bytes()) for name in [
            'rust/cix-native/experiments/release-opportunities/release_trace.rs',
            'docs/research/2026-10-04-release-0.1/predictive.py']},
        'copied_source_hashes': {path.name: sha(path.read_bytes()) for path in sorted((ROOT/'benchmark-work/predictive-information/source').glob('*.rs'))},
        'trace_binary_sha256': sha((WORK/'build/release_trace').read_bytes()),
        'range': {'offset':8192, 'length':'min(4096,size-offset)', 'minimum_remaining':256},
        'split':'sorted canonical samples: even development, odd heldout; SHA-256 duplicate chunks removed before split',
        'experts':EXPERTS, 'raw_ppm_column':'ppm_o3_e1_native_subprob__p_actual', 'samples':rows})

def load(split):
    frozen = json.loads(FREEZE.read_text()); output=[]
    for sample in frozen['samples']:
        if sample['split'] != split: continue
        path = trace_path(sample)
        with path.open() as stream: rows = list(csv.DictReader(stream, delimiter='\t'))
        assert len(rows) == sample['bytes']
        values = [[float(row[name+'__p_actual']) for name in EXPERTS] for row in rows]
        actual = [int(row['actual']) for row in rows]
        raw = [float(row['ppm_o3_e1_native_subprob__p_actual']) for row in rows]
        masses = [float(row['ppm_o3_e1_native_subprob__valid_byte_mass']) for row in rows]
        assert all(0 < value <= 1 for row in values for value in row)
        output.append((sample, values, raw, masses, actual, sha(path.read_bytes())))
    return output
def bindings_ok(frozen):
    return (frozen['source_hashes']['rust/cix-native/experiments/release-opportunities/release_trace.rs'] == sha((ROOT/'rust/cix-native/experiments/release-opportunities/release_trace.rs').read_bytes())
            and frozen['source_hashes']['docs/research/2026-10-04-release-0.1/predictive.py'] == sha(Path(__file__).read_bytes())
            and frozen['trace_binary_sha256'] == sha((WORK/'build/release_trace').read_bytes())
            and all(sha((ROOT/'benchmark-work/predictive-information/source'/name).read_bytes()) == digest for name,digest in frozen['copied_source_hashes'].items()))

def static_em(rows):
    rows = np.asarray(rows)
    weights = np.ones(len(EXPERTS)) / len(EXPERTS)
    for _ in range(500):
        responsibility = rows * weights / (rows @ weights)[:,None]
        weights = np.maximum(1e-12, responsibility.mean(axis=0))
        weights /= weights.sum()
    return weights.tolist()
def online(rows, eta, share=0):
    weights=[1/len(EXPERTS)]*len(EXPERTS); result=[]
    for row in rows:
        result.append(sum(w*p for w,p in zip(weights,row)))
        un=[w*(max(p,1e-300)**eta) for w,p in zip(weights,row)]; total=sum(un); weights=[(1-share)*w/total+share/len(EXPERTS) for w in un]
    return result
def methods(rows, frozen):
    equal=[sum(row)/len(EXPERTS) for row in rows]; static=[sum(w*p for w,p in zip(frozen['static'],row)) for row in rows]
    return {'equal_static':equal, 'optimized_static':static, 'bayesian_eta1':online(rows,1), 'hedge_eta01':online(rows,.1),
            'fixed_share_1_256':online(rows,.1,1/256), 'fixed_share_001':online(rows,.1,.01),
            **{name:[row[j] for row in rows] for j,name in enumerate(EXPERTS)}}

def train():
    if TRAINED.exists(): raise SystemExit('weights already frozen')
    files=load('development'); rows=[row for _, values, _, _, _, _ in files for row in values]
    assert bindings_ok(json.loads(FREEZE.read_text()))
    manifest=json.loads((WORK/'development-manifest.json').read_text()); assert manifest['freeze_sha256']==sha(FREEZE.read_bytes())
    manifest_hashes={row['id']:row['trace_sha256'] for row in manifest['traces']}
    assert all(manifest_hashes[sample['id']]==digest for sample,_,_,_,_,digest in files)
    weights=static_em(rows); all_methods=methods(rows, {'static':weights})
    # Every adaptive method restarts for each trace file; no cross-file state.
    per_file={key:0.0 for key in all_methods}
    for _,values,_,_,_,_ in files:
        for key,predictions in methods(values, {'static':weights}).items(): per_file[key]+=loss(predictions)
    choice=min(per_file, key=per_file.get)
    write_json(TRAINED, {'freeze_sha256':sha(FREEZE.read_bytes()), 'source_sha256':sha(Path(__file__).read_bytes()),
        'static':weights, 'choice':choice, 'development_bits':per_file,
        'trace_hashes':{sample['id']:digest for sample,_,_,_,_,digest in files}, 'trace_manifest_sha256':sha((WORK/'development-manifest.json').read_bytes())})

def run(split):
    frozen=json.loads(FREEZE.read_text())
    if frozen.get('status') != 'FROZEN_BEFORE_DATA' or not bindings_ok(frozen): raise SystemExit('freeze/source binding is invalid')
    if not __import__('os').environ.get('CIX_RELEASE_LEASE'): raise SystemExit('run only through schedule.py with CIX_RELEASE_LEASE')
    if split == 'heldout':
        trained=json.loads(TRAINED.read_text())
        assert trained['freeze_sha256']==sha(FREEZE.read_bytes()) and trained['source_sha256']==sha(Path(__file__).read_bytes())
    manifest_path=WORK/(split+'-manifest.json')
    if manifest_path.exists(): raise SystemExit('immutable trace manifest already exists')
    chunks=WORK/'chunks'; traces=WORK/'traces'; chunks.mkdir(parents=True, exist_ok=True); traces.mkdir(parents=True, exist_ok=True)
    manifest=[]
    for sample in frozen['samples']:
        if sample['split'] != split: continue
        data=Path(sample['path']).read_bytes()[sample['offset']:sample['offset']+sample['bytes']]
        if sha(data) != sample['sample_sha256']: raise SystemExit('sample hash mismatch: '+sample['id'])
        chunk=chunks/(sample['id']+'.bin'); trace=traces/(sample['id']+'.tsv')
        if trace.exists(): raise SystemExit('trace already exists: '+sample['id'])
        chunk.write_bytes(data); subprocess.run([str(WORK/'build/release_trace'),str(chunk),str(trace)],check=True,timeout=300)
        manifest.append({'id':sample['id'],'chunk_sha256':sha(data),'trace_sha256':sha(trace.read_bytes())})
    write_json(manifest_path, {'freeze_sha256':sha(FREEZE.read_bytes()),'trained_sha256':sha(TRAINED.read_bytes()) if split=='heldout' else None,'traces':manifest})

def evaluate():
    if RESULTS.exists() or RESULTS_JSON.exists(): raise SystemExit('heldout results already exist; analysis is immutable')
    frozen=json.loads(TRAINED.read_text()); assert frozen['freeze_sha256']==sha(FREEZE.read_bytes())
    assert frozen['source_sha256']==sha(Path(__file__).read_bytes()), 'analysis script changed after training freeze'
    freeze_data=json.loads(FREEZE.read_text()); assert bindings_ok(freeze_data), 'source or trace binary changed after freeze'
    manifest=json.loads((WORK/'heldout-manifest.json').read_text())
    assert manifest['freeze_sha256']==sha(FREEZE.read_bytes()) and manifest['trained_sha256']==sha(TRAINED.read_bytes())
    files=load('heldout'); rows=[row for _, values, _, _, _, _ in files for row in values]; raw=[p for _,_,raw,_,_,_ in files for p in raw]; masses=[p for _,_,_,masses,_,_ in files for p in masses]
    assert {s['id']:d for s,_,_,_,_,d in files} == {s['id']:s['trace_sha256'] for s in manifest['traces']}
    controls={key:[p for _,values,_,_,_,_ in files for p in methods(values,frozen)[key]] for key in methods(files[0][1],frozen)}
    individual={name:loss([row[index] for row in rows]) for index,name in enumerate(EXPERTS)}
    oracle=loss([max(row) for row in rows]); selected=controls[frozen['choice']]
    strongest=min(individual, key=individual.get)
    v1_gain=(individual['fixedmix_v1']-loss(selected))/len(rows)
    causal_gain=(individual[strongest]-loss(selected))/len(rows)
    gate=causal_gain >= .05 and loss(selected) < .99*individual[strongest]
    baseline = [row[0] for row in rows]
    noisy = {}
    offset = 0
    for sample, values, _, _, actual, _ in files:
        for epsilon in [.1, .2]:
            for seed in range(5):
                key=f'dirichlet_eps{epsilon}_seed{seed}'
                noisy.setdefault(key, [])
                noisy[key].extend((1-epsilon)*row[0] + epsilon*dirichlet_actual(sample['id'], position, byte, seed)
                                  for position, (row, byte) in enumerate(zip(values, actual)))
        offset += len(values)
    uniform = [(1-.1)*p + .1/256 for p in baseline]
    alignment_broken = list(reversed(baseline))
    def null_stats(predictions):
        matrix=np.asarray(predictions).T
        singles=-np.log2(matrix).sum(axis=0)
        hindsight=float(-np.log2(matrix.max(axis=1)).sum())
        equal=float(-np.log2(matrix.mean(axis=1)).sum())
        return {'best_single_bits':float(singles.min()), 'noncausal_oracle_bits':hindsight, 'oracle_gap_bits':float(singles.min())-hindsight, 'equal_mixture_gain_bits':float(singles.min())-equal}
    nulls={'duplicate':null_stats([baseline,baseline]), 'smoothing':null_stats([baseline,uniform]),
           'independent_noise':null_stats([baseline,*noisy.values()]),
           'INVALID_alignment_broken_losses':null_stats([baseline,alignment_broken])}
    lines=['# RELEASE-PREDICTIVE-1 results','', 'Ideal predictive bits only; no physical archive claim.','',
           f"Held-out bytes: {len(rows)}", f"Frozen causal choice: {frozen['choice']}", f"HINDSIGHT ORACLE — NON-CAUSAL DIAGNOSTIC ONLY: {oracle:.6f} bits", '', '| item | ideal bits |', '| --- | ---: |']
    lines += [f'| {name} | {bits:.6f} |' for name,bits in individual.items()] + [f'| {name} | {loss(value):.6f} |' for name,value in controls.items()]
    lines += ['', f'Raw native PPM path bits: {loss(raw):.6f}; paid native valid-mass bits: {loss(masses):.6f}.',
              f'Best held-out single native expert: {strongest} ({individual[strongest]:.6f} bits).',
              f'Causal gain over best held-out single: {causal_gain:.6f} b/B; marginal over existing v1: {v1_gain:.6f} b/B.',
              f'v3-N1 marginal over fixedmix-v1: {(individual["fixedmix_v1"]-individual["fixedmix_v3_n1"])/len(rows):.6f} b/B.',
              f'v3-N2 marginal over fixedmix-v1: {(individual["fixedmix_v1"]-individual["fixedmix_v3_n2"])/len(rows):.6f} b/B.',
              f'Gate (>0.05 b/B and >1% strongest-pool improvement): {"PASS" if gate else "FAIL"}.',
              f'Duplicate null bits: {loss(baseline):.6f}.',
              'Dirichlet noisy-null bits: ' + ', '.join(f'{key}={loss(value):.6f}' for key,value in sorted(noisy.items())) + '.',
              f'Redundant uniform-smoothing null bits: {loss(uniform):.6f}.',
              f'INVALID alignment-broken diagnostic bits: {loss(alignment_broken):.6f}; it is not a causal forecast.',
              'PPM rows are separate potential-new-model diagnostics; neither native raw PPM nor normalized PPM participates in the oracle, static/online pool, or gate.',
              'This is a narrow omitted-signal screen; the full complementarity/calibration analysis remains CPI1.',
              'These fixed ranges were not used by CPI1, but earlier project research may have exposed them; this is not a pristine corpus-level holdout.',
              'Null oracle controls: '+json.dumps(nulls)]
    RESULTS.write_text('\n'.join(lines)+'\n')
    wins=[]
    for sample, values, _, _, _, digest in files:
        selected_file=loss(methods(values,frozen)[frozen['choice']]); singles=[loss([row[index] for row in values]) for index in range(len(EXPERTS))]
        wins.append({'id':sample['id'], 'trace_sha256':digest, 'selected_bits':selected_file, 'best_single_bits':min(singles), 'selected_wins':selected_file < min(singles)})
    write_json(RESULTS_JSON, {'identity':'RELEASE-PREDICTIVE-1', 'ideal_predictive_only':True, 'experts':EXPERTS,
        'individual_bits':individual, 'method_bits':{key:loss(value) for key,value in controls.items()}, 'oracle_noncausal_bits':oracle,
        'oracle_gap_bits':individual[strongest]-oracle, 'causal_gain_bits':individual[strongest]-loss(selected),
        'bytes':len(rows), 'selected_method':frozen['choice'], 'nulls':nulls,
        'raw_ppm_path_bits':loss(raw), 'paid_ppm_valid_mass_bits':loss(masses), 'normalized_ppm_new_model_diagnostic_bits':loss(raw)-loss(masses),
        'gate':gate, 'file_wins':wins})

parser=argparse.ArgumentParser(); parser.add_argument('phase', choices=['freeze','development','heldout','train','evaluate']); args=parser.parse_args()
{'freeze':freeze,'development':lambda:run('development'),'heldout':lambda:run('heldout'),'train':train,'evaluate':evaluate}[args.phase]()
