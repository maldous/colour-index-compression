"""Quick physical Brotli controls for Alpha call candidate representations."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import resource
import subprocess
import time
import zlib
import brotli
import _brotli
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_calls, ecoff_call_entries, ecoff_probe
from benchmarks.competitive_codec import sha

MAGIC = b'CIXB\x06'


def encode(data, mode, entries=True):
    codec = ecoff_call_entries if entries else ecoff_calls
    raw, stats = codec.transform(data, mode)
    frame = MAGIC + bytes([entries]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + brotli.compress(raw, quality=11, lgwin=24)
    return frame, dict(stats, entries=entries, transformed_sha256=sha(raw))


def decode(frame):
    if len(frame) < 6 or frame[:5] != MAGIC or frame[5] not in (0, 1):
        raise ValueError('invalid call Brotli frame')
    n, pos = vdecode(frame, 6); crc = int.from_bytes(frame[pos:pos + 4], 'big')
    codec = ecoff_call_entries if frame[5] else ecoff_calls
    data = codec.inverse(brotli.decompress(frame[pos + 4:]))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('call Brotli source checksum mismatch')
    return data


def worker(spec):
    offset, length, mode, entries, output = spec; folder = Path(output) / f'{offset}-{int(entries)}-{mode}'
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'stream.cixb').exists():
        raise ValueError('preserve existing call Brotli trial')
    source = Path('benchmark-work/silesia/mozilla'); data = source.read_bytes()[offset:offset + length]
    codec = ecoff_call_entries if entries else ecoff_calls
    paths = [__file__, codec.__file__, codec.parent.__file__, codec.parent.parent.__file__, codec.parent.parent.base.__file__, 'cix/multinomial.py']
    hashes = {str(Path(p)): sha(Path(p).read_bytes()) for p in paths}; binary = sha(Path(_brotli.__file__).read_bytes())
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    start = time.perf_counter(); frame, stats = encode(data, mode, entries); enc = time.perf_counter() - start
    (folder / 'stream.cixb').write_bytes(frame); start = time.perf_counter(); restored = decode((folder / 'stream.cixb').read_bytes()); dec = time.perf_counter() - start
    if restored != data:
        raise ValueError('call Brotli physical stream failed independent restoration')
    for p, value in hashes.items():
        if sha(Path(p).read_bytes()) != value:
            raise ValueError('call Brotli source changed')
    if sha(Path(_brotli.__file__).read_bytes()) != binary:
        raise ValueError('call Brotli backend changed')
    row = dict(stats, offset=offset, backend='brotli11', physical_bytes=len(frame), round_trip=True,
        complete_silesia_member=offset == 0 and len(data) == source.stat().st_size,
        input_sha256=sha(data), restored_sha256=sha(restored), frame_sha256=sha(frame), source_hashes=hashes,
        backend_sha256=binary, brotli_version=brotli.__version__, revision=revision, encode_seconds=enc, decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (folder / 'complete.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps({k: row[k] for k in ('offset', 'entries', 'mode', 'physical_bytes', 'round_trip')}), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--modes', nargs='+', type=int, default=list(range(6))); p.add_argument('--entries', nargs='+', type=int, default=[1])
    p.add_argument('--whole', action='store_true'); p.add_argument('--jobs', type=int, default=2); args = p.parse_args()
    root = Path(args.output).resolve(); root.mkdir(parents=True, exist_ok=True)
    regions = [(0, 51220480)] if args.whole else ecoff_probe.REGIONS
    specs = [(off, n, m, bool(e), str(root)) for off, n in regions for e in args.entries for m in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, specs))
    (root / 'complete.json').write_text(json.dumps(dict(complete=True, diagnostic_only=not args.whole, rows=rows), indent=2) + '\n')


if __name__ == '__main__':
    main()
