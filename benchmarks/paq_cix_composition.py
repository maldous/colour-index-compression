"""CIXH3: predicted conditional error compositions and packed exact ranks.

The unchanged PAQ model supplies confidence classes. Within each class, fixed
blocks have binomial count priors. Past compositions may refine that prior,
optionally conditioned on the previous composition. The exact count restricts
the arrangement to C(n,k); integer ranks are bit-packed with no byte alignment.
"""
from collections import defaultdict
from functools import lru_cache
import math
import zlib

from cix.multinomial import (vencode,vdecode,_ArithmeticEncoder,_ArithmeticDecoder,
                            _ArithmeticBitWriter,_ArithmeticBitReader)
from benchmarks import paq_cix_residual as base

MAGIC=b'CIXH\x03'
SCALE=1<<20
PRIOR=16


@lru_cache(maxsize=4096)
def binomial_prior(n,bucket,subbits):
    exponent=bucket>>subbits;fine=bucket&((1<<subbits)-1)
    # Midpoint of the logarithmic PAQ error-probability bucket, exactly rational.
    a=(1<<exponent)*((1<<(subbits+1))+2*fine+1)
    d=1<<(32+subbits);a=min(a,d//2)
    divisor=math.gcd(a,d);a//=divisor;d//=divisor;b=d-a
    denominator=d**n;term=b**n;result=[]
    for k in range(n+1):
        result.append(max(1,(term*SCALE)//denominator))
        if k<n:term=term*(n-k)*a//((k+1)*b)
    return tuple(result)


class CompositionModel:
    def __init__(self,subbits,mode):
        self.subbits=subbits;self.mode=mode
        self.hist={};self.previous=defaultdict(int)

    def context(self,n,bucket):
        previous=self.previous[bucket]
        category=previous if previous<4 else previous.bit_length()+1
        return (n,bucket,category if self.mode==2 else 0)

    def frequencies(self,n,bucket):
        prior=binomial_prior(n,bucket,self.subbits)
        if self.mode==0:return prior
        key=self.context(n,bucket);hist=self.hist.get(key)
        if hist is None:return prior
        weights=[PRIOR*p+SCALE*h for p,h in zip(prior,hist)]
        divisor=max(1,(sum(weights)+(1<<24)-1)//(1<<24))
        return tuple(max(1,w//divisor) for w in weights)

    def observe(self,n,bucket,k):
        key=self.context(n,bucket)
        if self.mode:
            hist=self.hist.setdefault(key,[0]*(n+1));hist[k]+=1
            if sum(hist)>2048:
                for i in range(len(hist)):hist[i]=(hist[i]+1)//2
        self.previous[bucket]=k


def put_rank(writer,stream):
    n=len(stream);k=sum(stream);width=(math.comb(n,k)-1).bit_length()
    rank=int.from_bytes(base.rank_binary(stream),'big')
    for shift in range(width-1,-1,-1):writer.write((rank>>shift)&1)
    return width


def take_rank(reader,n,k):
    width=(math.comb(n,k)-1).bit_length()
    if reader.pos+width>reader.bit_length:raise ValueError('truncated packed rank')
    rank=0
    for _ in range(width):rank=(rank<<1)|reader.read()
    return base.unrank_binary(rank.to_bytes((width+7)//8,'big'),n,k)


def encode(trace,paq_archive,source,*,block_size=64,subbits=0,mode=1):
    if block_size not in (16,64,256) or subbits not in range(4) or mode not in (0,1,2):raise ValueError('invalid composition policy')
    if len(paq_archive)<9 or paq_archive[:6]!=b'paq8px':raise ValueError('missing PAQ header')
    groups,stats=base.partition(trace,subbits)
    header_size=9 if paq_archive[7]&32 else 8
    out=bytearray(MAGIC+bytes([subbits,mode,(16,64,256).index(block_size),header_size])+paq_archive[:header_size]
                  +vencode(len(source))+zlib.crc32(source).to_bytes(4,'big'))
    for group in groups:out.extend(vencode(len(group)))
    count_encoder=_ArithmeticEncoder();rank_writer=_ArithmeticBitWriter();model=CompositionModel(subbits,mode)
    count_logloss=0.0;rank_entropy=0.0;blocks=0;forced_events=0
    for bucket,group in enumerate(groups):
        for start in range(0,len(group),block_size):
            block=group[start:start+block_size];n=len(block);k=sum(block);freq=model.frequencies(n,bucket)
            lo=sum(freq[:k]);total=sum(freq);count_encoder.encode(lo,lo+freq[k],total)
            count_logloss+=math.log2(total/freq[k]);model.observe(n,bucket,k)
            cardinality=math.comb(n,k);rank_entropy+=math.log2(cardinality)
            put_rank(rank_writer,block);blocks+=1
            if k in (0,n):forced_events+=n
    counts,count_bits=count_encoder.finish();ranks,rank_bits=rank_writer.finish()
    framing=len(out)
    out.extend(vencode(count_bits));out.extend(counts);out.extend(vencode(rank_bits));out.extend(ranks)
    stats.update(block_size=block_size,subbits=subbits,mode=mode,blocks=blocks,forced_events=forced_events,
        composition_prediction_bits=count_logloss,remaining_combinatorial_bits=rank_entropy,
        count_stream_bytes=len(counts),rank_stream_bytes=len(ranks),rank_bits=rank_bits,
        rank_rounding_bits=rank_bits-rank_entropy,framing_bytes=framing,
        physical_bytes=len(out),baseline_paq_bytes=len(paq_archive),delta_vs_paq_bytes=len(out)-len(paq_archive))
    return bytes(out),stats


def residuals(frame):
    if len(frame)<17 or frame[:5]!=MAGIC:raise ValueError('invalid CIXH3 frame')
    subbits,mode,size_code,header_size=frame[5:9]
    if subbits not in range(4) or mode not in (0,1,2) or size_code not in range(3) or header_size not in (8,9):raise ValueError('invalid composition header')
    block_size=(16,64,256)[size_code];header=frame[9:9+header_size];pos=9+header_size
    if header[:6]!=b'paq8px':raise ValueError('invalid PAQ header')
    original,pos=vdecode(frame,pos)
    if pos+4>len(frame):raise ValueError('missing CRC')
    crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    lengths=[]
    for _ in range(31<<subbits):n,pos=vdecode(frame,pos);lengths.append(n)
    if sum(lengths)>1<<28:raise ValueError('diagnostic stream too large')
    count_bits,pos=vdecode(frame,pos);end=pos+(count_bits+7)//8
    if end>len(frame):raise ValueError('truncated count stream')
    count_decoder=_ArithmeticDecoder(frame[pos:end],count_bits);pos=end
    rank_bits,pos=vdecode(frame,pos);end=pos+(rank_bits+7)//8
    if end!=len(frame):raise ValueError('rank stream length mismatch')
    rank_reader=_ArithmeticBitReader(frame[pos:end],rank_bits);model=CompositionModel(subbits,mode)
    raw=bytearray(b'CIXE1'+bytes([subbits]))
    for bucket,length in enumerate(lengths):
        group=bytearray()
        for start in range(0,length,block_size):
            n=min(block_size,length-start);freq=model.frequencies(n,bucket);total=sum(freq);target=count_decoder.target(total);lo=0
            for k,f in enumerate(freq):
                if target<lo+f:count_decoder.update(lo,lo+f,total);break
                lo+=f
            else:raise ValueError('composition count not found')
            group.extend(take_rank(rank_reader,n,k));model.observe(n,bucket,k)
        raw.extend(length.to_bytes(8,'little'));raw.extend(group)
    if rank_reader.pos!=rank_bits:raise ValueError('unused rank bits')
    return header,bytes(raw),original,crc


def decode(frame):
    # Reuse the frozen independent PAQ replay path without changing its protocol.
    import os,subprocess,tempfile
    from pathlib import Path
    header,raw,original,crc=residuals(frame)
    with tempfile.TemporaryDirectory(prefix='cix-composition-') as folder:
        folder=Path(folder);archive=folder/'input.paq8px215';errors=folder/'errors.bin';output=folder/'restored.bin'
        archive.write_bytes(header+bytes(4));errors.write_bytes(raw)
        env={k:v for k,v in os.environ.items() if k not in ('CIX_TRACE_OUT','CIX_RESIDUAL_IN')};env['CIX_RESIDUAL_IN']=str(errors)
        subprocess.run([str(base.BINARY),'-d','-simd','AVX2',str(archive),str(output)],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        result=output.read_bytes()
    if len(result)!=original or zlib.crc32(result)!=crc:raise ValueError('composition restoration checksum failed')
    return result
