"""Independent integer oracle for explicitly discounted causal log evidence."""
from benchmarks.register_log_math import TablePosterior


class DiscountPosterior(TablePosterior):
    def __init__(self,shift):
        if shift not in (0,5,7,9,11): raise ValueError('unsupported discount shift')
        super().__init__(); self.shift=shift

    def observe(self,predictions,y):
        if len(set(predictions))==1: return
        super().observe(predictions,y)
        if self.shift:
            denominator=1<<self.shift
            self.scores=[-(((-s)*(denominator-1)+denominator//2)//denominator) for s in self.scores]
