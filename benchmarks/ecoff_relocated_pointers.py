"""Restrict relocated data pointers using transmitted symbol definitions.

Relocation symbol indices identify a small candidate alphabet; definitions in
other objects add candidates without an external dictionary. Every exception is
literal, and all field positions remain fixed for the parent PAQ/Brotli models.
"""
from collections import Counter, defaultdict
import struct
from benchmarks import ecoff_got as parent

MAGIC = b'ECRP1'


def candidates(data, shared=True):
    parsed = parent.objects(data); definitions = defaultdict(Counter)
    if shared:
        for _, _, _, symbols in parsed:
            for name, value in symbols:
                if value: definitions[name][value] += 1
    fields = []
    for off, d, sec, symbols in parsed:
        if b'.rel.dyn' not in sec: continue
        regions = []
        for i in range(struct.unpack_from('<H', d, 2)[0]):
            name, _, virtual, size, pointer, _, _, _, _, _ = struct.unpack_from('<8sQQQQQQHHI', d, 104+i*64)
            if name.rstrip(b'\0') in (b'.rdata', b'.data', b'.sdata') and pointer:
                regions.append((virtual, size, pointer))
        start, size = sec[b'.rel.dyn']; alphabets = {}
        for p in range(start, start+size//16*16, 16):
            address, info, _ = struct.unpack_from('<QII', d, p); symbol = info >> 8
            if info & 255 != 2 or symbol >= len(symbols): continue
            locations = [pointer+address-virtual for virtual, n, pointer in regions if virtual <= address and address+8 <= virtual+n]
            if len(locations) != 1: continue
            if symbol not in alphabets:
                name, value = symbols[symbol]
                rest = sorted(definitions[name], key=lambda v: (-definitions[name][v], v)) if shared else []
                alphabets[symbol] = [value]+[v for v in rest if v != value]
            fields.append((off+locations[0], alphabets[symbol], int(symbols[symbol][1] == 0)))
    fields.sort(key=lambda f:f[0]); blocked=set()
    for i,(a,b) in enumerate(zip(fields, fields[1:])):
        if a[0]+8>b[0]: blocked.update((i,i+1))
    return [f for i,f in enumerate(fields) if i not in blocked]


def transform(data, mode=1, shared=True):
    if mode not in range(6): raise ValueError('invalid relocated-pointer representation')
    fields=candidates(data,shared);out=bytearray(data);flags=bytearray((len(fields)+7)//8) if mode==1 else bytearray()
    digits=[];alphabets=[];contexts=[];exceptions=bytearray();hits=0
    for i,(where,options,context) in enumerate(fields):
        value=struct.unpack_from('<Q',data,where)[0];digit=options.index(value) if value in options else len(options);hits+=digit<len(options)
        if mode==1 and digit<len(options):
            flags[i//8]|=1<<(i%8);struct.pack_into('<Q',out,where,digit)
        elif mode>=2:
            out[where:where+8]=bytes(8);digits.append(digit);alphabets.append(len(options)+1);contexts.append(context)
            if digit==len(options):exceptions.extend(data[where:where+8])
    if mode>=2:choices,uncertainty,model_bits=parent.encode_choices(digits,alphabets,contexts,mode-2)
    else:choices=b'';uncertainty=0.;model_bits=None
    skeleton,_=parent.transform(bytes(out),3)
    metadata=bytes([mode,int(shared)])+parent.pack(bytes(flags))+parent.pack(choices)+bytes(exceptions)
    raw=skeleton+metadata+len(metadata).to_bytes(8,'little')+MAGIC
    return raw,dict(mode=mode,shared=shared,original_bytes=len(data),transformed_bytes=len(raw),mapped_pointers=len(fields),in_candidates=hits,
                    membership_bytes=len(flags),choice_bytes=len(choices),exception_bytes=len(exceptions),candidate_combinatorial_bits=uncertainty,choice_model_bits=model_bits)


def inverse(raw):
    if len(raw)<17 or raw[-5:]!=MAGIC:raise ValueError('invalid relocated-pointer trailer')
    size=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-size
    if start<0 or size<4:raise ValueError('invalid pointer metadata size')
    meta=raw[start:-13];mode,shared=meta[:2]
    if mode not in range(6) or shared not in (0,1):raise ValueError('invalid pointer model')
    data=parent.inverse(raw[:start]);fields=candidates(data,bool(shared));flags,pos=parent.read(meta,2);choices,pos=parent.read(meta,pos)
    if len(flags)!=((len(fields)+7)//8 if mode==1 else 0):raise ValueError('pointer membership length mismatch')
    if mode<2 and choices:raise ValueError('unexpected pointer choices')
    digits=parent.decode_choices(choices,[len(v)+1 for _,v,_ in fields],[c for _,_,c in fields],mode-2) if mode>=2 else []
    out=bytearray(data)
    for i,(where,options,_) in enumerate(fields):
        if mode==1 and flags[i//8] & (1<<(i%8)):
            digit=struct.unpack_from('<Q',out,where)[0]
            if digit>=len(options):raise ValueError('pointer index outside alphabet')
            struct.pack_into('<Q',out,where,options[digit])
        elif mode>=2:
            if any(out[where:where+8]):raise ValueError('pointer skeleton is not zero')
            digit=digits[i]
            if digit==len(options):
                if pos+8>len(meta):raise ValueError('truncated pointer exception')
                out[where:where+8]=meta[pos:pos+8];pos+=8
            else:struct.pack_into('<Q',out,where,options[digit])
    if pos!=len(meta):raise ValueError('unused pointer metadata')
    return bytes(out)
