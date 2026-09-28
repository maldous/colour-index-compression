"""CIXR7 fixed 1 MiB relation tournament, retaining an exact complete R6 stream.

The reference encoder can compute R6 itself. The benchmark cache path must validate
input, policy and physical artifact hashes before supplying an incumbent.
"""
import zlib
from cix.multinomial import vencode,vdecode
from benchmarks.relational_mixer import Native

MAGIC=b'CIXR\x07'
BLOCK_SIZE=1048576
BITS=(0,2)
MODES=(0,1,2)


def encode(data, *, incumbent=None):
    native=Native()
    out=bytearray(MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big'))
    for start in range(0,len(data),BLOCK_SIZE):
        block=data[start:start+BLOCK_SIZE]
        best=b'\0'+block
        for mode in MODES:
            for bits in BITS:
                candidate=native.encode(block,bits,mode)
                if native.decode(candidate)!=block:raise ValueError('candidate round trip failed')
                candidate=b'\1'+candidate
                if len(candidate)<len(best):best=candidate
        out.extend(vencode(len(best)));out.extend(best)
    if incumbent is None:
        from benchmarks.mixer_ppm_large import encode as old_encode
        incumbent=old_encode(data)
    return bytes(out) if len(out)<len(incumbent) else incumbent


def decode(frame):
    if frame[:5] in (b'CIXR\x05', b'CIXR\x06'):
        from benchmarks.legacy_mixer_native import enable
        enable()
        from benchmarks.mixer_ppm_large import decode as old_decode
        return old_decode(frame)
    if frame[:5]!=MAGIC:raise ValueError('unknown relation portfolio')
    length,pos=vdecode(frame,5)
    if pos+4>len(frame):raise ValueError('truncated checksum')
    checksum=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    out=bytearray();native=Native()
    while len(out)<length:
        expected=min(BLOCK_SIZE,length-len(out));size,pos=vdecode(frame,pos)
        if not 1<=size<=expected+1 or pos+size>len(frame):raise ValueError('invalid block')
        mode=frame[pos];payload=frame[pos+1:pos+size]
        if mode==0: block=payload
        elif mode==1: block=native.decode(payload)
        else:raise ValueError('unknown mode')
        if len(block)!=expected:raise ValueError('block length mismatch')
        out.extend(block);pos+=size
    if pos!=len(frame) or zlib.crc32(out)!=checksum:raise ValueError('trailing bytes or checksum mismatch')
    return bytes(out)
