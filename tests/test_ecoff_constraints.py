import io
import struct
import tarfile
import pytest
from benchmarks import ecoff_constraints as codec


def object_file(noncanonical=False):
    names=b'\0a\0i\0q\0'
    symbols=b''.join(struct.pack('<IIQIBBH',off,int(i==0),i*1234,0,0x12,0,0xff01) for i,off in enumerate((0,1,3,5)))
    # All three one-letter hashes occupy bucket 1; ascending chain 1,2,3.
    hashes=struct.pack('<14I',8,4,0,1,0,0,0,0,0,0,0,2,3,0)+b'PADD'
    reloc=struct.pack('<QII',0,0,1)+b''.join(struct.pack('<QII',i*8,(symbol<<8)|2,0) for i,symbol in enumerate((1,3,2),1))
    msym=struct.pack('<8I',0,0,97,256,105,768,113,512)+b'tail'
    if noncanonical:msym=msym[:8]+b'XXXX'+msym[12:]
    parts=[(b'.dynstr',names),(b'.dynsym',symbols),(b'.rel.dyn',reloc),(b'.hash',hashes),(b'.msym',msym)]
    header=bytearray(24+80+64*len(parts));struct.pack_into('<HHIQIHH',header,0,0x183,len(parts),123,0,0,80,0x2007)
    out=bytearray(header)
    for i,(name,content) in enumerate(parts):
        offset=len(out);out.extend(content)
        struct.pack_into('<8sQQQQQQHHI',out,104+64*i,name,0,0,len(content),offset,0,0,0,0,0)
    return bytes(out)+b'literal suffix'


@pytest.mark.parametrize('mode',range(4))
def test_derived_tables_and_literal_padding(mode):
    data=object_file();raw,stats=codec.transform(data,mode)
    assert codec.inverse(raw)==data
    assert stats['hash_tables']==bool(mode&1) and stats['msym_tables']==bool(mode&2)
    if mode==3:
        assert stats['derived_bytes']==80
        sec=codec.sections(data);damaged=bytearray(raw);damaged[sec[b'.hash'][0]+8]=1
        with pytest.raises(ValueError,match='not zero'):codec.inverse(bytes(damaged))


def test_noncanonical_exception_and_multiple_tar_objects():
    good=object_file();bad=object_file(True);stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        for name,data in [('arbitrary-name',good),('not-an-extension',bad),('literal',b'ordinary bytes')]:
            info=tarfile.TarInfo(name);info.size=len(data);archive.addfile(info,io.BytesIO(data))
    source=stream.getvalue()+b'extra bytes';raw,stats=codec.transform(source,3)
    assert codec.inverse(raw)==source
    assert stats['hash_tables']==2 and stats['msym_tables']==1
    for unknown in (b'',b'garbage\x83\x01',good[:80]):assert codec.inverse(codec.transform(unknown)[0])==unknown
