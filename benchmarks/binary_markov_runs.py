"""Exact binary Markov classes through alternating positive run compositions.

Given n, the number of ones, the first bit and the number of runs, every valid
sequence corresponds to one positive composition for zero runs and one for one
runs. Their joint cardinality is C(n0-1,r0-1)*C(n1-1,r1-1). This is the binary
specialization of the valid-trail constraint, without repeated determinants.
"""
from itertools import groupby
import math
from cix.multinomial import vencode,vdecode
from benchmarks import paq_cix_residual as binary


def space(total,runs):
    if runs==0:
        if total:return 0
        return 1
    return math.comb(total-1,runs-1) if total>=runs else 0


def separators(lengths):
    if not lengths:return b''
    return b'\1'.join(b'\0'*(length-1) for length in lengths)


def lengths_from(bits,total,runs):
    if not runs:
        if total or bits:raise ValueError('invalid absent binary run class')
        return []
    values=[len(piece)+1 for piece in bits.split(b'\1')]
    if len(values)!=runs or sum(values)!=total:raise ValueError('invalid positive run composition')
    return values


def encode_group(stream,method=0):
    if method not in (0,1) or not stream or any(value>1 for value in stream):raise ValueError('invalid binary Markov input')
    groups=[[],[]]
    for value,run in groupby(stream):groups[value].append(sum(1 for _ in run))
    n=len(stream);ones=sum(stream);start=stream[0];runs=sum(map(len,groups));totals=[n-ones,ones]
    possibilities=[space(total,len(lengths)) for total,lengths in zip(totals,groups)]
    streams=[separators(lengths) for lengths in groups]
    header=vencode(ones)+vencode(2*runs+start)
    if method==0:
        ranks=[int.from_bytes(binary.rank_binary(bits),'big') for bits in streams]
        count=possibilities[0]*possibilities[1];rank=ranks[0]+possibilities[0]*ranks[1]
        width=(count-1).bit_length();payload=rank.to_bytes((width+7)//8,'big')
    else:payload=b''.join(binary.arith_binary(bits) for bits in streams)
    return header+payload,dict(events=n,errors=ones,runs=runs,first=start,valid_space_bits=math.log2(math.prod(possibilities)),
                              zero_order_space_bits=math.log2(math.comb(n,ones)),physical_group_bytes=len(header)+len(payload),method=method)


def decode_group(blob,pos,n,method=0):
    if not 0<n<=1<<28 or method not in (0,1):raise ValueError('invalid binary Markov group size/method')
    ones,pos=vdecode(blob,pos);token,pos=vdecode(blob,pos);runs,start=divmod(token,2)
    if ones>n or not 1<=runs<=n:raise ValueError('invalid binary run counts')
    run_counts=[runs//2,runs//2];run_counts[start]+=runs&1;totals=[n-ones,ones]
    possibilities=[space(total,count) for total,count in zip(totals,run_counts)]
    if not all(possibilities):raise ValueError('impossible binary Markov class')
    streams=[]
    if method==0:
        count=possibilities[0]*possibilities[1];size=((count-1).bit_length()+7)//8
        if pos+size>len(blob):raise ValueError('truncated binary Markov rank')
        rank=int.from_bytes(blob[pos:pos+size],'big');pos+=size
        if rank>=count:raise ValueError('binary Markov rank outside class')
        for total,number,possibility in zip(totals,run_counts,possibilities):
            digit=rank%possibility;rank//=possibility;width=(possibility-1).bit_length()
            streams.append(binary.unrank_binary(digit.to_bytes((width+7)//8,'big'),max(0,total-1),max(0,number-1)))
    else:
        for total,number in zip(totals,run_counts):
            bits,pos=binary.unarith_binary(blob,pos,max(0,total-1),max(0,number-1));streams.append(bits)
    lengths=[lengths_from(bits,total,number) for bits,total,number in zip(streams,totals,run_counts)]
    cursors=[0,0];out=bytearray();value=start
    for _ in range(runs):
        out.extend(bytes([value])*lengths[value][cursors[value]]);cursors[value]+=1;value^=1
    return bytes(out),pos
