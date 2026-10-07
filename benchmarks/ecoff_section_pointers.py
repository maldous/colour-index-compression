"""Section/function alphabets followed by causal pointer-residual prediction.

Section labels and bounds, symbol addresses and pdata function starts are all
transmitted input. Membership flags preserve arbitrary exceptions. Uniform rank
and arithmetic controls receive identical function candidate alphabets.
"""
from math import log2
import struct
from benchmarks import ecoff_pointer_deltas as parent, ecoff_call_entries as uniform

MAGIC=b'ECSP1'
WORD_MASK=(1<<64)-1
CODE_SECTIONS=(b'.text',b'.init',b'.fini')


def fields(data,mode):
    result=[]
    for off,d,sec,symbols in parent.parent.objects(data):
        if b'.rel.dyn' not in sec:continue
        sections={}
        for i in range(struct.unpack_from('<H',d,2)[0]):
            name,_,virtual,size,pointer,_,_,_,_,_=struct.unpack_from('<8sQQQQQQHHI',d,104+64*i)
            if virtual+size<=1<<64:sections[name.rstrip(b'\0')]=(virtual,size,pointer)
        functions={value for _,value in symbols}
        if b'.pdata' in sections:
            virtual,size,pointer=sections[b'.pdata']
            if pointer:
                for p in range(pointer,pointer+size//8*8,8):
                    functions.add((virtual+(struct.unpack_from('<i',d,p)[0]&~3))&WORD_MASK)
        pools={}
        for name,(virtual,size,_) in sections.items():
            if name in CODE_SECTIONS:
                pool=tuple(sorted(v for v in functions if virtual<=v<virtual+size and (v-virtual)%4==0))
                if 0<len(pool)<=65535:pools[name]=pool
        ro,rn=sec[b'.rel.dyn']
        for p in range(ro,ro+rn//16*16,16):
            address,info,_=struct.unpack_from('<QII',d,p);symbol=info>>8
            if info&255!=2 or symbol>=len(symbols):continue
            name,declared=symbols[symbol]
            if name not in sections or (mode in (0,1,2,5,6) and name not in CODE_SECTIONS):continue
            positions=[pointer+address-virtual for label,(virtual,size,pointer) in sections.items()
                       if label in (b'.rdata',b'.data',b'.sdata') and pointer and virtual<=address and address+8<=virtual+size]
            if len(positions)!=1:continue
            virtual,size,_=sections[name];pool=pools.get(name)
            use_functions=mode in (0,1,5,6) or (mode==4 and name in CODE_SECTIONS)
            if use_functions and pool is None:continue
            alphabet=pool if use_functions else (virtual,(size+3)//4)
            if not alphabet or (not use_functions and alphabet[1]==0):continue
            result.append((off+positions[0],declared,use_functions,alphabet))
    result.sort(key=lambda r:r[0]);blocked=set()
    for i,(a,b) in enumerate(zip(result,result[1:])):
        if a[0]+8>b[0]:blocked.update((i,i+1))
    return [r for i,r in enumerate(result) if i not in blocked]


def transform(data,mode=1):
    if mode not in range(7):raise ValueError('invalid section-pointer model')
    descriptors=fields(data,mode);flags=bytearray((len(descriptors)+7)//8) if mode else bytearray();out=bytearray(data)
    indices={}
    for _,_,isfunc,pool in descriptors:
        if isfunc and id(pool) not in indices:indices[id(pool)]={v:i for i,v in enumerate(pool)}
    digits=[];alphabets=[];matches=0;source_bits=0.;restricted_bits=0.
    for i,(where,declared,isfunc,pool) in enumerate(descriptors):
        value=struct.unpack_from('<Q',data,where)[0]
        if isfunc:
            digit=indices[id(pool)].get(value);k=len(pool)
        else:
            virtual,k=pool;digit=(value-virtual)//4 if virtual<=value and (value-virtual)%4==0 and (value-virtual)//4<k else None
        if digit is None:continue
        matches+=1;source_bits+=64;restricted_bits+=log2(k)
        if mode:
            flags[i//8]|=1<<(i%8)
            if mode in (5,6):
                struct.pack_into('<Q',out,where,declared);digits.append(digit);alphabets.append(k)
            else:struct.pack_into('<Q',out,where,(declared+digit)&WORD_MASK)
    if mode==5:choices,_,model_bits=parent.parent.encode_choices(digits,alphabets,[0]*len(digits),1)
    elif mode==6:choices,model_bits=uniform.arithmetic(digits,alphabets,[0]*len(digits),False)
    else:choices=b'';model_bits=None
    skeleton,_=parent.transform(bytes(out),5)
    metadata=bytes([mode])+parent.parent.pack(bytes(flags))+parent.parent.pack(choices)
    raw=skeleton+metadata+len(metadata).to_bytes(8,'little')+MAGIC
    return raw,dict(mode=mode,original_bytes=len(data),transformed_bytes=len(raw),eligible_pointers=len(descriptors),in_candidates=matches,
                    membership_bytes=len(flags),choice_bytes=len(choices),unrestricted_word_bits=source_bits,candidate_combinatorial_bits=restricted_bits,choice_model_bits=model_bits)


def inverse(raw):
    if len(raw)<16 or raw[-5:]!=MAGIC:raise ValueError('invalid section-pointer trailer')
    size=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-size
    if start<0 or size<3:raise ValueError('invalid section-pointer metadata size')
    meta=raw[start:-13];mode=meta[0]
    if mode not in range(7):raise ValueError('invalid section-pointer model')
    flags,pos=parent.parent.read(meta,1);choices,pos=parent.parent.read(meta,pos)
    if pos!=len(meta):raise ValueError('unused section-pointer metadata')
    data=parent.inverse(raw[:start]);descriptors=fields(data,mode)
    if len(flags)!=((len(descriptors)+7)//8 if mode else 0):raise ValueError('section-pointer membership mismatch')
    if mode not in (5,6) and choices:raise ValueError('unexpected section choices')
    alphabets=[len(pool) for i,(_,_,_,pool) in enumerate(descriptors) if mode in (5,6) and flags[i//8]&(1<<(i%8))]
    if mode==5:digits=parent.parent.decode_choices(choices,alphabets,[0]*len(alphabets),1)
    elif mode==6:digits,_=uniform.arithmetic(None,alphabets,[0]*len(alphabets),False,choices)
    else:digits=[]
    out=bytearray(data);event=0
    for i,(where,declared,isfunc,pool) in enumerate(descriptors):
        if not mode or not flags[i//8]&(1<<(i%8)):continue
        encoded=struct.unpack_from('<Q',out,where)[0]
        if mode in (5,6):
            if encoded!=declared:raise ValueError('section-pointer skeleton differs from declared base')
            digit=digits[event];event+=1
        else:digit=(encoded-declared)&WORD_MASK
        if isfunc:
            if digit>=len(pool):raise ValueError('function index outside alphabet')
            value=pool[digit]
        else:
            virtual,k=pool
            if digit>=k:raise ValueError('section index outside interval')
            value=virtual+digit*4
        struct.pack_into('<Q',out,where,value)
    return bytes(out)
