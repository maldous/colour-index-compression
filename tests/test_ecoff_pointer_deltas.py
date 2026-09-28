import pytest
from benchmarks import ecoff_pointer_deltas as codec
from tests.test_ecoff_relocated_pointers import object_file,archive


@pytest.mark.parametrize('mode',range(6))
def test_causal_pointer_deltas_and_modular_edges(mode):
    for data in [archive(),object_file((0,99,42),(0,(1<<64)-1,1<<63,99),(1,1,1,1)),b'no object']:
        raw,stats=codec.transform(data,mode);assert codec.inverse(raw)==data
    x=object_file((0,99,42),(99,42,99,42),(1,2,1,2))
    _,stats=codec.transform(x,mode)
    if mode in (2,3,5):assert stats['exact_predictions']==4


def test_residual_overflow_rejected():
    x=object_file((0,99,42),(99,),(1,));raw,_,_=codec.process(x,4)
    with pytest.raises(ValueError,match='outside word'):codec.process(raw,4,True,codec.vencode(1<<64))
