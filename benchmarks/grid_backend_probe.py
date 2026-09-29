"""Matched physical grid/feedback/rank/arithmetic controls with PAQ or Brotli.

This separate frame leaves qualified and running codecs frozen. Modes two,
three and four receive identical bounded coordinate information; only their
integer representation differs. Full dictionary/framing/checksum costs count.
"""
import argparse
import concurrent.futures
import datetime
import json
from pathlib import Path
import resource
import subprocess
import time
import zlib

import brotli
import _brotli
import numpy
from cix import multinomial
from benchmarks import competitive_codec as paq
from benchmarks import record_grid_integer as bounded
from benchmarks import record_grid_feedback as feedback
from benchmarks import record_float_grid as grid

MAGIC = b'CIXB\x1e'
SOURCES = [__file__, paq.__file__, bounded.__file__, feedback.__file__,
           grid.__file__, multinomial.__file__, _brotli.__file__]


def transform(data, mode):
    if mode == 0:
        return data, dict(control='untransformed source')
    if mode == 1:
        return feedback.transform(data, 1, 1)
    if mode in (2, 3, 4):
        return bounded.transform(data, {2: 2, 3: 3, 4: 1}[mode], 4096)
    raise ValueError('invalid grid mode')


def inverse(raw, mode):
    if mode == 0:
        return raw
    if mode == 1:
        return feedback.inverse(raw)
    if mode in (2, 3, 4):
        return bounded.inverse(raw)
    raise ValueError('invalid grid mode')


def encode(data, mode, backend, options='-4'):
    raw, stats = transform(data, mode)
    if inverse(raw, mode) != data:
        raise ValueError('transform inversion failed')
    if backend == 0:
        payload = brotli.compress(raw, quality=11)
    elif backend == 1:
        payload = paq.encode_paq(raw, 'v215', options)
    else:
        raise ValueError('invalid backend')
    frame = (MAGIC + bytes([mode, backend]) + multinomial.vencode(len(data))
             + zlib.crc32(data).to_bytes(4, 'big') + payload)
    return frame, dict(stats, transformed_bytes=len(raw), transformed_sha256=paq.sha(raw))


def decode(frame):
    if frame[:5] != MAGIC or len(frame) < 8:
        raise ValueError('invalid grid backend frame')
    mode, backend = frame[5:7]
    n, pos = multinomial.vdecode(frame, 7)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    payload = frame[pos+4:]
    if backend == 0:
        raw = brotli.decompress(payload)
    elif backend == 1:
        raw = paq.decode(payload)
    else:
        raise ValueError('invalid backend')
    data = inverse(raw, mode)
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('grid backend restoration mismatch')
    return data


def worker(spec):
    offset, length, mode, backend, options, output = spec
    folder = Path(output) / f'{offset}-{mode}-{backend}'
    folder.mkdir(parents=True, exist_ok=False)
    source = Path('benchmark-work/silesia/sao')
    data = source.read_bytes()[offset:offset+length]
    paths = [*SOURCES, paq.paq_binary('v215')]
    hashes = {str(Path(p).resolve()): paq.sha(Path(p).read_bytes()) for p in paths}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    def status(phase):
        (folder/'status.json').write_text(json.dumps(dict(phase=phase,
            at=datetime.datetime.now(datetime.timezone.utc).isoformat()))+'\n')
    status('encode')
    start = time.perf_counter()
    frame, stats = encode(data, mode, backend, options)
    enc = time.perf_counter()-start
    (folder/'stream.cixb').write_bytes(frame)
    status('decode')
    start = time.perf_counter()
    restored = decode((folder/'stream.cixb').read_bytes())
    dec = time.perf_counter()-start
    if restored != data or source.read_bytes()[offset:offset+length] != data:
        raise ValueError('full source restoration failed')
    if any(paq.sha(Path(p).read_bytes()) != digest for p, digest in hashes.items()):
        raise ValueError('experiment dependencies changed')
    row = dict(stats, mode=mode, backend=backend, options=options,
        file='sao', offset=offset, original_bytes=len(data),
        complete_silesia_member=offset == 0 and len(data) == source.stat().st_size,
        physical_bytes=len(frame), round_trip=True, input_sha256=paq.sha(data),
        restored_sha256=paq.sha(restored), frame_sha256=paq.sha(frame),
        source_hashes=hashes, revision=revision, encode_seconds=enc, decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        numpy_version=numpy.__version__, brotli_version=brotli.__version__,
        completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (folder/'complete.json').write_text(json.dumps(row, indent=2)+'\n')
    status('complete')
    print(json.dumps({k:row[k] for k in ('offset','mode','backend','physical_bytes','round_trip')}), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--whole', action='store_true')
    p.add_argument('--options', default='-4')
    p.add_argument('--pairs', nargs='+', default=['0:1','1:1','2:1','3:1','4:1','2:0'])
    args = p.parse_args()
    size = Path('benchmark-work/silesia/sao').stat().st_size
    regions = [(0, size)] if args.whole else [(0, 131068), ((size//2//28)*28, 131068), (((size-131068)//28)*28, 131068)]
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    specs = [(off, n, *map(int, pair.split(':')), args.options, str(root))
             for off, n in regions for pair in args.pairs]
    with concurrent.futures.ProcessPoolExecutor(args.jobs, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,
        diagnostic_only=not args.whole, rows=rows), indent=2)+'\n')


if __name__ == '__main__':
    main()
