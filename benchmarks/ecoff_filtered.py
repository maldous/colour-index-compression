"""Count every byte in CIX structure + PAQ reversible filters + Brotli.

Modes 0/1 share CIX's procedure/symbol representation. Mode 1 adds PAQ's
lossless filters; mode 2 gives the same filters the original source. The
isolated stored-state repair is required only for decoding level-zero PAQ.
This does not claim to use PAQ probabilities or remove uncertainty for free.
"""
from pathlib import Path
import subprocess
import tempfile
import zlib
import brotli
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_pdata_symbols as structure, competitive_codec as native

ROOT = Path(__file__).resolve().parents[1]
FORK = ROOT/'benchmark-work/references/paq8px-cix-store-state/build-local/paq8px'
MAGIC = b'CIXB\x13'


def encode(data, mode=1):
    if mode not in range(3): raise ValueError('invalid filter combination')
    raw, stats = structure.transform(data, 1) if mode != 2 else (data, {})
    structural_hash = native.sha(raw)
    if mode:
        with tempfile.TemporaryDirectory(prefix='cix-stored-filters-') as folder:
            folder=Path(folder); source=folder/'source.bin'; archive=folder/'stream.paq8px216';source.write_bytes(raw)
            subprocess.run([native.paq_binary('v216'),'-0','-simd','AVX2',str(source),str(archive)],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            raw=archive.read_bytes()
    payload=brotli.compress(raw,quality=11,lgwin=24)
    frame=MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return frame,dict(mode=mode,original_bytes=len(data),structural_stats=stats,structural_sha256=structural_hash,
                      backend_input_bytes=len(raw),backend_input_sha256=native.sha(raw))


def decode(frame):
    if len(frame)<11 or frame[:5]!=MAGIC or frame[5] not in range(3): raise ValueError('invalid stored-filter frame')
    mode=frame[5]; length,pos=vdecode(frame,6); checksum=int.from_bytes(frame[pos:pos+4],'big');raw=brotli.decompress(frame[pos+4:])
    if mode:
        with tempfile.TemporaryDirectory(prefix='cix-stored-filters-') as folder:
            folder=Path(folder); archive=folder/'stream.paq8px216';output=folder/'restored.bin';archive.write_bytes(raw)
            subprocess.run([str(FORK),'-d','-simd','AVX2',str(archive),str(output)],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            raw=output.read_bytes()
    data=structure.inverse(raw) if mode!=2 else raw
    if len(data)!=length or zlib.crc32(data)!=checksum: raise ValueError('stored-filter source checksum mismatch')
    return data
