import random
import struct
import pytest
from benchmarks import paq_cix_match as codec


@pytest.mark.parametrize('method',(0,1,2))
def test_match_components_and_controls(method):
    rng=random.Random(99);groups=[bytearray() for _ in range(4)];events=[]
    for pos in range(1500):
        group=rng.randrange(4);token=rng.choice([8]*16+list(range(8)))
        groups[group].append(token);events.append(struct.pack('<IBB',pos,group,token))
    records=b'CIXJ1'+b''.join(events);paq=b'paq8px\x04\0FAKE';source=b'source identity'
    frame,stats=codec.encode(source,paq,records,method)
    actual,raw,n,crc=codec.components(frame)
    assert actual==paq and n==len(source)
    assert raw==b'CIXM1'+b''.join(len(g).to_bytes(8,'little')+g for g in groups)
    assert stats['eliminated_bit_decisions']==sum(min(8,t+1) for g in groups for t in g)
    with pytest.raises(ValueError):codec.components(frame+b'\0')
    with pytest.raises(ValueError):codec.components(frame[:-1])


def test_counts_singleton_and_sparse():
    for counts in ([0]*8+[50000],[7,2,0,0,0,0,0,0,60000],[10]*9):
        blob=codec.encode_counts(counts);actual,pos=codec.decode_counts(blob,0,sum(counts))
        assert counts==actual and pos==len(blob)


def test_adaptive_count_rescaling():
    data=bytes(random.Random(1).choices(range(9),k=5000));payload,bits=codec.adaptive_encode(data)
    assert codec.adaptive_decode(payload,bits,len(data))==data
