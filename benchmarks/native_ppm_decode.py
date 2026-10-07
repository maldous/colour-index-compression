"""Opt-in native decoding, preserving the unchanged Python reference decoder."""
import ctypes
from pathlib import Path
from cix.multinomial import vdecode


def load(path='results/leaderboard/native_ppm_decode.so'):
    lib=ctypes.CDLL(str(Path(path).resolve()))
    lib.cix_ppm_decode.argtypes=[ctypes.c_char_p,ctypes.c_size_t,ctypes.c_uint64,
        ctypes.c_char_p,ctypes.c_size_t,ctypes.c_size_t,ctypes.c_uint,ctypes.c_uint,
        ctypes.c_uint,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_size_t)]
    lib.cix_ppm_decode.restype=ctypes.c_int
    lib.cix_ppm_free.argtypes=[ctypes.c_void_p];lib.cix_ppm_free.restype=None

    def decode(blob,*,source_length,prefix_history=b''):
        if (len(blob)<4 or blob[0] not in (3,4,5) or blob[1]>8 or source_length<0
            or source_length>1<<26 or blob[2]>(1 if blob[0]==5 else 3)):
            raise ValueError('invalid PPM header or output size')
        bits,pos=vdecode(blob,3)
        if pos+(bits+7)//8!=len(blob):raise ValueError('PPM payload length mismatch')
        secondary=blob[0]==5;exclusion=bool(blob[2]) if secondary else blob[0]==4
        payload=blob[pos:];result,size=ctypes.c_void_p(),ctypes.c_size_t()
        code=lib.cix_ppm_decode(payload,len(payload),bits,prefix_history,len(prefix_history),
            source_length,blob[1],0 if secondary else blob[2],exclusion,secondary,
            ctypes.byref(result),ctypes.byref(size))
        if code:raise ValueError('native PPM decoding failed')
        try:return ctypes.string_at(result,size.value)
        finally:lib.cix_ppm_free(result)
    return decode


def enable():
    from cix import ppm
    ppm.decode_ppm=load()
