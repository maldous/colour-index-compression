"""Explicit opt-in exact accelerator for positive four-byte hash-chain settings."""
import ctypes
from pathlib import Path


def parser(library='results/leaderboard/native_lz_parse.so'):
    from cix.lz import parse_lz, LZParse
    lib=ctypes.CDLL(str(Path(library).resolve()))
    call=lib.cix_lz_parse
    call.argtypes=[ctypes.c_void_p]+[ctypes.c_uint32]*6+[ctypes.c_int,ctypes.POINTER(ctypes.c_uint32),ctypes.POINTER(ctypes.c_uint32)]
    call.restype=ctypes.c_int
    def encode(data, *, prefix_history=b'',min_match=4,max_match=65535,window=1<<20,chain=32,key_len=4,lazy=False):
        if key_len!=4 or window<=0 or chain<=0 or max_match<4 or max(len(data),len(prefix_history),window,chain,max_match,min_match)>=2**31:
            return parse_lz(data,prefix_history=prefix_history,min_match=min_match,max_match=max_match,window=window,chain=chain,key_len=key_len,lazy=lazy)
        minimum=max(4,min_match);history=prefix_history[-window:];base=history+data
        out=(ctypes.c_uint32*(max(1,len(data))*3))();count=ctypes.c_uint32()
        status=call(base,len(base),len(history),window,chain,minimum,max_match,lazy,out,ctypes.byref(count))
        if status:raise RuntimeError('native LZ parser failure: '+str(status))
        tags=bytearray();literals=bytearray();positions=[];lengths=[];distances=[];offset=0
        for i in range(count.value):
            tag,value,length=out[i*3:i*3+3];tags.append(tag)
            if tag:distances.append(value);lengths.append(length-minimum);offset+=length
            else:literals.append(value);positions.append(offset);offset+=1
        return LZParse(bytes(tags),bytes(literals),positions,lengths,distances)
    return encode
