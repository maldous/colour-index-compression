"""Independent Python integer oracle for the pinned native logarithm tables."""
from functools import lru_cache
from pathlib import Path
import re

HEADER=Path(__file__).parent/'native/CixLogTables.hpp'
SCALE=1<<20


@lru_cache(maxsize=1)
def tables():
    text=HEADER.read_text();out=[]
    for name in ('LOG2_MANTISSA','EXP2_NEGATIVE'):
        body=text.split(name+'[] = {',1)[1].split('};',1)[0]
        values=tuple(map(int,re.findall(r'\d+',body)))
        if len(values)!=4097:raise ValueError('lookup table size changed')
        out.append(values)
    return out


def log_probability(p):
    if not 0<p<=1<<31:raise ValueError('invalid probability')
    logs,_=tables();exponent=p.bit_length()-1;mantissa=(p<<30)>>exponent
    fraction=mantissa-(1<<30);index=fraction>>18;remainder=fraction&((1<<18)-1)
    interpolated=logs[index]+((logs[index+1]-logs[index])*remainder+(1<<17))//(1<<18)
    return (exponent-31)*SCALE+(interpolated+512)//1024


def coding_weight(deficit):
    _,exps=tables();whole=deficit>>20
    if whole>=64:return 0
    fraction=deficit&(SCALE-1);index=fraction>>8;remainder=fraction&255
    interpolated=exps[index]-((exps[index]-exps[index+1])*remainder+128)//256
    return interpolated if whole==0 else (interpolated+(1<<(whole-1)))>>whole


class TablePosterior:
    def __init__(self,experts=5,native_bias=1):
        if experts!=5 or native_bias not in (1,8):raise ValueError('unsupported oracle configuration')
        self.scores=[3*SCALE if native_bias==8 else 0]+[0]*4
    def mix(self,predictions):
        top=max(self.scores);weights=[coding_weight(top-s) for s in self.scores];total=sum(weights)
        return max(1,min(0x7fffffff,(sum(w*p for w,p in zip(weights,predictions))+total//2)//total))
    def observe(self,predictions,y):
        if len(set(predictions))==1:return
        self.scores=[s+log_probability(p if y else (1<<31)-p) for s,p in zip(self.scores,predictions)]
        top=max(self.scores);self.scores=[s-top for s in self.scores]
