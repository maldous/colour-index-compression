"""Local physical GOT candidate tournaments on explicit small TAR cohorts."""
import argparse
from collections import Counter, defaultdict
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import resource
import struct
import subprocess
import tarfile
import time
import zlib
import brotli
from cix.multinomial import vencode, vdecode
from benchmarks import ecoff_got as codec, competitive_codec as paq

MAGIC = b'CIXB\x03'


def prepare(root):
    """Diagnostic fixture selection only; no offsets/names enter the codec."""
    data = Path('benchmark-work/silesia/mozilla').read_bytes()
    parsed = codec.objects(data); byoffset = {o: d for o, d, _, _ in parsed}; providers = defaultdict(set)
    for off, _, _, symbols in parsed:
        for _, value in symbols:
            if value:
                providers[value].add(off)
    fields = codec.candidates(data); rows = []; root.mkdir(parents=True, exist_ok=True)
    for seed in (4274176, 35383296, 47712256):
        targets = set()
        for where, options, _ in fields:
            if seed <= where < seed + len(byoffset[seed]):
                actual = struct.unpack_from('<Q', data, where)[0]
                if actual != options[0] and actual in options:
                    targets.add(actual)
        chosen = [seed]
        for _ in range(2):
            scores = Counter(o for value in targets for o in providers[value]
                             if o not in chosen and len(byoffset[o]) <= 350000)
            if not scores:
                break
            best = max(scores, key=lambda o: (scores[o] / len(byoffset[o]), scores[o], -o))
            chosen.append(best); targets = {value for value in targets if best not in providers[value]}
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for i, off in enumerate(chosen):
                info = tarfile.TarInfo(f'object-{i}'); info.size = len(byoffset[off])
                archive.addfile(info, io.BytesIO(byoffset[off]))
        blob = stream.getvalue(); path = root / f'{seed}.tar'; path.write_bytes(blob)
        entries = codec.candidates(blob)
        shared = sum(struct.unpack_from('<Q', blob, p)[0] in options for p, options, _ in entries)
        same = sum(struct.unpack_from('<Q', blob, p)[0] == options[0] for p, options, _ in entries)
        rows.append(dict(seed=seed, source_offsets=chosen, input_bytes=len(blob), sha256=paq.sha(blob), path=str(path),
                         mapped_addresses=len(entries), same_object_matches=same, global_matches=shared))
    report = dict(diagnostic_only=True, constructed_subarchives=True, source_sha256=paq.sha(data), rows=rows)
    (root / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def encode(data, mode, backend, options):
    if mode == -2:
        raw, stats = codec.parent.transform(data, 1)
    elif mode == -1:
        raw, stats = data, dict(original_bytes=len(data), transformed_bytes=len(data))
    else:
        raw, stats = codec.transform(data, mode if mode < 4 else 3, mode != 4)
    payload = brotli.compress(raw, quality=11, lgwin=24) if backend == 'brotli' else paq.encode_paq(raw, 'v215', options)
    frame = MAGIC + bytes([mode + 2, int(backend == 'paq')]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + payload
    return frame, dict(stats, mode=mode, transformed_sha256=paq.sha(raw))


def decode(frame):
    if frame[:5] != MAGIC or frame[5] > 6 or frame[6] > 1:
        raise ValueError('invalid framed GOT experiment')
    mode, backend = frame[5] - 2, frame[6]; n, pos = vdecode(frame, 7)
    crc = int.from_bytes(frame[pos:pos + 4], 'big'); payload = frame[pos + 4:]
    raw = paq.decode(payload) if backend else brotli.decompress(payload)
    data = codec.parent.inverse(raw) if mode == -2 else raw if mode == -1 else codec.inverse(raw)
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('GOT source checksum mismatch')
    return data


def worker(spec):
    path, mode, backend, options, output = spec; source = Path(path); data = source.read_bytes()
    folder = Path(output) / f'{source.stem}-{mode}'; folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'stream.cixb').exists():
        raise ValueError('preserve existing GOT trial')
    sources = [__file__, codec.__file__, codec.parent.__file__, codec.parent.base.__file__, paq.__file__, 'cix/multinomial.py']
    hashes = {str(Path(p)): paq.sha(Path(p).read_bytes()) for p in sources}
    binary = paq.sha(Path(paq.paq_binary('v215')).read_bytes()) if backend == 'paq' else None
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    start = time.perf_counter(); frame, stats = encode(data, mode, backend, options); enc = time.perf_counter() - start
    (folder / 'stream.cixb').write_bytes(frame); start = time.perf_counter(); restored = decode((folder / 'stream.cixb').read_bytes()); dec = time.perf_counter() - start
    if restored != data:
        raise ValueError('GOT physical stream failed independent restoration')
    for path, digest in hashes.items():
        if paq.sha(Path(path).read_bytes()) != digest:
            raise ValueError('GOT source changed')
    if binary and paq.sha(Path(paq.paq_binary('v215')).read_bytes()) != binary:
        raise ValueError('GOT backend changed')
    row = dict(stats, input_path=str(source), backend=backend, options=options, physical_bytes=len(frame), round_trip=True,
               complete_silesia_member=False, source_hashes=hashes, backend_sha256=binary, brotli_version=brotli.__version__,
               revision=revision, input_sha256=paq.sha(data), frame_sha256=paq.sha(frame), restored_sha256=paq.sha(restored),
               encode_seconds=enc, decode_seconds=dec, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder / 'complete.json').write_text(json.dumps(row, indent=2) + '\n')
    print(json.dumps({k: row[k] for k in ('input_path', 'mode', 'physical_bytes', 'round_trip', 'encode_seconds')}), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output'); p.add_argument('--prepare')
    p.add_argument('--manifest', default='results/leaderboard/ecoff-got-cohorts/manifest.json')
    p.add_argument('--modes', nargs='+', type=int, default=[-2, -1, 0, 1, 2, 3, 4]); p.add_argument('--backend', choices=['brotli', 'paq'], default='brotli')
    p.add_argument('--options', default='-4'); p.add_argument('--jobs', type=int, default=2); args = p.parse_args()
    if args.prepare:
        print(json.dumps(prepare(Path(args.prepare)), indent=2)); return
    if not args.output:
        p.error('--output is required')
    root = Path(args.output).resolve(); root.mkdir(parents=True, exist_ok=True); manifest = json.loads(Path(args.manifest).read_text())
    for r in manifest['rows']:
        if paq.sha(Path(r['path']).read_bytes()) != r['sha256']:
            raise ValueError('fixture manifest mismatch')
    specs = [(r['path'], m, args.backend, args.options, str(root)) for r in manifest['rows'] for m in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, specs))
    (root / 'complete.json').write_text(json.dumps(dict(complete=True, diagnostic_only=True, fixture=manifest, rows=rows), indent=2) + '\n')


if __name__ == '__main__':
    main()
