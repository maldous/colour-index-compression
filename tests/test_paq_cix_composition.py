import itertools
import random
import numpy as np
import pytest
from cix.multinomial import _ArithmeticBitWriter,_ArithmeticBitReader
from benchmarks import paq_cix_composition as codec
from benchmarks.paq_cix_residual import partition


def test_exact_packed_rank_boundaries():
    streams=[bytes(x) for n in range(6) for x in itertools.product((0,1),repeat=n)]
    writer=_ArithmeticBitWriter()
    for stream in streams:codec.put_rank(writer,stream)
    blob,bits=writer.finish();reader=_ArithmeticBitReader(blob,bits)
    for stream in streams:assert codec.take_rank(reader,len(stream),sum(stream))==stream
    assert reader.pos==bits


@pytest.mark.parametrize('mode',(0,1,2))
@pytest.mark.parametrize('block_size',(16,64,256))
def test_causal_composition_reconstruction(mode,block_size):
    rng=random.Random(92);words=[rng.randrange(1,1<<31)|(rng.randrange(2)<<31) for _ in range(2000)]
    trace=np.array(words,dtype='<u4').tobytes();header=b'paq8px\x04\0';source=b'original identity'
    frame,stats=codec.encode(trace,header+b'\0'*4,source,block_size=block_size,mode=mode)
    actual_header,raw,n,crc=codec.residuals(frame);groups,_=partition(trace,0)
    assert actual_header==header and n==len(source)
    assert raw==b'CIXE1\0'+b''.join(len(g).to_bytes(8,'little')+g for g in groups)
    assert stats['physical_bytes']==len(frame)
    with pytest.raises(ValueError):codec.residuals(frame[:-1])
    with pytest.raises(ValueError):codec.residuals(frame+b'\0')


def test_prior_is_exactly_binomial_at_half():
    import math
    prior=codec.binomial_prior(16,30,0)
    assert prior==tuple(max(1,math.comb(16,k)*codec.SCALE//(1<<16)) for k in range(17))


def test_prior_updates_use_only_previous_counts():
    model=codec.CompositionModel(0,1);before=model.frequencies(64,28)
    model.observe(64,28,2);after=model.frequencies(64,28)
    assert after[2]/sum(after)>before[2]/sum(before)
