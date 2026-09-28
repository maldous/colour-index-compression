"""Log-domain control for causal register expert mixing.

Linear posterior floors can forget evidence over long sequences. This control
retains relative expert log likelihoods, including experts whose current coding
weight rounds to zero. Future observations can revive them. Prediction-only;
native deterministic logarithm/weight tables are not implemented by this screen.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
from benchmarks import paq_register_adaptive_screen as screen


class LogPosterior:
    SCALE=1<<20
    def __init__(self,experts=5,native_bias=1):
        self.scores=[round(math.log2(native_bias)*self.SCALE)]+[0]*(experts-1)
    def mix(self,predictions):
        top=max(self.scores)
        weights=[0 if s-top < -64*self.SCALE else int((2**((s-top)/self.SCALE))*(1<<48)+0.5) for s in self.scores]
        total=sum(weights)
        return max(1,min(0x7fffffff,(sum(w*p for w,p in zip(weights,predictions))+total//2)//total))
    def observe(self,predictions,y):
        if len(set(predictions))==1:return
        for i,p in enumerate(predictions):
            likelihood=p if y else (1<<31)-p
            self.scores[i]+=round(math.log2(likelihood/(1<<31))*self.SCALE)
        top=max(self.scores);self.scores=[s-top for s in self.scores]


if __name__=='__main__':
    screen.Posterior=LogPosterior
    report=screen.analyze(sys.argv[1]);report['numerical_control']=__doc__
    report['source_hashes'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['posterior']='relative Q20 log likelihood; Q48 coding weights; no floor imposed on past expert evidence'
    Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['rows'],indent=2))
