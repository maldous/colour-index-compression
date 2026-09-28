"""CIXW1: PAQ match candidates eliminate prefixes; rank only the exceptions.

For a predicted match byte, token j=0..7 identifies the first differing bit;
j=8 means the entire byte is known. The prefix and first differing bit are then
forced. Unresolved suffix bits retain the exact original PAQ probabilities.
"""
import math
import os
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from cix.multinomial import (vencode,vdecode,multinomial_cardinality,permutation_rank,
    permutation_unrank,_range_encode_type_sequence,_range_decode_type_sequence,
    _ArithmeticEncoder,_ArithmeticDecoder,_composition_rank,_composition_unrank)

ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'benchmark-work/references/paq8px-cix-match/build-local/paq8px'
MAGIC=b'CIXW\x01'


def groups_from_records(records):
    if records[:5]!=b'CIXJ1' or (len(records)-5)%6:raise ValueError('invalid match records')
    groups=[bytearray() for _ in range(4)];events=[];previous=-1
    for position,group,token in struct.iter_unpack('<IBB',records[5:]):
        if position<=previous or group>=4 or token>8:raise ValueError('invalid match record')
        previous=position;groups[group].append(token);events.append((position,group,token))
    return list(map(bytes,groups)),events


def counts_of(stream):
    counts=[0]*9
    for symbol in stream:
        if symbol>8:raise ValueError('match token outside alphabet')
        counts[symbol]+=1
    return counts


def encode_counts(counts):
    active=[i for i,c in enumerate(counts) if c];n=sum(counts)
    if not active:return b'\0'
    mask=sum(1<<i for i in active);parts=[counts[i] for i in active]
    direct=b'\0'+b''.join(vencode(c) for c in parts[:-1])
    width=(math.comb(n-1,len(parts)-1)-1).bit_length()
    ranked=b'\1'+_composition_rank(parts).to_bytes((width+7)//8,'big')
    return vencode(mask)+min((direct,ranked),key=len)


def decode_counts(blob,pos,n):
    mask,pos=vdecode(blob,pos)
    if not 0<mask<512:raise ValueError('invalid match alphabet')
    active=[i for i in range(9) if mask&(1<<i)]
    if len(active)>n or pos>=len(blob):raise ValueError('invalid match count framing')
    mode=blob[pos];pos+=1
    if mode==0:
        parts=[]
        for _ in active[:-1]:value,pos=vdecode(blob,pos);parts.append(value)
        parts.append(n-sum(parts))
    elif mode==1:
        width=(math.comb(n-1,len(active)-1)-1).bit_length();size=(width+7)//8
        if pos+size>len(blob):raise ValueError('truncated match counts')
        rank=int.from_bytes(blob[pos:pos+size],'big');pos+=size
        parts=_composition_unrank(rank,n,len(active))
    else:raise ValueError('unknown count representation')
    if any(c<=0 for c in parts) or sum(parts)!=n:raise ValueError('invalid composition')
    counts=[0]*9
    for symbol,count in zip(active,parts):counts[symbol]=count
    return counts,pos


def adaptive_encode(stream):
    counts=[1]*9;coder=_ArithmeticEncoder()
    for symbol in stream:
        lo=sum(counts[:symbol]);coder.encode(lo,lo+counts[symbol],sum(counts));counts[symbol]+=1
        if sum(counts)>4096:counts=[(c+1)//2 for c in counts]
    return coder.finish()


def adaptive_decode(payload,bits,n):
    counts=[1]*9;coder=_ArithmeticDecoder(payload,bits);out=bytearray()
    for _ in range(n):
        total=sum(counts);target=coder.target(total);lo=0
        for symbol,count in enumerate(counts):
            if target<lo+count:coder.update(lo,lo+count,total);break
            lo+=count
        else:raise ValueError('adaptive match token outside alphabet')
        out.append(symbol);counts[symbol]+=1
        if sum(counts)>4096:counts=[(c+1)//2 for c in counts]
    return bytes(out)


def encode(source,filtered_archive,records,method=0):
    if method not in (0,1,2) or filtered_archive[:6]!=b'paq8px':raise ValueError('invalid match encoding inputs')
    groups,events=groups_from_records(records)
    out=bytearray(MAGIC+bytes([method])+vencode(len(source))+zlib.crc32(source).to_bytes(4,'big')
                  +vencode(len(filtered_archive))+filtered_archive)
    token_entropy=0.0;token_bytes=0;metadata_bytes=0
    for group in groups:
        out.extend(vencode(len(group)));metadata_bytes+=len(vencode(len(group)))
        if not group:continue
        counts=counts_of(group);cardinality=multinomial_cardinality(counts);token_entropy+=math.log2(cardinality)
        if method in (0,1):
            meta=encode_counts(counts);out.extend(meta);metadata_bytes+=len(meta)
        if method==0:
            width=(cardinality-1).bit_length();payload=permutation_rank(group,counts).to_bytes((width+7)//8,'big')
        else:
            payload,bits=_range_encode_type_sequence(group,counts) if method==1 else adaptive_encode(group)
            payload=vencode(bits)+payload
        out.extend(payload);token_bytes+=len(payload)
    return bytes(out),dict(method=method,physical_bytes=len(out),filtered_paq_bytes=len(filtered_archive),
        predicted_bytes=len(events),exact_matches=sum(t==8 for _,_,t in events),
        eliminated_bit_decisions=sum(min(8,t+1) for _,_,t in events),
        residual_token_combinatorial_bits=token_entropy,token_payload_bytes=token_bytes,
        token_metadata_bytes=metadata_bytes,groups=[len(g) for g in groups])


def components(frame):
    if len(frame)<12 or frame[:5]!=MAGIC or frame[5] not in (0,1,2):raise ValueError('invalid match frame')
    method=frame[5];original,pos=vdecode(frame,6)
    if pos+4>len(frame):raise ValueError('missing source checksum')
    crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4;size,pos=vdecode(frame,pos)
    if pos+size>len(frame):raise ValueError('truncated filtered PAQ stream')
    paq=frame[pos:pos+size];pos+=size
    if paq[:6]!=b'paq8px':raise ValueError('invalid filtered PAQ header')
    raw=bytearray(b'CIXM1')
    for _ in range(4):
        n,pos=vdecode(frame,pos)
        if n>1<<27:raise ValueError('oversized diagnostic token stream')
        if not n:stream=b''
        else:
            if method in (0,1):counts,pos=decode_counts(frame,pos,n)
            if method==0:
                width=(multinomial_cardinality(counts)-1).bit_length();size=(width+7)//8
                if pos+size>len(frame):raise ValueError('truncated token rank')
                stream=permutation_unrank(int.from_bytes(frame[pos:pos+size],'big'),counts);pos+=size
            else:
                bits,pos=vdecode(frame,pos);size=(bits+7)//8
                if pos+size>len(frame):raise ValueError('truncated token arithmetic stream')
                payload=frame[pos:pos+size];pos+=size
                stream=_range_decode_type_sequence(payload,bits,counts) if method==1 else adaptive_decode(payload,bits,n)
        raw.extend(n.to_bytes(8,'little'));raw.extend(stream)
    if pos!=len(frame):raise ValueError('trailing match data')
    return paq,bytes(raw),original,crc


def decode(frame):
    paq,raw,original,crc=components(frame)
    with tempfile.TemporaryDirectory(prefix='cix-match-') as folder:
        folder=Path(folder);archive=folder/'input.paq8px215';tokens=folder/'tokens.bin';output=folder/'restored.bin'
        archive.write_bytes(paq);tokens.write_bytes(raw)
        env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_MATCH_ENCODE','CIX_MATCH_DECODE')}
        env['CIX_MATCH_DECODE']=str(tokens)
        subprocess.run([str(BINARY),'-d','-simd','AVX2',str(archive),str(output)],check=True,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        restored=output.read_bytes()
    if len(restored)!=original or zlib.crc32(restored)!=crc:raise ValueError('match reconstruction checksum mismatch')
    return restored
