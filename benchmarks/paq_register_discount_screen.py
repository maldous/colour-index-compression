"""Test whether causal forgetting improves a register expert mixture.

Persistent log evidence is correct for a fixed expert choice. Real code may
change regime between functions. Explicit discounting is a different model,
not a numerical repair or a claim of a static Bayesian regret guarantee.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import paq_register_screen as base, paq_register_log_screen as log


class DiscountPosterior(log.LogPosterior):
    def __init__(self,shift):
        super().__init__(); self.shift=shift
    def observe(self,predictions,y):
        if len(set(predictions))==1: return
        super().observe(predictions,y)
        if self.shift:
            denominator=1<<self.shift
            self.scores=[-(((-s)*(denominator-1)+denominator//2)//denominator) for s in self.scores]


def analyze(folder):
    folder=Path(folder); proof=json.loads((folder/'complete.json').read_text())
    source=(folder/'source.bin').read_bytes(); raw=(folder/'predictions.u32').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']: raise ValueError('unqualified trace')
    if sha(source)!=proof['input_sha256'] or sha(raw)!=proof['trace_sha256']: raise ValueError('changed trace')
    events=array.array('I'); events.frombytes(raw)
    if sys.byteorder!='little': events.byteswap()
    outcome=base.mapping.outcome_bytes(events); settings=(0,5,7,9,11)
    totals={s:0. for s in settings}; native_loss=0.; fields=regions=0
    for off,size in base.fields.regions.objects.objects(source):
        obj=source[off:off+size]; sections=base.fields.regions.objects.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')): continue
        start,n=sections[b'.text']; si,ni=sections[b'.init']; sf,nf=sections[b'.fini']
        if si!=start+n or sf!=si+ni: continue
        code=base.mapping.shuffled_code(obj[start:start+n+ni+nf]); at=outcome.find(code)
        if at<0 or outcome.find(code,at+1)>=0: raise ValueError('nonunique code mapping')
        prior=base.Prior(0); models={s:{} for s in settings}; regions+=1
        for wi,(word,) in enumerate(struct.iter_unpack('>I',code)):
            opcode=word>>26
            for shift,kind,field,namespace in base.fields.register_fields(word):
                value=(word>>shift)&31; context=(namespace,kind+'.'+field,opcode); key=(namespace,); cdf=[0]
                for weight in prior.weights(key): cdf.append(cdf[-1]+weight)
                first=(at+wi*4)*8+27-shift; prefix=0; fields+=1
                for bit,record in zip(range(4,-1,-1),events[first:first+5]):
                    p=record&0x7fffffff; y=record>>31
                    if y!=((value>>bit)&1): raise ValueError('field outcome mismatch')
                    native_loss-=math.log2((p if y else (1<<31)-p)/(1<<31))
                    lo=prefix<<(bit+1); mid=lo+(1<<bit); hi=lo+(1<<(bit+1))
                    q=((cdf[hi]-cdf[mid])<<31)//(cdf[hi]-cdf[lo])
                    experts=[p]+[((d-1)*p+q+d//2)//d for d in (128,32,8,2)]
                    if not (1<<26)<=p<=31*(1<<26): experts=[p]*5
                    for setting in settings:
                        if context not in models[setting]: models[setting][context]=DiscountPosterior(setting)
                        model=models[setting][context]; prediction=model.mix(experts)
                        totals[setting]-=math.log2((prediction if y else (1<<31)-prediction)/(1<<31)); model.observe(experts,y)
                    prefix=prefix*2+y
                prior.observe(key,value)
    rows=[dict(discount_shift=s,retention='1' if s==0 else f'{(1<<s)-1}/{1<<s}',mixed_predictive_bits=loss,
        saved_predictive_bytes=(native_loss-loss)/8,saved_beyond_persistent_bytes=(totals[0]-loss)/8) for s,loss in totals.items()]
    rows.sort(key=lambda r:r['saved_predictive_bytes'],reverse=True)
    expected=json.loads(Path('docs/research/2026-09-28-register-log-screen.json').read_text())
    old=next(r for r in expected['rows'] if r['context']==3 and r['native_prior_bias']==1)
    if abs((native_loss-totals[0])/8-old['saved_predictive_bytes'])>1e-6: raise ValueError('qualified control changed')
    return dict(complete=True,diagnostic_only=True,physical_codec=False,code_regions=regions,register_fields=fields,
        native_register_predictive_bits=native_loss,rows=rows,qualified_trace=proof,
        source_hashes={str(p):sha(Path(p).read_bytes()) for p in [__file__,base.__file__,base.fields.__file__,base.mapping.__file__,log.__file__]},
        control_matches_qualified_predictive_screen=True,scope=__doc__,
        limitation='Same exploratory object. Prediction screen only; no physical bytes, full-file gain, hard state-space elimination or identical-information entropy-coder superiority.')


if __name__=='__main__':
    result=analyze(sys.argv[1]); Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['rows'],indent=2))
