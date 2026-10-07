import itertools
import math
import random
import pytest
from benchmarks import binary_markov_runs as codec,markov_euler


def test_binary_factorization_matches_general_exact_trail_count():
    for n in range(1,10):
        for values in itertools.product(range(2),repeat=n):
            data=bytes(values);matrix=[[0,0],[0,0]]
            for a,b in zip(values,values[1:]):matrix[a][b]+=1
            target=markov_euler.cardinality(markov_euler.freeze(matrix),values[0],values[-1])
            for method in (0,1):
                blob,stats=codec.encode_group(data,method);restored,pos=codec.decode_group(blob,0,n,method)
                assert restored==data and pos==len(blob)
                assert stats['valid_space_bits']==pytest.approx(math.log2(target))


@pytest.mark.parametrize('method',(0,1))
def test_long_binary_classes_and_invalid_metadata(method):
    rng=random.Random(41)
    for data in [b'\0'*8192,b'\1'*8192,b'\0'*4096+b'\1'*4096,bytes(rng.randrange(2) for _ in range(8192))]:
        blob,_=codec.encode_group(data,method);restored,pos=codec.decode_group(blob,0,len(data),method)
        assert restored==data and pos==len(blob)
    with pytest.raises(ValueError):codec.decode_group(b'\0\0',0,4,method)
    with pytest.raises(ValueError):codec.decode_group(b'\x05\x02',0,4,method)
