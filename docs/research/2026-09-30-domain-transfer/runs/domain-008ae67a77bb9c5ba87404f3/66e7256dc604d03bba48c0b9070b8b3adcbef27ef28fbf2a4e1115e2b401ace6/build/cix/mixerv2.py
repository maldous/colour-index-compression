"""Experimental fixed-share sparse context mixer for universal CIX.

Experts:
- contiguous byte contexts
- sparse byte-offset contexts
- generic lag byte predictors
- last-context match predictor

Weights are maintained independently per bit position and include a small fixed-share
term so a predictor that was poor in one regime can recover when the stream changes.
Everything is causal and format agnostic.
"""
from __future__ import annotations
import math
from .multinomial import _ArithmeticEncoder,_ArithmeticDecoder,vencode,vdecode

VERSION=1
SCALE=1<<15
COUNT_LIMIT=4096
WEIGHT_INIT=1<<14
SHARE_SHIFT=7

CONTEXT_PATTERNS=(
    (),
    (1,),
    (1,2),
    (1,2,3,4),
    (1,3),
    (1,4),
    (1,2,4),
    (1,4,8),
    (2,4,8),
)
LAGS=(1,2,4,8,16,32)
MATCH_ORDER=4

def _context(history:bytearray,pattern:tuple[int,...]):
    if not pattern:return ()
    if len(history)<max(pattern):return None
    return tuple(history[-offset] for offset in pattern)

def _prob(counts):
    if counts is None:return SCALE//2
    z,o=counts;total=z+o+2
    return min(SCALE-1,max(1,((o+1)*SCALE)//total))

def _update_count(counts,bit):
    counts[bit]+=1
    if counts[0]+counts[1]>COUNT_LIMIT:
        counts[0]//=2;counts[1]//=2

def _pred_prob(predicted:int|None,bit_pos:int,reliability):
    if predicted is None:return SCALE//2
    correct,wrong=reliability[bit_pos]
    total=correct+wrong+2
    confidence=((correct+1)*SCALE)//total
    confidence=min(SCALE-1,max(SCALE//2,confidence))
    bit=(predicted>>(7-bit_pos))&1
    return confidence if bit else SCALE-confidence

def _mix(probs,weights):
    tw=sum(weights)
    if not tw:return SCALE//2
    return min(SCALE-1,max(1,sum(p*w for p,w in zip(probs,weights))//tw))

def _update_weights(weights,probs,bit):
    for i,p in enumerate(probs):
        like=p if bit else SCALE-p
        weights[i]=max(1,(weights[i]*like)//(SCALE//2))
    total=sum(weights);avg=max(1,total//len(weights))
    for i,w in enumerate(weights):
        weights[i]=max(1,w-(w>>SHARE_SHIFT)+(avg>>SHARE_SHIFT))
    mx=max(weights)
    if mx>1<<25:
        for i,w in enumerate(weights):weights[i]=max(1,w>>8)

class State:
    def __init__(self,prefix=b""):
        self.history=bytearray(prefix)
        self.tables=[{} for _ in CONTEXT_PATTERNS]
        expert_count=len(CONTEXT_PATTERNS)+len(LAGS)+1
        self.weights=[[WEIGHT_INIT]*expert_count for _ in range(8)]
        self.lag_rel=[[[1,1] for _ in range(8)] for _ in LAGS]
        self.match_rel=[[1,1] for _ in range(8)]
        self.match_table={}

    def probabilities(self,bit_pos,prefix_bits):
        probs=[];keys=[]
        for i,pattern in enumerate(CONTEXT_PATTERNS):
            ctx=_context(self.history,pattern)
            key=(ctx,bit_pos,prefix_bits) if ctx is not None else None
            keys.append(key)
            probs.append(_prob(self.tables[i].get(key) if key is not None else None))

        for li,lag in enumerate(LAGS):
            pred=self.history[-lag] if len(self.history)>=lag else None
            probs.append(_pred_prob(pred,bit_pos,self.lag_rel[li]))

        match=None
        if len(self.history)>=MATCH_ORDER:
            match=self.match_table.get(bytes(self.history[-MATCH_ORDER:]))
        probs.append(_pred_prob(match,bit_pos,self.match_rel))
        return probs,keys

    def update_bit(self,bit_pos,prefix_bits,bit,probs,keys):
        _update_weights(self.weights[bit_pos],probs,bit)
        for i,key in enumerate(keys):
            if key is None:continue
            counts=self.tables[i].get(key)
            if counts is None:
                counts=[0,0];self.tables[i][key]=counts
            _update_count(counts,bit)

        base=len(CONTEXT_PATTERNS)
        for li,lag in enumerate(LAGS):
            if len(self.history)>=lag:
                pred=(self.history[-lag]>>(7-bit_pos))&1
                rel=self.lag_rel[li][bit_pos]
                rel[0 if pred==bit else 1]+=1
                if sum(rel)>COUNT_LIMIT:
                    rel[0]//=2;rel[1]//=2

        if len(self.history)>=MATCH_ORDER:
            predicted=self.match_table.get(bytes(self.history[-MATCH_ORDER:]))
            if predicted is not None:
                pred=(predicted>>(7-bit_pos))&1
                rel=self.match_rel[bit_pos]
                rel[0 if pred==bit else 1]+=1
                if sum(rel)>COUNT_LIMIT:
                    rel[0]//=2;rel[1]//=2

    def finish_byte(self,byte):
        if len(self.history)>=MATCH_ORDER:
            self.match_table[bytes(self.history[-MATCH_ORDER:])]=byte
        self.history.append(byte)
        if len(self.history)>65536:del self.history[:-32768]

def estimate_bits(data,prefix_history=b"",sample_limit=4096):
    sample=data[:sample_limit]
    if not sample:return 0.0
    s=State(prefix_history);bits=0.0
    for byte in sample:
        pref=0
        for bp in range(8):
            bit=(byte>>(7-bp))&1
            probs,keys=s.probabilities(bp,pref)
            mixed=_mix(probs,s.weights[bp])
            mass=mixed if bit else SCALE-mixed
            bits+=math.log2(SCALE)-math.log2(mass)
            s.update_bit(bp,pref,bit,probs,keys)
            pref=(pref<<1)|bit
        s.finish_byte(byte)
    return bits*len(data)/len(sample)

def encode(data,prefix_history=b""):
    s=State(prefix_history);enc=_ArithmeticEncoder()
    for byte in data:
        pref=0
        for bp in range(8):
            bit=(byte>>(7-bp))&1
            probs,keys=s.probabilities(bp,pref)
            mixed=_mix(probs,s.weights[bp]);zero=SCALE-mixed
            if bit:enc.encode(zero,SCALE,SCALE)
            else:enc.encode(0,zero,SCALE)
            s.update_bit(bp,pref,bit,probs,keys)
            pref=(pref<<1)|bit
        s.finish_byte(byte)
    payload,bits=enc.finish()
    return bytes((VERSION,))+vencode(bits)+payload

def decode(blob,source_length,prefix_history=b""):
    if not blob or blob[0]!=VERSION:raise ValueError("bad mix2 version")
    bits,pos=vdecode(blob,1)
    if pos+(bits+7)//8!=len(blob):raise ValueError("mix2 payload length")
    dec=_ArithmeticDecoder(blob[pos:],bits);s=State(prefix_history);out=bytearray()
    for _ in range(source_length):
        byte=0;pref=0
        for bp in range(8):
            probs,keys=s.probabilities(bp,pref)
            mixed=_mix(probs,s.weights[bp]);zero=SCALE-mixed
            target=dec.target(SCALE)
            if target<zero:bit=0;dec.update(0,zero,SCALE)
            else:bit=1;dec.update(zero,SCALE,SCALE)
            s.update_bit(bp,pref,bit,probs,keys)
            byte=(byte<<1)|bit;pref=(pref<<1)|bit
        out.append(byte);s.finish_byte(byte)
    return bytes(out)
