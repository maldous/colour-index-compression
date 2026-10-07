from fractions import Fraction
from benchmarks.paq_register_adaptive_screen import Posterior


def test_fixed_point_posterior_matches_exact_sequential_bayes():
    model=Posterior(experts=2,native_bias=8);weights=[Fraction(8),Fraction(1)]
    sequence=[(0x30000000,0x58000000,0),(0x62000000,0x10000000,1),
              (0x44000000,0x33000000,1),(0x38000000,0x61000000,0)]*8
    for p,q,y in sequence:
        expected=(weights[0]*p+weights[1]*q)/sum(weights)
        assert abs(model.mix([p,q])-float(expected))<20
        model.observe([p,q],y)
        weights=[w*(r if y else (1<<31)-r) for w,r in zip(weights,(p,q))]
        assert min(model.weights)>0


def test_equal_experts_preserve_state_and_exact_prediction():
    model=Posterior();initial=model.weights.copy()
    for p in (1,1<<30,0x7fffffff):
        assert model.mix([p]*5)==p
        for y in (0,1):model.observe([p]*5,y);assert model.weights==initial
