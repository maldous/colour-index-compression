"""Cheap causal-prior screen against unchanged, qualified PAQ predictions.

Mixtures are evaluated sequentially on one previously qualified real object.
Only past completed register fields update a prior. Prediction loss excludes
framing and is not a physical codec result. Any useful candidate still needs
native integration and independent byte restoration on further inputs.
"""
import array
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import ecoff_register_ranks as fields, ecoff_call_trace_analysis as mapping


class Prior:
    def __init__(self,mode):self.mode=mode;self.state={}
    def key(self,namespace,kind,field,opcode):
        return (namespace,) if self.mode==0 else (namespace,kind,field) if self.mode==1 else (namespace,kind,field,opcode)
    def weights(self,key):
        if self.mode<2:
            out=[1]*32
            for rank,value in enumerate(self.state.get(key,[])):out[value]=max(1,256>>rank)
            return out
        counts=self.state.get(key,[0]*32)
        return [n+1 for n in counts] if self.mode==2 else [32 if n else 1 for n in counts]
    def observe(self,key,value):
        if self.mode<2:
            row=self.state.setdefault(key,[])
            if value in row:row.remove(value)
            row.insert(0,value)
        else:
            row=self.state.setdefault(key,[0]*32);row[value]+=1
            if self.mode==2 and sum(row)>512:row[:]=[(n+1)//2 for n in row]


def analyze(folder):
    folder=Path(folder);proof=json.loads((folder/'complete.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']:raise ValueError('unqualified register trace')
    data=(folder/'source.bin').read_bytes();raw=(folder/'predictions.u32').read_bytes()
    if sha(data)!=proof['input_sha256'] or sha(raw)!=proof['trace_sha256']:raise ValueError('register trace identity mismatch')
    events=array.array('I');events.frombytes(raw)
    if sys.byteorder!='little':events.byteswap()
    outcome=mapping.outcome_bytes(events);losses=defaultdict(float);baseline=defaultdict(float);counts=defaultdict(int)
    denominators=(128,32,8,2);total_regions=0
    for off,size in fields.regions.objects.objects(data):
        obj=data[off:off+size];sections=fields.regions.objects.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')):continue
        start,n=sections[b'.text'];si,ni=sections[b'.init'];sf,nf=sections[b'.fini']
        if si!=start+n or sf!=si+ni:continue
        n+=ni+nf;code=mapping.shuffled_code(obj[start:start+n]);at=outcome.find(code)
        if at<0 or outcome.find(code,at+1)>=0:raise ValueError('nonunique register trace region')
        total_regions+=1;priors=[Prior(i) for i in range(4)]
        for i,(word,) in enumerate(struct.iter_unpack('>I',code)):
            opcode=word>>26
            for shift,kind,field,namespace in fields.register_fields(word):
                value=(word>>shift)&31;name=kind+'.'+field;counts[name]+=1
                keys=[p.key(namespace,kind,field,opcode) for p in priors];cdfs=[]
                for prior,key in zip(priors,keys):
                    cdf=[0]
                    for mass in prior.weights(key):cdf.append(cdf[-1]+mass)
                    cdfs.append(cdf)
                first=(at+i*4)*8+(27-shift);prefix=0
                for bit,record in zip(range(4,-1,-1),events[first:first+5]):
                    p=(record&0x7fffffff)/(1<<31);y=record>>31
                    if y!=((value>>bit)&1):raise ValueError('register causal field mismatch')
                    base=-math.log2(p if y else 1-p);baseline[name]+=base
                    low=prefix<<(bit+1);middle=low+(1<<bit);high=low+(1<<(bit+1))
                    for mode,cdf in enumerate(cdfs):
                        q=(cdf[high]-cdf[middle])/(cdf[high]-cdf[low])
                        for denominator in denominators:
                            prediction=p+(q-p)/denominator;cost=-math.log2(prediction if y else 1-prediction)
                            losses[(mode,denominator,0,name)]+=cost
                            losses[(mode,denominator,1,name)]+=cost if 1/32<=p<=31/32 else base
                    prefix=prefix*2+y
                for prior,key in zip(priors,keys):prior.observe(key,value)
    rows=[]
    for mode in range(4):
        for denominator in denominators:
            for gate in range(2):
                detail={name:dict(fields=counts[name],paq_bits=base,mixed_bits=losses[(mode,denominator,gate,name)],saved_predictive_bits=base-losses[(mode,denominator,gate,name)]) for name,base in baseline.items()}
                saved=sum(d['saved_predictive_bits'] for d in detail.values())
                rows.append(dict(mode=mode,prior_weight=f'1/{denominator}',ambiguous_only=bool(gate),saved_predictive_bits=saved,saved_predictive_bytes=saved/8,fields=detail))
    rows.sort(key=lambda r:r['saved_predictive_bits'],reverse=True)
    return dict(complete=True,diagnostic_only=True,physical_codec=False,qualified_trace=proof,code_regions=total_regions,
        prior_modes=['shared recency','field-role recency','opcode/role counts','opcode/role occupancy'],rows=rows,
        source_hashes={str(Path(p)):sha(Path(p).read_bytes()) for p in [__file__,fields.__file__,fields.layout.__file__,fields.regions.__file__,mapping.__file__]},
        note=__doc__)


if __name__=='__main__':
    result=analyze(sys.argv[1]);Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in row.items() if k!='fields'} for row in result['rows'][:8]],indent=2))
