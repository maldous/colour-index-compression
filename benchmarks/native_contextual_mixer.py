"""Opt-in native encoder; decoding remains independent Python."""
import ctypes,zlib
from pathlib import Path
from cix.fixedmix import _STRETCH
from cix.multinomial import vencode
from benchmarks.contextual_mixer import MAGIC


def encoder(library='results/leaderboard/native_contextual_mixer.so'):
    lib=ctypes.CDLL(str(Path(library).resolve()))
    call=lib.cix_fixed_encode
    call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.POINTER(ctypes.c_int32),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_size_t)]
    call.restype=ctypes.c_int
    lib.cix_ppm_free.argtypes=[ctypes.c_void_p]
    table=(ctypes.c_int32*4096)(*_STRETCH)
    def encode(data,bits):
        if bits not in (0,2,4):raise ValueError('unsupported context width')
        pointer=ctypes.c_void_p();size=ctypes.c_size_t()
        status=call(data,len(data),bits,table,ctypes.byref(pointer),ctypes.byref(size))
        if status:raise RuntimeError('native mixer failed')
        try:payload=ctypes.string_at(pointer,size.value)
        finally:lib.cix_ppm_free(pointer)
        return MAGIC+bytes([bits])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return encode
