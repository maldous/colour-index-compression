"""Causal copy-and-correct function templates, with every reference transmitted.

Function boundaries come from in-stream pdata and section tables. The encoder
matches opcode signatures across preceding functions; decoding needs only the
paid backward references, residual words, and already restored functions.
"""
import bisect
from collections import defaultdict
import struct
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_pointer_deltas as parent

MAGIC = b'ECFT1'


def regions(data):
    found = set()
    for off, d, _, _ in parent.parent.objects(data):
        sections = {}
        for i in range(struct.unpack_from('<H', d, 2)[0]):
            name, _, v, n, p, *_ = struct.unpack_from('<8sQQQQQQHHI', d, 104+64*i)
            sections[name.rstrip(b'\0')] = (v,n,p)
        if b'.pdata' not in sections: continue
        pv,pn,pp = sections[b'.pdata']
        starts = sorted(set((pv+(struct.unpack_from('<i', d, p)[0]&~3))&((1<<64)-1)
                            for p in range(pp,pp+pn//8*8,8)))
        for label in (b'.text',b'.init',b'.fini'):
            if label not in sections: continue
            a,n,p = sections[label]
            if not p: continue
            points = [v for v in starts if a <= v < a+n] + [a+n]
            for left,right in zip(points,points[1:]):
                length = right-left
                if 32 <= length <= 65536 and length%4 == 0:
                    found.add((off+p+left-a,length))
    result = sorted(found)
    if any(p+n>q for (p,n),(q,_) in zip(result,result[1:])):
        raise ValueError('overlapping function templates')
    return result


def transform(data, mode=1):
    if mode not in (0,1,2): raise ValueError('invalid template representation')
    fields=regions(data); out=bytearray(data); seen=defaultdict(list); changes=[]
    matched=changed=0
    for i,(p,n) in enumerate(fields):
        words=struct.unpack_from('<'+'I'*(n//4),data,p)
        # Deliberately bounded search: opcode sequence, four recent templates.
        key=bytes(w>>26 for w in words)
        candidates=seen[(n,key)]
        best=None
        for j in candidates:
            q,_=fields[j]; previous=struct.unpack_from('<'+'I'*(n//4),data,q)
            neq=sum(a!=b for a,b in zip(words,previous))
            if best is None or neq<best[0]: best=(neq,j,previous)
        if mode and best and best[0]*2 <= len(words):
            neq,j,previous=best
            residual=[a^b for a,b in zip(words,previous)] if mode==1 else [(a-b)&0xffffffff for a,b in zip(words,previous)]
            struct.pack_into('<'+'I'*len(residual),out,p,*residual)
            changes.append((i,j)); matched+=n; changed+=neq
        candidates.append(i)
        if len(candidates)>4: del candidates[0]
    skeleton,stats=parent.transform(bytes(out),5)
    meta=bytearray([mode])+vencode(len(changes)); last=-1
    for i,j in changes:
        meta.extend(vencode(i-last-1));meta.extend(vencode(i-j));last=i
    raw=skeleton+meta+len(meta).to_bytes(8,'little')+MAGIC
    return raw, dict(stats, template_mode=mode, functions=len(fields), template_functions=len(changes),
        template_source_bytes=matched, changed_words=changed, template_metadata_bytes=len(meta)+13,
        transformed_bytes=len(raw))


def inverse(raw):
    if len(raw)<15 or raw[-5:]!=MAGIC: raise ValueError('invalid template trailer')
    n=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-n
    if start<0 or n<2: raise ValueError('invalid template metadata')
    meta=raw[start:-13];mode=meta[0]
    if mode not in (0,1,2): raise ValueError('invalid template mode')
    out=bytearray(parent.inverse(raw[:start]));fields=regions(bytes(out))
    count,pos=vdecode(meta,1);last=-1
    if count>len(fields) or (mode==0 and count):raise ValueError('invalid template count')
    for _ in range(count):
        gap,pos=vdecode(meta,pos);back,pos=vdecode(meta,pos);i=last+1+gap;j=i-back
        if not 0<=j<i<len(fields):raise ValueError('template reference is not backward')
        p,n=fields[i];q,m=fields[j]
        if n!=m:raise ValueError('template length mismatch')
        words=struct.unpack_from('<'+'I'*(n//4),out,p);previous=struct.unpack_from('<'+'I'*(n//4),out,q)
        restored=[a^b for a,b in zip(words,previous)] if mode==1 else [(a+b)&0xffffffff for a,b in zip(words,previous)]
        struct.pack_into('<'+'I'*len(restored),out,p,*restored);last=i
    if pos!=len(meta):raise ValueError('unused template metadata')
    return bytes(out)
