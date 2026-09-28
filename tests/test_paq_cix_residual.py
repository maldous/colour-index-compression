import itertools
import math
import random
import pytest
import numpy as np
from benchmarks import paq_cix_residual as codec


def test_exhaustive_binary_type_classes():
    for n in range(9):
        ranks={}
        for bits in itertools.product((0,1),repeat=n):
            stream=bytes(bits);k=sum(bits);blob=codec.rank_binary(stream)
            assert codec.unrank_binary(blob,n,k)==stream
            ranks.setdefault(k,set()).add(int.from_bytes(blob,'big'))
            arithmetic=codec.arith_binary(stream)
            restored,end=codec.unarith_binary(arithmetic,0,n,k)
            assert restored==stream and end==len(arithmetic)
        for k,values in ranks.items():assert values==set(range(math.comb(n,k)))


@pytest.mark.parametrize('subbits',range(4))
def test_prediction_partition_matches_integer_definition(subbits):
    probabilities=[1,2,3,4,7,8,1023,1024,(1<<30)-1,1<<30,(1<<30)+1,(1<<31)-1]
    records=[p|(y<<31) for p in probabilities for y in (0,1)]
    trace=np.array(records,dtype='<u4').tobytes()
    groups,_=codec.partition(trace,subbits)
    expected=[bytearray() for _ in groups]
    for record in records:
        p=record&0x7fffffff;y=record>>31;q=min(p,(1<<31)-p);exponent=q.bit_length()-1;base=1<<exponent
        index=(exponent<<subbits)+(((q-base)<<subbits)//base)
        expected[index].append(y^(p>>30))
    assert groups==list(map(bytes,expected))


@pytest.mark.parametrize('method',(0,1))
def test_self_contained_compositions(method):
    rng=random.Random(5);records=[rng.randrange(1,1<<31)|(rng.randrange(2)<<31) for _ in range(1000)]
    trace=np.array(records,dtype='<u4').tobytes();header=b'paq8px\x04\0';source=b'arbitrary source identity'
    frame,stats=codec.encode(trace,header+b'\0'*4,source,1,method)
    actual_header,raw,n,crc=codec.residuals(frame)
    groups,_=codec.partition(trace,1)
    expected=b'CIXE1\1'+b''.join(len(g).to_bytes(8,'little')+g for g in groups)
    assert raw==expected and actual_header==header and n==len(source)
    assert stats['physical_bytes']==len(frame)
    with pytest.raises(ValueError):codec.residuals(frame+b'\0')
