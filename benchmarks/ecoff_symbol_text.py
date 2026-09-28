"""Expose transmitted symbol-name boundaries to PAQ's text models.

The position-preserving byte permutations are involutions. Symbol tables, counts,
GOT candidates and all exceptions are restored before the parent inverse runs.
"""
from benchmarks import ecoff_got as parent

MAGIC = b'ECST1'


def ranges(data):
    out=[]
    for off,size in parent.parent.base.objects(data):
        sections=parent.parent.base.sections(data[off:off+size])
        if b'.dynstr' in sections:
            start,length=sections[b'.dynstr'];out.append((off+start,length))
    return out


def permutation(mode):
    if mode not in (0,1,2):raise ValueError('invalid symbol-text permutation')
    table=bytearray(range(256))
    if mode:
        table[0],table[10]=table[10],table[0]
    if mode==2:
        table[32],table[95]=table[95],table[32]
    return bytes(table)


def transform(data,mode=1):
    table=permutation(mode);fields=ranges(data);skeleton,stats=parent.transform(data,3);out=bytearray(skeleton)
    for start,length in fields:out[start:start+length]=out[start:start+length].translate(table)
    raw=bytes(out)+bytes([mode])+MAGIC
    return raw,dict(mode=mode,original_bytes=len(data),transformed_bytes=len(raw),symbol_tables=len(fields),symbol_bytes=sum(n for _,n in fields),parent_statistics=stats)


def inverse(raw):
    if len(raw)<6 or raw[-5:]!=MAGIC:raise ValueError('invalid symbol-text frame')
    table=permutation(raw[-6]);out=bytearray(raw[:-6])
    for start,length in ranges(out):out[start:start+length]=out[start:start+length].translate(table)
    return parent.inverse(bytes(out))
