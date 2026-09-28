import math
from benchmarks.paq_register_log_screen import LogPosterior


def test_long_evidence_survives_coding_weight_underflow():
    model=LogPosterior(experts=2);predictions=[int(0.9*(1<<31)),int(0.1*(1<<31))]
    costs=[0.,0.];mixed=0.
    for y in [0]*300+[1]*600:
        p=model.mix(predictions);mixed-=math.log2((p if y else (1<<31)-p)/(1<<31))
        for i,q in enumerate(predictions):costs[i]-=math.log2((q if y else (1<<31)-q)/(1<<31))
        model.observe(predictions,y)
    assert mixed<=min(costs)+1.01
    assert model.scores[0]>model.scores[1]


def test_equal_expert_updates_have_no_relative_effect():
    model=LogPosterior(native_bias=8);before=model.scores.copy()
    for p in (1,1<<30,0x7fffffff):
        assert model.mix([p]*5)==p
        model.observe([p]*5,1)
    assert model.scores==before
