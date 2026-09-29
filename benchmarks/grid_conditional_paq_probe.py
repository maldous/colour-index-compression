"""Matched native PAQ controls for coordinate-grouped corrections."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import zlib
from benchmarks import grid_conditional_corrections as codec
from benchmarks import competitive_codec as paq
from cix import multinomial

MAGIC = b'CIXB\x21'
SOURCES = [__file__, codec.__file__, codec.grid.__file__, codec.feedback.__file__,
           codec.bounded.__file__, multinomial.__file__, paq.__file__]


def encode(data, context, options):
    raw, stats = codec.transform(data, context, 0)
    if codec.inverse(raw) != data:
        raise ValueError('grouped transform inversion failed')
    payload = paq.encode_paq(raw, 'v215', options)
    frame = MAGIC + multinomial.vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + payload
    return frame, dict(stats, transformed_sha256=paq.sha(raw))


def decode(frame):
    if frame[:5] != MAGIC:
        raise ValueError('invalid grouped PAQ frame')
    n, pos = multinomial.vdecode(frame, 5)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    data = codec.inverse(paq.decode(frame[pos+4:]))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('grouped PAQ source mismatch')
    return data


def worker(spec):
    off, length, context, options, cpu, output = spec
    os.sched_setaffinity(0, {cpu})
    folder = Path(output)/f'{off}-{context}'
    folder.mkdir(parents=True, exist_ok=False)
    source = Path('benchmark-work/silesia/sao')
    data = source.read_bytes()[off:off+length]
    hashes = {str(Path(p).resolve()): paq.sha(Path(p).read_bytes()) for p in [*SOURCES, paq.paq_binary('v215')]}
    revision = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    start = time.perf_counter()
    frame, stats = encode(data, context, options)
    enc = time.perf_counter()-start
    (folder/'stream.cixb').write_bytes(frame)
    start = time.perf_counter()
    restored = decode((folder/'stream.cixb').read_bytes())
    dec = time.perf_counter()-start
    if restored != data or source.read_bytes()[off:off+length] != data:
        raise ValueError('grouped PAQ restoration failed')
    if any(paq.sha(Path(p).read_bytes()) != h for p,h in hashes.items()):
        raise ValueError('grouped PAQ dependency changed')
    row = dict(stats, options=options, offset=off, original_bytes=len(data), physical_bytes=len(frame),
        round_trip=True, complete_silesia_member=off==0 and len(data)==source.stat().st_size,
        input_sha256=paq.sha(data), restored_sha256=paq.sha(restored), frame_sha256=paq.sha(frame),
        source_hashes=hashes, revision=revision, encode_seconds=enc, decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        completed_at=datetime.now(timezone.utc).isoformat())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ('offset','context','physical_bytes','round_trip')}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--whole',action='store_true')
    p.add_argument('--options',default='-4')
    p.add_argument('--contexts',nargs='+',type=int,default=[0,3])
    p.add_argument('--cpus',nargs='+',type=int,default=[16,18])
    args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    size=Path('benchmark-work/silesia/sao').stat().st_size
    regions=[(0,size)] if args.whole else [(0,131068),(3625972,131068),(7120876,131068)]
    pairs=[(off,n,c) for off,n in regions for c in args.contexts]
    specs=[(*t,args.options,args.cpus[i%len(args.cpus)],str(root)) for i,t in enumerate(pairs)]
    with concurrent.futures.ProcessPoolExecutor(len(args.cpus),max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=not args.whole,rows=rows),indent=2)+'\n')


if __name__=='__main__':
    main()
