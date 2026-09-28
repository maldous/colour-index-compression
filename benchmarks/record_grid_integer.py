"""Restricted integer intervals and causal correction feedback, exact controls.

Within each block, transmitted bounds constrain every integer. Compare fixed
bits, a joint mixed-radix rank, and uniform arithmetic on that same interval.
Rice and raw fallback candidates retain inexpensive nonuniform representations.
Every choice and every bound is included in the physical stream.
"""
import math
import zlib
from cix.multinomial import vencode,vdecode,_ArithmeticEncoder,_ArithmeticDecoder
from benchmarks import record_float_grid as grid
from benchmarks import record_grid_feedback as feedback

MAGIC=b'CIXI\x01'
RAW=b'SGBI1'


def fold(x):return x*2 if x>=0 else -x*2-1
def unfold(x):return x//2 if not x&1 else -(x//2)-1


def rice(values):
    z=[fold(x) for x in values];estimate=max(0,int(math.log2(sum(z)/len(z)+1))-1)
    k=min(range(max(0,estimate-2),min(31,estimate+2)+1),key=lambda k:sum((x>>k)+1+k if x>>k<32 else 65 for x in z))
    rank=0;bits=0
    for x in z:
        quotient=x>>k
        if quotient<32:width=quotient+1+k;word=(((1<<quotient)-1)<<(k+1))|(x&((1<<k)-1))
        else:width=65;word=((1<<32)-1)<<33|x
        rank=(rank<<width)|word;bits+=width
    return bytes([k])+vencode(bits)+rank.to_bytes((bits+7)//8,'big')


def unrice(blob,n):
    k=blob[0];bits,pos=vdecode(blob,1)
    if k>31 or len(blob)-pos!=(bits+7)//8:raise ValueError('invalid Rice frame')
    rank=int.from_bytes(blob[pos:],'big');remaining=bits;out=[]
    def take(width):
        nonlocal remaining
        if remaining<width:raise ValueError('short Rice payload')
        remaining-=width;return (rank>>remaining)&((1<<width)-1)
    for _ in range(n):
        quotient=0
        while quotient<32 and take(1):quotient+=1
        value=take(33) if quotient==32 else (quotient<<k)|take(k)
        out.append(unfold(value))
    if remaining:raise ValueError('trailing Rice bits')
    return out


def interval(values,policy):
    lo=min(values);span=max(values)-lo+1;digits=[x-lo for x in values];n=len(values)
    header=grid.signed(lo)+vencode(span)
    if policy==1:
        width=(span-1).bit_length();rank=0
        for x in digits:rank=(rank<<width)|x
        return header+rank.to_bytes((width*n+7)//8,'big')
    if policy==2:
        rank=0
        for x in digits:rank=rank*span+x
        return header+rank.to_bytes(((span**n-1).bit_length()+7)//8,'big')
    if span>1<<29:return None
    encoder=_ArithmeticEncoder()
    for x in digits:encoder.encode(x,x+1,span)
    payload,bits=encoder.finish();return header+vencode(bits)+payload


def uninterval(blob,n,policy):
    lo,pos=grid.read_signed(blob,0);span,pos=vdecode(blob,pos)
    if not 1<=span<1<<34:raise ValueError('invalid integer bound')
    if policy==3:
        bits,pos=vdecode(blob,pos)
        if span>1<<29 or len(blob)-pos!=(bits+7)//8:raise ValueError('invalid arithmetic interval')
        decoder=_ArithmeticDecoder(blob[pos:],bits);digits=[]
        for _ in range(n):
            x=decoder.target(span)
            if not 0<=x<span:raise ValueError('integer outside interval')
            digits.append(x);decoder.update(x,x+1,span)
    else:
        width=(span-1).bit_length();length=(width*n+7)//8 if policy==1 else ((span**n-1).bit_length()+7)//8
        if len(blob)-pos!=length:raise ValueError('interval rank length')
        rank=int.from_bytes(blob[pos:],'big');digits=[0]*n
        for i in range(n-1,-1,-1):
            if policy==1:digits[i]=rank&((1<<width)-1);rank>>=width
            else:rank,digits[i]=divmod(rank,span)
        if rank or any(x>=span for x in digits):raise ValueError('rank outside interval')
    return [lo+x for x in digits]


def encode_integers(q,policy=2,block=256):
    if policy not in (1,2,3) or not 1<=block<=4096:raise ValueError('invalid integer policy')
    out=bytearray(vencode(block));choices={};uncertainty=0.0
    for at in range(0,len(q),block):
        values=q[at:at+block];delta=[values[0]]+[b-a for a,b in zip(values,values[1:])]
        candidates=[b'\0'+b''.join(grid.signed(x) for x in values)]
        for is_delta,series in enumerate((values,delta)):
            packed=interval(series,policy)
            if packed is not None:candidates.append(bytes([2*policy-1+is_delta])+packed)
            candidates.append(bytes([7+is_delta])+rice(series))
        winner=min(candidates,key=lambda x:(len(x),x[0]));out.extend(vencode(len(winner)));out.extend(winner)
        choices[winner[0]]=choices.get(winner[0],0)+1
        if winner[0] in (2*policy-1,2*policy):
            series=delta if winner[0]%2==0 else values;uncertainty+=len(series)*math.log2(max(series)-min(series)+1)
    return bytes(out),dict(block=block,choices=choices,selected_interval_uncertainty_bits=uncertainty,integer_bytes=len(out))


def decode_integers(blob,n):
    block,pos=vdecode(blob,0)
    if not 1<=block<=4096:raise ValueError('invalid integer block')
    q=[]
    for at in range(0,n,block):
        size,pos=vdecode(blob,pos);part=blob[pos:pos+size];pos+=size;count=min(block,n-at)
        if not part or len(part)!=size:raise ValueError('truncated integer block')
        kind=part[0];payload=part[1:]
        if kind==0:
            values=[];p=0
            for _ in range(count):x,p=grid.read_signed(payload,p);values.append(x)
            if p!=len(payload):raise ValueError('trailing raw integers')
        elif 1<=kind<=6:values=uninterval(payload,count,(kind+1)//2)
        elif kind in (7,8):values=unrice(payload,count)
        else:raise ValueError('invalid integer representation')
        if kind and kind%2==0:
            for i in range(1,len(values)):values[i]+=values[i-1]
        if any(not -(1<<31)<x<(1<<31) for x in values):raise ValueError('coordinate outside range')
        q.extend(values)
    if pos!=len(blob):raise ValueError('trailing integer stream')
    return q


def transform(data,policy=2,block=256):
    base,_=feedback.transform(data,1,1);inner=base[7:];n,pos=feedback.prefix(inner)
    out=bytearray(RAW+base[5:7]+inner[:pos]);rows=[]
    for start,width,_ in grid.FIELDS:
        field_start=pos;q,_,field_prefix,pos=feedback.read_field(inner,pos,n,width,1)
        integers,stats=encode_integers(q,policy,block)
        out.extend(field_prefix[:8]);out.extend(vencode(len(integers)));out.extend(integers)
        out.extend(inner[field_start+len(field_prefix):pos]);rows.append(dict(offset=start,**stats))
    return bytes(out),dict(policy=policy,block=block,records=n,original_bytes=len(data),transformed_bytes=len(out),fields=rows)


def inverse(blob):
    if blob[:5]!=RAW or blob[5:7]!=b'\x01\x01':raise ValueError('invalid bounded-grid transform')
    inner=blob[7:];n,pos=feedback.prefix(inner);out=bytearray(feedback.RAW+blob[5:7]+inner[:pos])
    for _,width,_ in grid.FIELDS:
        scale=inner[pos:pos+8];pos+=8;size,pos=vdecode(inner,pos);q=decode_integers(inner[pos:pos+size],n);pos+=size
        qbytes=b''.join(grid.signed(x-(q[i-1] if i else 0)) for i,x in enumerate(q))
        field_prefix=scale+vencode(len(qbytes))+qbytes
        # Parse the remaining correction field using a temporary ordinary prefix.
        temporary=field_prefix+inner[pos:];_,_,_,used=feedback.read_field(temporary,0,n,width,1)
        rest=used-len(field_prefix);out.extend(field_prefix);out.extend(inner[pos:pos+rest]);pos+=rest
    if pos!=len(inner):raise ValueError('trailing bounded-grid fields')
    return feedback.inverse(bytes(out))


def encode(data,policy=2,block=256):
    import brotli
    raw,stats=transform(data,policy,block)
    frame=MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+brotli.compress(raw,quality=11)
    return frame,dict(**stats,physical_bytes=len(frame))


def decode(frame):
    import brotli
    if frame[:5]!=MAGIC:raise ValueError('invalid bounded-grid frame')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4;data=inverse(brotli.decompress(frame[pos:]))
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('bounded-grid checksum mismatch')
    return data
