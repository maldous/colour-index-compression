"""Isolated fixed-generator/count research. No production CIX code."""
import ctypes
import ctypes.util
import hashlib
import json
import lzma
import math
from pathlib import Path
import struct
import sys
import zlib

MASK = (1 << 31)-1
COMB = [[math.comb(n, k) if k <= n else 0 for k in range(32)] for n in range(32)]
LIB = ctypes.CDLL(ctypes.util.find_library('zstd'))
LIB.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
LIB.ZSTD_compressBound.restype = ctypes.c_size_t
LIB.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
LIB.ZSTD_compress.restype = ctypes.c_size_t
LIB.ZSTD_getFrameContentSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
LIB.ZSTD_getFrameContentSize.restype = ctypes.c_ulonglong
LIB.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t]
LIB.ZSTD_decompress.restype = ctypes.c_size_t
LIB.ZSTD_isError.argtypes = [ctypes.c_size_t]
LIB.ZSTD_isError.restype = ctypes.c_uint


def generate(k, a, step):
    return sum(1 << ((a+step*j) % 31) for j in range(k))


PARAMS = {k: {generate(k, a, b): (a, b) for a in range(31) for b in range(1, 16)} for k in range(10, 16)}
DICTIONARY = {k: sorted(p) for k, p in PARAMS.items()}
INDEX = {k: {x: i for i, x in enumerate(xs)} for k, xs in DICTIONARY.items()}
assert all(len(xs) == 465 for xs in DICTIONARY.values())


class Writer:
    def __init__(self):
        self.value = 0
        self.bits = 0
        self.data = bytearray()

    def put(self, value, bits):
        assert 0 <= value < (1 << bits)
        self.value = (self.value << bits) | value
        self.bits += bits
        while self.bits >= 8:
            self.bits -= 8
            self.data.append((self.value >> self.bits) & 255)
        self.value &= (1 << self.bits)-1

    def finish(self):
        if self.bits:
            return bytes(self.data) + bytes([self.value << (8-self.bits)])
        return bytes(self.data)


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.value = 0
        self.bits = 0

    def get(self, bits):
        while self.bits < bits:
            if self.pos >= len(self.data):
                raise ValueError('truncated bitstream')
            self.value = (self.value << 8) | self.data[self.pos]
            self.pos += 1
            self.bits += 8
        self.bits -= bits
        value = self.value >> self.bits
        self.value &= (1 << self.bits)-1
        return value

    def end(self):
        if self.pos != len(self.data) or self.bits >= 8 or self.value:
            raise ValueError('trailing/nonzero padding')


def rank(value):
    r, j = 0, 1
    while value:
        low = value & -value
        r += COMB[low.bit_length()-1][j]
        value ^= low
        j += 1
    return r


def unrank(r, k, n=31):
    if r < 0 or r >= COMB[n][k]:
        raise ValueError('out of range combinatorial index')
    word, pos = 0, n-1
    for j in range(k, 0, -1):
        while COMB[pos][j] > r:
            pos -= 1
        word |= 1 << pos
        r -= COMB[pos][j]
        pos -= 1
    return word


def tokens(data, method):
    inp, out = Reader(data), Writer()
    n, tail = divmod(len(data)*8, 31)
    counts = dict(blocks=n, dense=0, dictionary_hits=0, literals=0, enumerated=0)
    for _ in range(n):
        word = inp.get(31)
        k = word.bit_count()
        colour = int(k > 15)
        minor = word ^ (MASK if colour else 0)
        k = min(k, 31-k)
        counts['dense'] += int(k >= 10)
        hit = k >= 10 and minor in INDEX[k]
        counts['dictionary_hits'] += int(hit)
        width = (COMB[31][k]-1).bit_length()
        use_dict = method in (2, 3) and hit
        use_count = (method == 1 or k < 10) and 5+width < 31
        if use_dict or use_count:
            out.put(1, 1)
            out.put(k, 4)
            out.put(colour, 1)
            if use_dict:
                if method == 2:
                    out.put(INDEX[k][minor], 9)
                else:
                    a, step = PARAMS[k][minor]
                    out.put(a, 5)
                    out.put(step-1, 4)
            else:
                out.put(rank(minor), width)
                counts['enumerated'] += 1
        else:
            out.put(0, 1)
            out.put(word, 31)
            counts['literals'] += 1
    if tail:
        out.put(inp.get(tail), tail)
    inp.end()
    return out.finish(), counts


def untokens(payload, method, size):
    inp, out = Reader(payload), Writer()
    n, tail = divmod(size*8, 31)
    for _ in range(n):
        if not inp.get(1):
            word = inp.get(31)
        else:
            k, colour = inp.get(4), inp.get(1)
            if method in (2, 3) and k >= 10:
                if method == 2:
                    idx = inp.get(9)
                    if idx >= 465:
                        raise ValueError('invalid dictionary index')
                    word = DICTIONARY[k][idx]
                else:
                    a, step = inp.get(5), inp.get(4)+1
                    if a >= 31 or step >= 16:
                        raise ValueError('invalid function parameter')
                    word = generate(k, a, step)
            else:
                word = unrank(inp.get((COMB[31][k]-1).bit_length()), k)
            if colour:
                word ^= MASK
        out.put(word, 31)
    if tail:
        out.put(inp.get(tail), tail)
    inp.end()
    return out.finish()


def zcompress(data):
    bound = LIB.ZSTD_compressBound(len(data))
    out = ctypes.create_string_buffer(bound)
    size = LIB.ZSTD_compress(out, bound, data, len(data), 9)
    if LIB.ZSTD_isError(size):
        raise ValueError('Zstd compression failure')
    return out.raw[:size]


def zdecompress(data, limit):
    size = LIB.ZSTD_getFrameContentSize(data, len(data))
    if size > limit:
        raise ValueError('invalid Zstd payload length')
    out = ctypes.create_string_buffer(max(size, 1))
    got = LIB.ZSTD_decompress(out, size, data, len(data))
    if LIB.ZSTD_isError(got) or got != size:
        raise ValueError('Zstd decompression failure')
    return out.raw[:got]


def frame(data, mode, payload):
    return b'CG31'+struct.pack('>BII', mode, len(data), zlib.crc32(data))+payload


def archives(data):
    out = {0: frame(data, 0, data), 4: frame(data, 4, zcompress(data)),
           8: frame(data, 8, zlib.compress(data, 9)), 9: frame(data, 9, lzma.compress(data, preset=1))}
    stats = {}
    for mode in (1, 2, 3):
        payload, stat = tokens(data, mode)
        out[mode] = frame(data, mode, payload)
        out[mode+4] = frame(data, mode+4, zcompress(payload))
        stats[mode] = stat
    return out, stats


def decode(archive):
    if len(archive) < 13 or archive[:4] != b'CG31':
        raise ValueError('invalid frame')
    mode, size, crc = struct.unpack('>BII', archive[4:13])
    if size > 1048576:
        raise ValueError('research frame size limit')
    payload = archive[13:]
    if mode in (4, 5, 6, 7):
        payload = zdecompress(payload, (size*8//31*32+30+7)//8)
        mode -= 4
    elif mode == 8:
        d = zlib.decompressobj(); payload = d.decompress(payload, size+1)
        if not d.eof or d.unused_data or d.unconsumed_tail:
            raise ValueError('invalid zlib stream')
        mode = 0
    elif mode == 9:
        d = lzma.LZMADecompressor(); payload = d.decompress(payload, max_length=size+1)
        if not d.eof or d.unused_data:
            raise ValueError('invalid xz stream')
        mode = 0
    if mode == 0:
        data = payload
    elif mode in (1, 2, 3):
        data = untokens(payload, mode, size)
    else:
        raise ValueError('unknown method')
    if len(data) != size or zlib.crc32(data) != crc:
        raise ValueError('restoration mismatch')
    return data


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'decode':
        Path(sys.argv[3]).write_bytes(decode(Path(sys.argv[2]).read_bytes()))
    else:
        raise SystemExit('usage: count_dictionary.py decode ARCHIVE OUTPUT')
