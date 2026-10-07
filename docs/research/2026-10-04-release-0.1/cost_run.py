"""Physical native substream costs; no complete-archive comparison."""
import csv, hashlib, json, math, os, subprocess
from pathlib import Path

A=Path(__file__).resolve().parent
R=A.parents[2]
W=R/'benchmark-work/release-opportunities'
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
freeze=json.loads((A/'prediction-freeze.json').read_text())
out=W/'costs'
out.mkdir(exist_ok=False)
totals={}
receipts=[]
for sample in freeze['samples']:
    if sample['split']!='heldout': continue
    chunk=W/'chunks'/(sample['id']+'.bin')
    assert hashlib.sha256(chunk.read_bytes()).hexdigest()==sample['sample_sha256']
    target=out/(sample['id']+'.json')
    subprocess.run([str(W/'build/cost_trace'),str(chunk),str(target)],check=True)
    rows=json.loads(target.read_text())['rows']
    trace=list(csv.DictReader((W/'traces'/(sample['id']+'.tsv')).open(),delimiter='\t'))
    for row in rows:
        route=row['route']; total=totals.setdefault(route,{'total_bytes':0,'metadata_bytes':0,'arithmetic_bytes':0,'ideal_bits':0.0,'ideal_available':route.startswith(('fixedmix','ppm'))})
        total['total_bytes']+=row['payload_total_bytes'];total['metadata_bytes']+=row['metadata_header_bytes'];total['arithmetic_bytes']+=row['arithmetic_payload_bytes']
        if total['ideal_available']:
            column=route.replace('_eta6','')+'__p_actual' if route.startswith('fixedmix') else 'ppm_o3_e1_native_subprob__p_actual'
            total['ideal_bits']+=sum(-math.log2(float(x[column])) for x in trace)
    receipts.append({'sample':sample['id'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
for total in totals.values():
    total['finite_precision_termination_padding_bits']=total['arithmetic_bytes']*8-total['ideal_bits'] if total['ideal_available'] else None
result={'scope':'existing native substreams only, not complete archives','totals':totals,'receipts':receipts,
        'cost_binary_sha256':hashlib.sha256((W/'build/cost_trace').read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256((R/'rust/cix-native/experiments/release-opportunities/cost_trace.rs').read_bytes()).hexdigest()}
(A/'cost-results.json').write_text(json.dumps(result,indent=2)+'\n')
