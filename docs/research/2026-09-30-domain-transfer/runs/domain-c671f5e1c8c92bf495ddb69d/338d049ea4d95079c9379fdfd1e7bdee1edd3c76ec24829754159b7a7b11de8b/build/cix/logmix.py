"""Experimental PAQ-style logistic bit mixer for universal CIX.

All experts are generic byte-history functions: contiguous/sparse contexts, lag
predictors and a match predictor. The mixer combines log-odds and adapts weights online
to coding loss. This is an experiment; production would replace floating-point squash /
stretch with fixed deterministic tables.
"""
from __future__ import annotations
import math
from .multinomial import _ArithmeticEncoder,_ArithmeticDecoder,vencode,vdecode

VERSION=1
SCALE=1<<15
COUNT_LIMIT=2048
PATTERNS=((),(1,),(1,2),(1,2,3),(1,2,3,4),(1,3),(1,4),(1,5),(2,3),(2,4),(3,6),(4,8),(1,4,8))
LAGS=(1,2,4,8,16,32)
MATCH_ORDER=4
CLIP=9.0

def _context(h,pat):
    if not pat:return ()
    if len(h)<max(pat):return None
    return tuple(h[-x] for x in pat)

def _stretch(p):
    p=min(1-1e-6,max(1e-6,p))
    return max(-CLIP,min(CLIP,math.log(p/(1-p))))

def _squash(x):
    x=max(-CLIP,min(CLIP,x))
    return 1/(1+math.exp(-x))

def _ctx_p(counts):
    if counts is None:return .5
    z,o=counts
    return (o+.5)/(z+o+1)

def _reliability_p(pred,rel,bp):
    if pred is None:return .5
    good,bad=rel[bp]
    conf=(good+.5)/(good+bad+1)
    bit=(pred>>(7-bp))&1
    return conf if bit else 1-conf

class State:
    def __init__(self,prefix=b"",eta=.01):
        self.h=bytearray(prefix[-65536:])
        self.tables=[{} for _ in PATTERNS]
        n=len(PATTERNS)+len(LAGS)+1
        self.weights=[[1.0/n]*n for _ in range(8)]
        self.bias=[0.0]*8
        self.eta=eta
        self.lag_rel=[[[1,1] for _ in range(8)] for _ in LAGS]
        self.match_rel=[[1,1] for _ in range(8)]
        self.matches={}
    def preds(self,bp,pref):
        ps=[];keys=[]
        for i,pat in enumerate(PATTERNS):
            c=_context(self.h,pat)
            key=(c,bp,pref) if c is not None else None;keys.append(key)
            ps.append(_ctx_p(self.tables[i].get(key) if key is not None else None))
        for li,lag in enumerate(LAGS):
            pred=self.h[-lag] if len(self.h)>=lag else None
            ps.append(_reliability_p(pred,self.lag_rel[li],bp))
        pred=self.matches.get(bytes(self.h[-MATCH_ORDER:])) if len(self.h)>=MATCH_ORDER else None
        ps.append(_reliability_p(pred,self.match_rel,bp))
        ts=[_stretch(p) for p in ps]
        z=self.bias[bp]+sum(w*t for w,t in zip(self.weights[bp],ts))
        return _squash(z),ts,keys
    def update(self,bp,pref,bit,p,ts,keys):
        err=bit-p
        self.bias[bp]=max(-CLIP,min(CLIP,self.bias[bp]+self.eta*err))
        ws=self.weights[bp]
        for i,t in enumerate(ts):
            ws[i]=max(-4.0,min(4.0,ws[i]+self.eta*err*t))
        for i,key in enumerate(keys):
            if key is None:continue
            c=self.tables[i].get(key)
            if c is None:c=[0,0];self.tables[i][key]=c
            c[bit]+=1
            if c[0]+c[1]>COUNT_LIMIT:c[0]=(c[0]+1)//2;c[1]=(c[1]+1)//2
        for li,lag in enumerate(LAGS):
            if len(self.h)>=lag:
                pred=(self.h[-lag]>>(7-bp))&1;r=self.lag_rel[li][bp]
                r[0 if pred==bit else 1]+=1
                if sum(r)>COUNT_LIMIT:r[0]=(r[0]+1)//2;r[1]=(r[1]+1)//2
        if len(self.h)>=MATCH_ORDER:
            predbyte=self.matches.get(bytes(self.h[-MATCH_ORDER:]))
            if predbyte is not None:
                pred=(predbyte>>(7-bp))&1;r=self.match_rel[bp]
                r[0 if pred==bit else 1]+=1
                if sum(r)>COUNT_LIMIT:r[0]=(r[0]+1)//2;r[1]=(r[1]+1)//2
    def byte(self,b):
        if len(self.h)>=MATCH_ORDER:self.matches[bytes(self.h[-MATCH_ORDER:])]=b
        self.h.append(b)
        if len(self.h)>65536:del self.h[:-32768]

ETAS=(.0025,.005,.01,.02)

def _encode(data,prefix,eta_id):
    eta=ETAS[eta_id];s=State(prefix,eta);enc=_ArithmeticEncoder()
    for b in data:
        pref=0
        for bp in range(8):
            bit=(b>>(7-bp))&1;p,ts,keys=s.preds(bp,pref)
            one=min(SCALE-1,max(1,int(round(p*SCALE))));zero=SCALE-one
            if bit:enc.encode(zero,SCALE,SCALE)
            else:enc.encode(0,zero,SCALE)
            s.update(bp,pref,bit,p,ts,keys);pref=(pref<<1)|bit
        s.byte(b)
    payload,bits=enc.finish()
    return bytes((VERSION,eta_id))+vencode(bits)+payload

def encode_logmix(data,prefix_history=b"",eta_id=None):
    if eta_id is not None:return _encode(data,prefix_history,eta_id)
    return min((_encode(data,prefix_history,i) for i in range(len(ETAS))),key=len)

def decode_logmix(blob,source_length,prefix_history=b""):
    if len(blob)<2 or blob[0]!=VERSION:raise ValueError("bad logmix version")
    eid=blob[1]
    if eid>=len(ETAS):raise ValueError("bad eta")
    bits,pos=vdecode(blob,2)
    if pos+(bits+7)//8!=len(blob):raise ValueError("bad logmix payload")
    s=State(prefix_history,ETAS[eid]);dec=_ArithmeticDecoder(blob[pos:],bits);out=bytearray()
    for _ in range(source_length):
        b=0;pref=0
        for bp in range(8):
            p,ts,keys=s.preds(bp,pref);one=min(SCALE-1,max(1,int(round(p*SCALE))));zero=SCALE-one
            target=dec.target(SCALE)
            if target<zero:bit=0;dec.update(0,zero,SCALE)
            else:bit=1;dec.update(zero,SCALE,SCALE)
            s.update(bp,pref,bit,p,ts,keys);b=(b<<1)|bit;pref=(pref<<1)|bit
        out.append(b);s.byte(b)
    return bytes(out)
