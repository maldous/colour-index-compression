import struct
import pytest
from benchmarks import ecoff_section_pointers as codec


def object_file():
    text=0x120000000;rdata=0x200000000;names=b'\0.text\0.rdata\0funcA\0funcB\0'
    symbols=b''.join(struct.pack('<IIQIBBH',off,0,value,0,0x12,0,0xff01)
                      for off,value in [(0,0),(1,text+4),(7,rdata),(14,text+8),(20,text+16)])
    targets=[text+8,text+12,text+3,(1<<64)-1,rdata+16,rdata+8]
    reloc=b''.join(struct.pack('<QII',rdata+i*8,(symbol<<8)|2,0) for i,symbol in enumerate([1,1,1,1,2,2]))
    parts=[(b'.dynstr',0,names),(b'.dynsym',0,symbols),(b'.hash',0,struct.pack('<9I',2,5,0,0,0,0,0,0,0)),
           (b'.pdata',text-1024,struct.pack('<6i',1024,0,1032,0,1040,0)),(b'.text',text,bytes(32)),
           (b'.rdata',rdata,struct.pack('<6Q',*targets)),(b'.rel.dyn',0,reloc)]
    out=bytearray(104+64*len(parts));struct.pack_into('<HHIQIHH',out,0,0x183,len(parts),0,0,0,80,0x2007)
    for i,(name,v,raw) in enumerate(parts):
        start=len(out);out.extend(raw);struct.pack_into('<8sQQQQQQHHI',out,104+64*i,name,v,v,len(raw),start,0,0,0,0,0)
    return bytes(out)


@pytest.mark.parametrize('mode',range(7))
def test_section_function_support_and_literal_exceptions(mode):
    x=object_file();raw,stats=codec.transform(x,mode);assert codec.inverse(raw)==x
    expected={0:1,1:1,2:2,3:4,4:3,5:1,6:1}
    assert stats['in_candidates']==expected[mode]
    if mode==6:assert stats['choice_model_bits']==pytest.approx(stats['candidate_combinatorial_bits'])
    assert codec.inverse(codec.transform(b'unsupported literal',mode)[0])==b'unsupported literal'


def test_function_rank_outside_alphabet_rejected():
    x=object_file();raw,_=codec.transform(x,1);size=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-size
    normalized=bytearray(codec.parent.inverse(raw[:start]));where,declared,_,pool=codec.fields(x,1)[0]
    struct.pack_into('<Q',normalized,where,declared+len(pool))
    corrupt,_=codec.parent.transform(bytes(normalized),5)
    with pytest.raises(ValueError,match='outside alphabet'):codec.inverse(corrupt+raw[start:])
