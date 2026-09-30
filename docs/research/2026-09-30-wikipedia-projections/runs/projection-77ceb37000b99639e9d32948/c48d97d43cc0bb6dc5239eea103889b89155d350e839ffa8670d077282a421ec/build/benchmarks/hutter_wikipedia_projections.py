"""Fixed, self-contained projection frames for later matched-backend trials.

No compressor is invoked here.  Large inputs require ``pydivsufsort`` for BWT;
the deliberately slow reference fallback is allowed only for small correctness
fixtures and is never selected silently for a moderate experiment.
"""
from __future__ import annotations
from array import array

from cix.bwt import bwt_inverse
from cix.multinomial import vdecode, vencode

MAGIC=b"HWPJ1"
RECIPES={"p1":1,"p2":2,"p3":3}
RECIPE_BY_ID={value:key for key,value in RECIPES.items()}
PYTHON_BWT_MAX=4096

def _have_native_bwt():
    try:
        import pydivsufsort  # type: ignore # noqa:F401
        return True
    except ImportError:return False

def _bwt(data):
    if not data:return 0,b""
    try:
        from pydivsufsort import bw_transform  # type: ignore
    except ImportError:
        if len(data)>PYTHON_BWT_MAX:raise RuntimeError("pydivsufsort is required for BWT projections above 4096 bytes")
        from cix.bwt import _bwt_transform_python
        return _bwt_transform_python(data)
    # Do not route through cix.bwt.bwt_transform: it intentionally catches a
    # native exception and falls back to a quadratic suffix sort, unsuitable
    # for any moderate projection run.
    primary,transformed=bw_transform(data)
    return int(primary),bytes(transformed)

def _ibwt(primary,transformed):
    if not transformed:
        if primary!=0:raise ValueError("invalid empty BWT primary index")
        return b""
    # pydivsufsort 0.0.20 returns a zero byte for its single-symbol inverse;
    # the libdivsufsort BWT convention makes the transformed symbol itself the
    # complete source in this degenerate case.
    if len(transformed)==1:
        if primary!=1:raise ValueError("invalid single-symbol BWT primary index")
        return bytes(transformed)
    try:
        from pydivsufsort import inverse_bw_transform  # type: ignore
    except ImportError:
        if len(transformed)>PYTHON_BWT_MAX:raise RuntimeError("pydivsufsort is required to restore BWT projections above 4096 bytes")
        return bwt_inverse(primary,transformed)
    return bytes(inverse_bw_transform(primary,transformed))

def _pack_planes(values):
    n=len(values); width=(n+7)//8;out=bytearray()
    for bit in range(7,-1,-1):
        plane=bytearray(width)
        for pos,value in enumerate(values): plane[pos//8]|=((value>>bit)&1)<<(7-(pos%8))
        out.extend(plane)
    return bytes(out)

def _planes(blob,n):
    width=(n+7)//8
    if len(blob)!=8*width:raise ValueError("invalid packed bitplane length")
    values=bytearray(n)
    for level,bit in enumerate(range(7,-1,-1)):
        plane=blob[level*width:(level+1)*width]
        for pos in range(n): values[pos]|=((plane[pos//8]>>(7-(pos%8)))&1)<<bit
    return bytes(values)

def _mtf(data):
    order=list(range(256));positions=list(range(256));out=bytearray()
    for value in data:
        rank=positions[value];out.append(rank)
        if rank:
            moved=order[rank]
            for at in range(rank,0,-1):order[at]=order[at-1];positions[order[at]]=at
            order[0]=moved;positions[moved]=0
    return bytes(out)

def _unmtf(ranks):
    order=list(range(256));out=bytearray()
    for rank in ranks:
        value=order[rank];out.append(value)
        if rank:order.pop(rank);order.insert(0,value)
    return bytes(out)

def _p2(data):
    orders=[list(range(256)) for _ in range(257)]; positions=[list(range(256)) for _ in range(257)]; previous=256;out=bytearray()
    for actual in data:
        rank=positions[previous][actual];out.append(rank);order=orders[previous];pos=positions[previous]
        if rank:
            moved=order[rank]
            for at in range(rank,0,-1):order[at]=order[at-1];pos[order[at]]=at
            order[0]=moved;pos[moved]=0
        previous=actual
    return bytes(out)

def _unp2(ranks):
    orders=[list(range(256)) for _ in range(257)];previous=256;out=bytearray()
    for rank in ranks:
        order=orders[previous];actual=order[rank];out.append(actual)
        if rank:order.pop(rank);order.insert(0,actual)
        previous=actual
    return bytes(out)

def _p3(data):
    current=bytes(data);levels=[];zeros=[]
    for bit in range(7,-1,-1):
        bits=bytes((value>>bit)&1 for value in current);zeros.append(bits.count(0));levels.append(_pack_one(bits));current=bytes(value for value,b in zip(current,bits) if not b)+bytes(value for value,b in zip(current,bits) if b)
    return zeros,b"".join(levels)

def _pack_one(bits):
    out=bytearray((len(bits)+7)//8)
    for pos,value in enumerate(bits):out[pos//8]|=value<<(7-(pos%8))
    return bytes(out)

def _unpack_one(blob,n):
    if len(blob)!=(n+7)//8:raise ValueError("invalid wavelet level length")
    return bytes((blob[pos//8]>>(7-(pos%8)))&1 for pos in range(n))

def _unp3(zeros,planes,n):
    width=(n+7)//8
    if len(zeros)!=8 or len(planes)!=8*width:raise ValueError("invalid wavelet payload")
    levels=[]
    for level in range(8):
        bits=_unpack_one(planes[level*width:(level+1)*width],n);zero=zeros[level]
        if not 0<=zero<=n or bits.count(0)!=zero:raise ValueError("wavelet zero count mismatch")
        prefix=array("I",[0])
        for bit in bits:prefix.append(prefix[-1]+bit)
        levels.append((bits,prefix,zero))
    out=bytearray(n)
    for origin in range(n):
        pos=origin;value=0
        for level,(bits,prefix,zero) in enumerate(levels):
            bit=bits[pos];value|=bit<<(7-level)
            pos=(zero+prefix[pos]) if bit else (pos-prefix[pos])
        out[origin]=value
    return bytes(out)

def _frame(recipe,n,primary,payload):return MAGIC+bytes((RECIPES[recipe],))+vencode(n)+vencode(primary)+vencode(len(payload))+payload

def _unframe(frame):
    if not frame.startswith(MAGIC) or len(frame)<=len(MAGIC):raise ValueError("invalid projection magic")
    rid=frame[len(MAGIC)]
    if rid not in RECIPE_BY_ID:raise ValueError("unknown projection recipe")
    n,pos=vdecode(frame,len(MAGIC)+1);primary,pos=vdecode(frame,pos);size,pos=vdecode(frame,pos)
    if pos+size!=len(frame):raise ValueError("projection payload length mismatch")
    recipe=RECIPE_BY_ID[rid]
    if recipe=="p2":
        if primary!=0:raise ValueError("p2 has no BWT primary index")
    elif n==0 and primary!=0:raise ValueError("invalid empty projection primary")
    elif n and not 1<=primary<=n:raise ValueError("invalid projection primary")
    return recipe,n,primary,frame[pos:]

def project(data:bytes,recipe:str)->bytes:
    if recipe not in RECIPES:raise ValueError("unknown projection recipe")
    if recipe=="p1":
        primary,transformed=_bwt(data);payload=_pack_planes(_mtf(transformed))
    elif recipe=="p2":
        primary=0;payload=_pack_planes(_p2(data))
    else:
        primary,transformed=_bwt(data);zeros,planes=_p3(transformed);payload=b"".join(vencode(zero) for zero in zeros)+planes
    return _frame(recipe,len(data),primary,payload)

def restore(frame:bytes)->bytes:
    recipe,n,primary,payload=_unframe(frame);width=(n+7)//8
    if recipe=="p1":
        transformed=_unmtf(_planes(payload,n));return _ibwt(primary,transformed)
    if recipe=="p2":return _unp2(_planes(payload,n))
    pos=0;zeros=[]
    for _ in range(8):
        zero,pos=vdecode(payload,pos);zeros.append(zero)
    if len(payload)-pos!=8*width:raise ValueError("invalid wavelet matrix payload length")
    transformed=_unp3(zeros,payload[pos:],n);return _ibwt(primary,transformed)

DEPENDENCIES={"bwt":"pydivsufsort.bw_transform when installed; cix.bwt reference inverse", "p1":"BWT, MTF, eight MSB-first packed planes", "p2":"257 fixed recency rank lists, eight MSB-first packed planes", "p3":"BWT, eight stable wavelet levels, eight paid zero counts"}
