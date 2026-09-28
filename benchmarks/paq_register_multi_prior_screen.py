"""Screen causal occupancy/composition and recency experts before native work.

This adds predictive information derived exclusively from past decoded register
fields. No hard exclusion or enumerative-coder superiority is asserted. Physical
framing and independent decoder qualification remain mandatory after a win.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import paq_register_screen as base, paq_register_log_screen as log


def analyze(folder):
    folder=Path(folder); proof=json.loads((folder/'complete.json').read_text())
    source=(folder/'source.bin').read_bytes(); raw=(folder/'predictions.u32').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']: raise ValueError('unqualified trace')
    if sha(source)!=proof['input_sha256'] or sha(raw)!=proof['trace_sha256']: raise ValueError('changed trace')
    events=array.array('I'); events.frombytes(raw)
    if sys.byteorder!='little': events.byteswap()
    outcome=base.mapping.outcome_bytes(events)
    settings={'shared_recency':(0,), 'role_recency':(1,), 'composition':(2,), 'occupancy':(3,),
              'both_recencies':(0,1), 'recency_composition':(0,2), 'recency_occupancy':(0,3), 'all':(0,1,2,3)}
    totals={name:0. for name in settings}; native_loss=0.; fields=regions=0
    for off,size in base.fields.regions.objects.objects(source):
        obj=source[off:off+size]; sections=base.fields.regions.objects.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')): continue
        start,n=sections[b'.text']; si,ni=sections[b'.init']; sf,nf=sections[b'.fini']
        if si!=start+n or sf!=si+ni: continue
        code=base.mapping.shuffled_code(obj[start:start+n+ni+nf]); at=outcome.find(code)
        if at<0 or outcome.find(code,at+1)>=0: raise ValueError('nonunique code mapping')
        priors=[base.Prior(i) for i in range(4)]; models={name:{} for name in settings}; regions+=1
        for wi,(word,) in enumerate(struct.iter_unpack('>I',code)):
            opcode=word>>26
            for shift,kind,field,namespace in base.fields.register_fields(word):
                value=(word>>shift)&31; context=(namespace,kind+'.'+field,opcode)
                keys=[prior.key(namespace,kind,field,opcode) for prior in priors]; cdfs=[]
                for prior,key in zip(priors,keys):
                    cdf=[0]
                    for weight in prior.weights(key): cdf.append(cdf[-1]+weight)
                    cdfs.append(cdf)
                first=(at+wi*4)*8+27-shift; prefix=0; fields+=1
                for bit,record in zip(range(4,-1,-1),events[first:first+5]):
                    p=record&0x7fffffff; y=record>>31
                    if y!=((value>>bit)&1): raise ValueError('field outcome mismatch')
                    native_loss-=math.log2((p if y else (1<<31)-p)/(1<<31))
                    lo=prefix<<(bit+1); mid=lo+(1<<bit); hi=lo+(1<<(bit+1)); predictions=[]
                    for cdf in cdfs:
                        q=((cdf[hi]-cdf[mid])<<31)//(cdf[hi]-cdf[lo])
                        predictions.append([((d-1)*p+q+d//2)//d for d in (128,32,8,2)])
                    for name,families in settings.items():
                        experts=[p]+[x for family in families for x in predictions[family]]
                        if not (1<<26)<=p<=31*(1<<26): experts=[p]*len(experts)
                        if context not in models[name]: models[name][context]=log.LogPosterior(experts=len(experts))
                        model=models[name][context]; prediction=model.mix(experts)
                        totals[name]-=math.log2((prediction if y else (1<<31)-prediction)/(1<<31)); model.observe(experts,y)
                    prefix=prefix*2+y
                for prior,key in zip(priors,keys): prior.observe(key,value)
    rows=[dict(priors=name,experts=1+4*len(settings[name]),mixed_predictive_bits=loss,
        saved_predictive_bytes=(native_loss-loss)/8) for name,loss in totals.items()]
    rows.sort(key=lambda r:r['saved_predictive_bytes'],reverse=True)
    # Recover the independently qualified predictive control before using new arms.
    control=next(r for r in rows if r['priors']=='shared_recency')
    expected=json.loads(Path('docs/research/2026-09-28-register-log-screen.json').read_text())
    old=next(r for r in expected['rows'] if r['context']==3 and r['native_prior_bias']==1)
    if abs(control['saved_predictive_bytes']-old['saved_predictive_bytes'])>1e-6: raise ValueError('qualified control changed')
    for row in rows: row['saved_beyond_qualified_predictor_bytes']=row['saved_predictive_bytes']-control['saved_predictive_bytes']
    return dict(complete=True,diagnostic_only=True,physical_codec=False,code_regions=regions,register_fields=fields,
        native_register_predictive_bits=native_loss,rows=rows,qualified_trace=proof,
        source_hashes={str(p):sha(Path(p).read_bytes()) for p in [__file__,base.__file__,base.fields.__file__,base.mapping.__file__,log.__file__]},
        control_matches_qualified_predictive_screen=True,scope=__doc__,
        limitation='Same exploratory object; no held-out, physical compression, whole-member or leaderboard claim. Python floating log screen requires deterministic native refinement.')


if __name__=='__main__':
    result=analyze(sys.argv[1]); Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['rows'],indent=2))
