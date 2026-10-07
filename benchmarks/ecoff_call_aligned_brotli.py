"""Full physical Brotli controls for aligned function-constrained call indices."""
import argparse
import concurrent.futures
import json
import resource
import subprocess
import time
import zlib
from pathlib import Path
import brotli
import _brotli
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_call_aligned as codec
from benchmarks.competitive_codec import sha

MAGIC = b'CIXB\x08'


def encode(data, mode):
    raw, stats = codec.transform(data, mode)
    frame = MAGIC + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + brotli.compress(raw, quality=11, lgwin=24)
    return frame, dict(stats, transformed_sha256=sha(raw))


def decode(frame):
    if frame[:5] != MAGIC: raise ValueError('invalid aligned-call Brotli frame')
    n, pos = vdecode(frame, 5); crc = int.from_bytes(frame[pos:pos+4], 'big')
    data = codec.inverse(brotli.decompress(frame[pos+4:]))
    if len(data) != n or zlib.crc32(data) != crc: raise ValueError('aligned-call checksum mismatch')
    return data


def worker(spec):
    mode, output = spec; folder = Path(output)/str(mode); folder.mkdir(parents=True, exist_ok=True)
    if (folder/'stream.cixb').exists(): raise ValueError('preserve existing trial')
    data = Path('benchmark-work/silesia/mozilla').read_bytes()
    paths = [__file__, codec.__file__, codec.parent.__file__, codec.parent.parent.__file__, codec.parent.parent.base.__file__, 'cix/multinomial.py', _brotli.__file__]
    hashes = {str(Path(p)): sha(Path(p).read_bytes()) for p in paths}; revision = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    t = time.perf_counter(); frame, stats = encode(data, mode); enc = time.perf_counter()-t
    (folder/'stream.cixb').write_bytes(frame); t = time.perf_counter(); restored = decode((folder/'stream.cixb').read_bytes()); dec = time.perf_counter()-t
    if data != restored: raise ValueError('full restoration failed')
    if any(sha(Path(p).read_bytes()) != h for p,h in hashes.items()): raise ValueError('experiment dependencies changed')
    row = dict(stats, physical_bytes=len(frame), round_trip=True, complete_silesia_member=True,
               input_sha256=sha(data), restored_sha256=sha(restored), frame_sha256=sha(frame), source_hashes=hashes,
               backend='brotli11', brotli_version=brotli.__version__, revision=revision,
               encode_seconds=enc, decode_seconds=dec, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n'); print(json.dumps({k:row[k] for k in ['mode','physical_bytes','round_trip']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=2);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(m,str(root)) for m in (0,1)]))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=False,rows=rows),indent=2)+'\n')


if __name__ == '__main__': main()
