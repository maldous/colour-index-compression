import io
import struct
import tarfile
import pytest
from benchmarks import ecoff_relocated_pointers as codec


def object_file(values,targets,indices,duplicate=False):
    names=b'\0alpha\0beta\0';virtual=0x120002000
    symbols=b''.join(struct.pack('<IIQIBBH',o,0,v,0,0x12,0,0xff01) for o,v in zip((0,1,7),values))
    relocs=b''.join(struct.pack('<QII',virtual+8*i,(s<<8)|2,0) for i,s in enumerate(indices))
    if duplicate:relocs+=struct.pack('<QII',virtual,258,0)
    # Invalid relocation type and out-of-section address must remain literal.
    relocs+=struct.pack('<QII',virtual+1,257,0)+struct.pack('<QII',virtual+4096,258,0)
    parts=[(b'.dynstr',0,names),(b'.dynsym',0,symbols),(b'.hash',0,struct.pack('<7I',2,3,0,0,0,0,0)),
           (b'.rdata',virtual,struct.pack('<'+'Q'*len(targets),*targets)),(b'.rel.dyn',0,relocs)]
    out=bytearray(104+64*len(parts));struct.pack_into('<HHIQIHH',out,0,0x183,len(parts),0,0,0,80,0x2007)
    for i,(name,v,raw) in enumerate(parts):
        start=len(out);out.extend(raw);struct.pack_into('<8sQQQQQQHHI',out,104+64*i,name,v,v,len(raw),start,0,0,0,0,0)
    return bytes(out)


def archive():
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as tar:
        for i,x in enumerate([object_file((0,0,42),(99,1234567,42),(1,1,2)),object_file((0,99,42),(99,42),(1,2))]):
            info=tarfile.TarInfo(str(i));info.size=len(x);tar.addfile(info,io.BytesIO(x))
    return stream.getvalue()+b'unchanged trailer'


@pytest.mark.parametrize('mode',range(6))
def test_named_relocations_shared_candidates_and_literal_exceptions(mode):
    data=archive()
    for shared,expected in [(False,3),(True,4)]:
        raw,stats=codec.transform(data,mode,shared);assert codec.inverse(raw)==data
        assert stats['mapped_pointers']==5 and stats['in_candidates']==expected
        if mode==4:assert stats['choice_model_bits']==pytest.approx(stats['candidate_combinatorial_bits'])
    assert codec.inverse(codec.transform(b'unknown input',mode)[0])==b'unknown input'


def test_duplicate_relocations_remain_literal_and_bad_indices_rejected():
    data=object_file((0,99,42),(99,42),(1,2),True)
    raw,stats=codec.transform(data,1);assert stats['mapped_pointers']==1 and codec.inverse(raw)==data
    with pytest.raises(ValueError):codec.inverse(raw[:-1])


def test_invalid_in_place_index_is_rejected():
    data=object_file((0,99,42),(99,42),(1,2));raw,_=codec.transform(data,1)
    size=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-size
    skeleton=bytearray(codec.parent.inverse(raw[:start]));where=codec.candidates(data)[0][0]
    struct.pack_into('<Q',skeleton,where,999)
    changed,_=codec.parent.transform(bytes(skeleton),3)
    with pytest.raises(ValueError,match='outside alphabet'):codec.inverse(changed+raw[start:])
