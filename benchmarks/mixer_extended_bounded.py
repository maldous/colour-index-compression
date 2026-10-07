"""Experimental CIXR3: fixed 64 KiB blocks, generic mixer banks 0/2/raw."""
import zlib
from cix.multinomial import vencode,vdecode
from benchmarks.rounded_mixer import decode as decode_mixer

MAGIC=b'CIXR\x03'
BLOCK_SIZE=65536
CONTEXT_BITS=(0,2)


def encode(data, *, library="results/leaderboard/native_mixer_rounding.so"):
    from benchmarks.rounded_mixer import native_encoder as encoder
    native=encoder(library)
    from benchmarks.extended_mixer import native_encoder as extended_encoder
    extended=extended_encoder()
    result=bytearray(MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big'))
    for start in range(0,len(data),BLOCK_SIZE):
        block=data[start:start+BLOCK_SIZE]
        best=b'\x00'+block
        for implementation in (native,extended):
            for bits in CONTEXT_BITS:
                candidate=b'\x01'+implementation(block,bits)
                if len(candidate)<len(best):best=candidate
        result.extend(vencode(len(best)));result.extend(best)
    return bytes(result)


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('unknown mixer stream')
    length,pos=vdecode(frame,5)
    if pos+4>len(frame):raise ValueError('truncated checksum')
    checksum=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    result=bytearray()
    while len(result)<length:
        expected=min(BLOCK_SIZE,length-len(result));size,pos=vdecode(frame,pos)
        if not 1<=size<=expected+1 or pos+size>len(frame):raise ValueError('invalid mixer block')
        mode=frame[pos];payload=frame[pos+1:pos+size]
        if mode==0:block=payload
        elif mode==1:
            nested_length,_=vdecode(payload,6)
            if nested_length!=expected:raise ValueError('nested length mismatch')
            if payload[:5]==b'CIXQ\x03':
                from benchmarks.extended_mixer import decode as decode_extended
                block=decode_extended(payload)
            else:block=decode_mixer(payload)
        else:raise ValueError('unknown mixer block mode')
        if len(block)!=expected:raise ValueError('block length mismatch')
        result.extend(block);pos+=size
    if pos!=len(frame) or zlib.crc32(result)!=checksum:raise ValueError('trailing bytes or checksum mismatch')
    return bytes(result)
