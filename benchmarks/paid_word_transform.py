"""Input-derived word dictionaries, fully paid inside a reversible CIX frame.

CMIX v21's GPL preprocessor supplies word replacement and its independent
inverse. The stream carries the entire dictionary; the decoder needs no corpus,
external dictionary, training cache or filename-based choice.
"""
from collections import Counter
from pathlib import Path
import re
import subprocess
import tempfile
import zlib
import brotli
from cix.multinomial import vencode, vdecode
from benchmarks import competitive_codec as backend

MAGIC = b'CIXB\x1e'
ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / 'benchmark-work/references/cmix-v21/source/cmix/cmix'
BINARY_SHA256 = 'd4a5566fe3a58b8f8af722800963cbb7f3f88d5be8dbd8ffb579ed482f4fc558'


def binary():
    if backend.sha(BINARY.read_bytes()) != BINARY_SHA256:
        raise ValueError('CMIX preprocessor binary changed')
    return str(BINARY)


def dictionary(data):
    counts = Counter(re.findall(rb'[a-z]{3,}', data.lower()))
    words = sorted((w for w, n in counts.items() if n >= 3), key=lambda w: (-counts[w], w))[:40960]
    return b''.join(w + b'\n' for w in words)


def preprocess(data, words, reverse=False):
    with tempfile.TemporaryDirectory(prefix='cix-cmix-words-') as folder:
        root = Path(folder); source = root / 'source.bin'; out = root / 'output.bin'
        source.write_bytes(data)
        args = [binary(), '-d' if reverse else '-s']
        if words:
            path = root / 'dictionary.txt'; path.write_bytes(words); args.append(str(path))
        subprocess.run([*args, str(source), str(out)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out.read_bytes()


def encode(data, mode=1, entropy='brotli', options='-4'):
    if mode not in (0, 1): raise ValueError('unknown word-transform mode')
    words = dictionary(data) if mode else b''
    transformed = preprocess(data, words) if mode else data
    raw = vencode(len(words)) + words + transformed
    if entropy == 'brotli': payload = brotli.compress(raw,quality=11,lgwin=24); kind=0
    elif entropy == 'paq': payload=backend.encode_paq(raw,'v215',options); kind=1
    else: raise ValueError('unknown entropy backend')
    frame = MAGIC + bytes([mode,kind]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4,'big') + payload
    return frame, dict(mode=mode,entropy=entropy,options=options,dictionary_bytes=len(words),
        transformed_bytes=len(transformed),paid_raw_bytes=len(raw),physical_bytes=len(frame))


def decode(frame):
    if frame[:5]!=MAGIC or len(frame)<7 or frame[5]>1 or frame[6]>1:
        raise ValueError('invalid word-transform frame')
    mode,kind=frame[5:7];n,pos=vdecode(frame,7)
    crc=int.from_bytes(frame[pos:pos+4],'big');payload=frame[pos+4:]
    raw=backend.decode(payload) if kind else brotli.decompress(payload)
    size,pos=vdecode(raw,0)
    if pos+size>len(raw) or (not mode and size): raise ValueError('invalid dictionary frame')
    words=raw[pos:pos+size];transformed=raw[pos+size:]
    data=preprocess(transformed,words,True) if mode else transformed
    if len(data)!=n or zlib.crc32(data)!=crc: raise ValueError('word-transform checksum mismatch')
    return data
