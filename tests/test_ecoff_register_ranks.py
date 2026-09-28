import random
import struct
import pytest
from benchmarks import ecoff_register_ranks as codec
from tests.test_paq_memory_feedback import memory_fixture


@pytest.mark.parametrize('mode',range(1,5))
def test_register_ranks_all_opcodes_and_reset_boundaries(mode):
    rng=random.Random(710);words=[(op<<26)|rng.getrandbits(26) for _ in range(9) for op in range(64)]
    data=struct.pack('>'+'I'*len(words),*words);coded=codec.recency(data,mode)
    assert codec.recency(coded,mode,True)==data
    # BSR target bits and the Opr literal-selector bit retain their meaning.
    for old,(new,) in zip(words,struct.iter_unpack('>I',coded)):
        assert old>>26==new>>26
        if old>>26==0x34:assert old&0x1fffff==new&0x1fffff
        if old>>26 in (0x10,0x11,0x12,0x13,0x1c):assert old&(1<<25)==new&(1<<25)
    full=b'abc'+data+b'tail';transformed=codec.transform(full,[(3,len(data))],mode)
    assert codec.inverse(transformed,mode)==full


@pytest.mark.parametrize('mode',range(5))
def test_native_register_frames_restore(mode):
    data=memory_fixture();frame,stats=codec.encode(data,mode)
    assert codec.decode(frame)==data
    if mode:assert stats['regions']==1
