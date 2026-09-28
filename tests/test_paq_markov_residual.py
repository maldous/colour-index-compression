import numpy as np
import pytest
from benchmarks import paq_markov_residual as codec


@pytest.mark.parametrize('method',(0,2,3))
def test_whole_group_and_markov_selection_reconstruct_exact_errors(method):
    for errors in [[],[0]*32,[0,1]*256,[0]*1024+[1]*1024]:
        trace=np.array([(1<<30)|(y<<31) for y in errors],dtype='<u4').tobytes()
        frame,stats=codec.encode(trace,b'paq8px'+bytes([4,0])+bytes(4),b'placeholder',method,1)
        header,raw,n,crc=codec.residuals(frame);groups,_=codec.base.partition(trace,1)
        expected=b'CIXE1\x01'+b''.join(len(x).to_bytes(8,'little')+x for x in groups)
        assert raw==expected and n==len(b'placeholder')
        if method and len(errors)==2048:assert stats['selected_markov_groups']==1
        with pytest.raises(ValueError):codec.residuals(frame[:-1])
