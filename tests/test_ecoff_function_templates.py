import struct
import pytest
from benchmarks import ecoff_function_templates as codec


@pytest.mark.parametrize('mode',[0,1,2])
def test_causal_template_chain(monkeypatch,mode):
    words=[(8<<26)+i*16 for i in range(16)]
    regions=[(i*64,64) for i in range(6)]
    blobs=[]
    for i in range(6):
        row=list(words);row[2]+=i;row[9]-=i
        blobs.append(struct.pack('<16I',*row))
    data=b''.join(blobs)
    monkeypatch.setattr(codec,'regions',lambda raw:regions)
    monkeypatch.setattr(codec.parent,'transform',lambda raw,mode:(raw,{}))
    monkeypatch.setattr(codec.parent,'inverse',lambda raw:raw)
    raw,stats=codec.transform(data,mode)
    assert codec.inverse(raw)==data
    assert stats['template_functions']==(5 if mode else 0)
    if mode:
        corrupted=bytearray(raw)
        # First selected function must refer backward, never to itself.
        meta=len(raw)-13-int.from_bytes(raw[-13:-5],'little')
        corrupted[meta+3]=0
        with pytest.raises(ValueError,match='backward'):codec.inverse(bytes(corrupted))


@pytest.mark.parametrize('mode',[0,1,2])
def test_unrecognized_bytes_round_trip(mode):
    data=bytes(range(256))*2
    raw,stats=codec.transform(data,mode)
    assert codec.inverse(raw)==data
    assert stats['template_functions']==0
