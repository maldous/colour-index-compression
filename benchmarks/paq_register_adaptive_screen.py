"""Screen fixed-point causal expert mixtures using unchanged PAQ predictions.

Additional information comes only from previously decoded register fields and
past expert errors. This is a prediction diagnostic, not a compressed artifact.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import paq_register_screen as base


class Posterior:
    def __init__(self,experts=5,native_bias=1):
        self.weights=[(1<<24)*native_bias]+[1<<24]*(experts-1)
    def mix(self,predictions):
        total=sum(self.weights)
        return max(1,min(0x7fffffff,(sum(w*p for w,p in zip(self.weights,predictions))+total//2)//total))
    def observe(self,predictions,y):
        if len(set(predictions))==1:return
        products=[w*(p if y else (1<<31)-p) for w,p in zip(self.weights,predictions)]
        total=sum(products)
        self.weights=[max(1,(v<<30)//total) for v in products]


def key(kind,namespace,field,opcode):
    if kind==0:return ()
    if kind==1:return (namespace,)
    if kind==2:return (namespace,field)
    return (namespace,field,opcode)


def analyze(folder):
    folder=Path(folder);proof=json.loads((folder/'complete.json').read_text())
    source=(folder/'source.bin').read_bytes();raw=(folder/'predictions.u32').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']:raise ValueError('unqualified trace')
    if sha(source)!=proof['input_sha256'] or sha(raw)!=proof['trace_sha256']:raise ValueError('changed source/trace')
    events=array.array('I');events.frombytes(raw)
    if sys.byteorder!='little':events.byteswap()
    outcome=base.mapping.outcome_bytes(events);totals={};native_loss=0.;fields=0;regions=0
    settings=[(kind,bias) for kind in range(4) for bias in (1,8)]
    for off,size in base.fields.regions.objects.objects(source):
        obj=source[off:off+size];sections=base.fields.regions.objects.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')):continue
        start,n=sections[b'.text'];si,ni=sections[b'.init'];sf,nf=sections[b'.fini']
        if si!=start+n or sf!=si+ni:continue
        code=base.mapping.shuffled_code(obj[start:start+n+ni+nf]);at=outcome.find(code)
        if at<0 or outcome.find(code,at+1)>=0:raise ValueError('nonunique code region')
        prior=base.Prior(0);models={setting:{} for setting in settings};regions+=1
        for wi,(word,) in enumerate(struct.iter_unpack('>I',code)):
            opcode=word>>26
            for shift,kind,field,namespace in base.fields.register_fields(word):
                value=(word>>shift)&31;name=kind+'.'+field;pk=(namespace,);weights=prior.weights(pk)
                cdf=[0]
                for w in weights:cdf.append(cdf[-1]+w)
                first=(at+wi*4)*8+27-shift;prefix=0;fields+=1
                for bit,record in zip(range(4,-1,-1),events[first:first+5]):
                    p=record&0x7fffffff;y=record>>31
                    if y!=((value>>bit)&1):raise ValueError('field outcome mismatch')
                    native_loss-=math.log2((p if y else (1<<31)-p)/(1<<31))
                    lo=prefix<<(bit+1);mid=lo+(1<<bit);hi=lo+(1<<(bit+1))
                    q=((cdf[hi]-cdf[mid])<<31)//(cdf[hi]-cdf[lo])
                    experts=[p]+[max(1,min(0x7fffffff,((d-1)*p+q+d//2)//d)) for d in (128,32,8,2)]
                    if not (1<<26)<=p<=31*(1<<26):experts=[p]*5
                    for setting in settings:
                        mode,bias=setting;k=key(mode,namespace,name,opcode)
                        if k not in models[setting]:models[setting][k]=Posterior(native_bias=bias)
                        model=models[setting][k];prediction=model.mix(experts)
                        totals[setting]=totals.get(setting,0.)-math.log2((prediction if y else (1<<31)-prediction)/(1<<31))
                        model.observe(experts,y)
                    prefix=prefix*2+y
                prior.observe(pk,value)
    rows=[dict(context=mode,native_prior_bias=bias,mixed_predictive_bits=totals[(mode,bias)],
        saved_predictive_bytes=(native_loss-totals[(mode,bias)])/8) for mode,bias in settings]
    rows.sort(key=lambda r:r['saved_predictive_bytes'],reverse=True)
    return dict(complete=True,diagnostic_only=True,physical_codec=False,code_regions=regions,register_fields=fields,
        native_register_predictive_bits=native_loss,contexts=['global','namespace','field role','opcode and field role'],
        rows=rows,qualified_trace=proof,source_hashes={str(Path(p)):sha(Path(p).read_bytes()) for p in [__file__,base.__file__,base.fields.__file__,base.mapping.__file__]},
        note=__doc__,limitation='Exploratory screen on the same object used for fixed-prior selection. Native integration, framing and independent restoration remain required.')


if __name__=='__main__':
    report=analyze(sys.argv[1]);Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['rows'],indent=2))
