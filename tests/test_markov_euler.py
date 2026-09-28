from collections import defaultdict
import itertools
import random
import pytest
from benchmarks import markov_euler as codec


def test_exact_counts_and_ranks_against_exhaustive_sequences():
    for n in range(1,8):
        groups=defaultdict(list)
        for sequence in itertools.product(range(3),repeat=n):
            matrix=[[0]*3 for _ in range(3)]
            for a,b in zip(sequence,sequence[1:]):matrix[a][b]+=1
            groups[(codec.freeze(matrix),sequence[0],sequence[-1])].append(sequence)
        for (matrix,start,end),sequences in groups.items():
            assert codec.cardinality(matrix,start,end)==len(sequences)
            for rank,sequence in enumerate(sequences):
                assert codec.trail_rank(sequence,matrix)==(rank,len(sequences))


@pytest.mark.parametrize('mode',range(4))
def test_physical_round_trips(mode):
    rng=random.Random(20260928)
    cases=[b'',b'x',b'x'*128,bytes(range(8))*16,b'\0'*64+b'\1'*64+b'\2'*64]
    cases += [bytes(rng.randrange(k) for _ in range(128)) for k in (2,3,8)]
    for data in cases:
        frame,stats=codec.encode(data,mode);codec.cardinality.cache_clear()
        assert codec.decode(frame)==data
        assert stats['valid_trail_space_bits']<=stats['row_space_bits']+1e-9
        with pytest.raises(ValueError):codec.decode(frame[:-1])


def test_dead_end_orderings_are_removed_by_both_conditioned_coders():
    data=b'\0'*64+b'\1'*64+b'\2'*64
    rows=[codec.encode(data,m)[1] for m in range(4)]
    assert rows[2]['valid_trail_space_bits']==0 and rows[2]['row_space_bits']==12
    assert rows[2]['payload_bits']==rows[3]['payload_bits']==0
    assert rows[0]['payload_bytes']>rows[2]['payload_bytes']
    assert codec.cardinality(((1,0),(0,1)),0,0)==0
