"""Cheap visible-state affine-recurrence screen; never a compressed-size result."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import os
from benchmarks import mysql_record_constraints as records


def screen(values):
    differences=[b-a for a,b in zip(values,values[1:])];constraint=0
    for a,b,c in zip(differences,differences[1:],differences[2:]):
        constraint=math.gcd(constraint,abs(a*c-b*b))
    models=set();low=min(values);high=max(values)
    for offset in sorted({0,low}):
        x=[v-offset for v in values]
        for modulus in sorted({high-offset+1,len(set(values)),2**31-1,2**31,2**32}):
            if modulus<2:continue
            for a,b,c in zip(x[:64],x[1:65],x[2:66]):
                if math.gcd(b-a,modulus)!=1:continue
                slope=((c-b)*pow(b-a,-1,modulus))%modulus
                intercept=(b-slope*a)%modulus
                models.add((offset,modulus,slope,intercept))
    candidates=[]
    # Prefix fitting is only screening. Count full support for every proposed rule.
    for offset,modulus,slope,intercept in models:
        hits=sum((slope*(a-offset)+intercept)%modulus+offset==b
                 for a,b in zip(values,values[1:]))
        candidates.append(dict(offset=offset,modulus=modulus,slope=slope,intercept=intercept,matches=hits))
    candidates.sort(key=lambda r:(-r['matches'],r['offset'],r['modulus'],r['slope'],r['intercept']))
    return dict(values=len(values),alphabet=len(set(values)),minimum=low,maximum=high,
                determinant_gcd=constraint,models_tested=len(models),best=candidates[:3],
                comparison_transitions=len(values)-1,exact_model=bool(candidates and candidates[0]['matches']==len(values)-1))


def main():
    os.sched_setaffinity(0,{24})
    path=Path('benchmark-work/silesia/osdb');data=path.read_bytes();_,columns=records.split(data)
    rows=[dict(column=i,**screen([int.from_bytes(v,'little') for v in columns[i]])) for i in (0,1,2,5)]
    sources=[Path(__file__),Path(records.__file__)]
    report=dict(complete=True,diagnostic_only=True,scored=False,rows=rows,
        input_sha256=hashlib.sha256(data).hexdigest(),source_hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        conclusion='No tested direct visible-state recurrence reconstructs these columns. Rules inferred from short prefixes mostly match only fitting samples or the constant-frequency baseline. Hidden-state generators, shuffled sequences and other mathematical models are not disproven. No compressed size or rank is inferred.')
    out=Path('docs/research/2026-09-28-generative-rule-screen.json');out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps([dict(column=r['column'],best=r['best'][:1],transitions=r['comparison_transitions'],exact=r['exact_model']) for r in rows],indent=2))


if __name__=='__main__':main()
