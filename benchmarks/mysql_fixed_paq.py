"""Test whether inferred field widths and alphabet occupancy help PAQ together."""
import argparse
import concurrent.futures
import json
import resource
import subprocess
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode, vdecode
from benchmarks import mysql_fixed_columns as fixed, mysql_record_constraints as records
from benchmarks import competitive_codec as backend

MAGIC = b'CIXD\x03'


def encode(data, mode=1, options='-4'):
    raw, stats = fixed.transform(data, mode)
    payload = backend.encode_paq(raw, 'v215', options)
    frame = MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4, 'big')+payload
    return frame, dict(**stats, physical_bytes=len(frame), transformed_sha256=backend.sha(raw))


def decode(frame):
    if frame[:5] != MAGIC:
        raise ValueError('invalid fixed-column PAQ frame')
    n, pos = vdecode(frame, 5)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    data = fixed.inverse(backend.decode(frame[pos+4:]))
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('fixed-column PAQ source checksum mismatch')
    return data


def worker(spec):
    mode, offset, length, options, output = spec
    folder = Path(output)/f'{offset}-{mode}'
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/'stream.cixd').exists():
        raise ValueError('preserve existing physical experiment')
    source = Path('benchmark-work/silesia/osdb')
    data = source.read_bytes()[offset:offset+length]
    paths = [__file__, fixed.__file__, records.__file__, backend.__file__,
             'cix/multinomial.py', 'benchmarks/record_float_grid.py']
    hashes = {str(Path(p)): backend.sha(Path(p).read_bytes()) for p in paths}
    binary_hash = backend.sha(Path(backend.paq_binary('v215')).read_bytes())
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    t = time.perf_counter()
    frame, stats = encode(data, mode, options)
    enc = time.perf_counter()-t
    (folder/'stream.cixd').write_bytes(frame)
    t = time.perf_counter()
    restored = decode((folder/'stream.cixd').read_bytes())
    dec = time.perf_counter()-t
    if restored != data:
        raise ValueError('fixed-column PAQ independent restoration failed')
    for path, digest in hashes.items():
        if backend.sha(Path(path).read_bytes()) != digest:
            raise ValueError('source changed during fixed-column experiment')
    if backend.sha(Path(backend.paq_binary('v215')).read_bytes()) != binary_hash:
        raise ValueError('backend changed during experiment')
    row = dict(**stats, file='osdb', offset=offset, options=options,
        complete_silesia_member=offset == 0 and len(data) == source.stat().st_size,
        round_trip=True, input_sha256=backend.sha(data), frame_sha256=backend.sha(frame),
        restored_sha256=backend.sha(restored), source_hashes=hashes,
        backend_sha256=binary_hash, revision=revision, encode_seconds=enc, decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row, indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ['mode','offset','physical_bytes','round_trip','encode_seconds','decode_seconds']}), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--modes', type=int, nargs='+', default=[1,2,3])
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--bytes', type=int, default=65536)
    p.add_argument('--options', default='-4')
    p.add_argument('--jobs', type=int, default=2)
    args = p.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    specs = [(mode,args.offset,args.bytes,args.options,str(root)) for mode in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__ == '__main__':
    main()
