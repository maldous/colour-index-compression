#!/usr/bin/env python3
"""Finite research closure adapter; no production integration."""
import gzip
import hashlib
import json
import lzma
import resource
import runpy
import struct
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/research/2026-10-04-native-rc'
D = runpy.run_path(str(BASE/'codec-decision-prediction-v2/dcp2_completion.py'), run_name='dcp')
C = runpy.run_path(str(BASE/'codec-transfer-v1/transfer.py'), run_name='ctr')
LEVELS = [1, 6, 9]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def timed(fn):
    w, c = time.perf_counter(), time.process_time()
    v = fn()
    return v, {'wall_s': time.perf_counter()-w, 'cpu_s': time.process_time()-c}


def replace_plaintext_coder(dcp, p, preset):
    q = 5 + dcp[4]
    orig, hn, xn = struct.unpack_from('<QII', dcp, q)
    xp = lzma.compress(p, preset=preset)
    return dcp[:q] + struct.pack('<QII', orig, hn, len(xp)) + xp + dcp[q+16+xn:]


def gzip_encode(source, level_id, preset):
    p = gzip.decompress(source)
    x = D['parse'](source)
    ref = D['parse_raw'](D['raw_deflate'](p, LEVELS[level_id]))
    cor = D['corrections_fixed'](x, ref)
    dcp = replace_plaintext_coder(D['pack'](x, p, cor), p, preset)
    counts = {str(i): sum(q[0] == i for seq in cor for q in seq) for i in range(4)}
    return b'GCR1' + bytes([level_id, preset]) + lzma.compress(dcp, preset=1), counts


def gzip_decode(archive):
    level_id, preset = archive[4:6]
    if level_id >= len(LEVELS) or preset not in [1, 6]:
        raise ValueError('unsupported recipe')
    x, plain, corr = D['unpack'](lzma.decompress(archive[6:]))
    ref = D['parse_raw'](D['raw_deflate'](plain, LEVELS[level_id]))
    rm = D['token_map'](ref)
    off, ci = 0, 0
    for b in x['blocks']:
        if b['type'] == 0:
            off += len(b['raw'])
            continue
        tokens = []
        for q in corr[ci]:
            if q[0] == 3:
                tokens.append((2,))
                continue
            if q[0] == 0:
                t = rm[off]
            elif q[0] == 1:
                t = (0, plain[off])
            elif q[0] == 2:
                t = (1, *q[1:])
            else:
                raise ValueError('bad correction')
            tokens.append(t)
            off += D['token_len'](t)
        if not tokens or tokens[-1] != (2,):
            raise ValueError('missing end of block')
        b['tokens'] = tokens
        ci += 1
    original = D['rebuild'](x)
    if len(original) != x['origlen'] or gzip.decompress(original) != plain:
        raise ValueError('gzip reconstruction mismatch')
    return original


def decode(archive):
    return gzip_decode(archive) if archive[:4] == b'GCR1' else C['decode'](archive)


def validate_fixtures():
    fixtures = []
    for level, data in [(0, b'nonempty stored '*7), (1, b'abac '*40), (9, bytes(range(256))*4)]:
        source = gzip.compress(data, compresslevel=level, mtime=0)
        for rid in range(3):
            for preset in [1, 6]:
                arc, _ = gzip_encode(source, rid, preset)
                if decode(arc) != source:
                    raise ValueError('fixture inverse')
        fixtures.append({'source_level': level, 'exact': True})
    return {'gzip': fixtures, 'mixed_stored_fixed': D['mixed_validation'](),
            'fixture_results_excluded_from_real_evidence': True}


def encode(source_path, archive_path, family):
    source = source_path.read_bytes()
    rows, candidates = [], []
    if family == 'gzip':
        for rid in range(3):
            for preset in [1, 6]:
                (a, stats), et = timed(lambda: gzip_encode(source, rid, preset))
                restored, dt = timed(lambda: decode(a))
                if restored != source:
                    raise ValueError('gzip exact candidate failure')
                total = sum(stats[str(i)] for i in [0, 1, 2])
                rows.append({'level': LEVELS[rid], 'inner_xz': preset, 'bytes': len(a),
                             'encode': et, 'decode_in_process': dt, 'tokens': stats,
                             'predicted_token_percent': 100*stats['0']/max(1, total)})
                candidates.append(a)
    elif family == 'bzip2':
        p = C['plaintext'](source, 'bzip2')
        for rid, r in enumerate(C['RECIPES']):
            if r['family'] != 'bzip2':
                continue
            for preset in [1, 6]:
                def make():
                    ref = C['reference'](p, rid)
                    if C['plaintext'](ref, 'bzip2') != p:
                        raise ValueError('reference plaintext mismatch')
                    a, e = C['encode'](source, lzma.compress(p, preset=preset), len(p), ref, rid, preset)
                    return a, ref, e
                (a, ref, residual), et = timed(make)
                restored, dt = timed(lambda: decode(a))
                if restored != source:
                    raise ValueError('bzip2 exact candidate failure')
                rows.append({'level': r['level'], 'inner_xz': preset, 'bytes': len(a),
                             'encode': et, 'decode_in_process': dt, 'reference_exact': ref == source,
                             'residual_nonzero_bytes': sum(x != 0 for x in residual)})
                candidates.append(a)
    else:
        raise ValueError('unsupported source family')
    controls = []
    for name, mode, fn in [('stored', 0, lambda: source), ('zlib9', 1, lambda: zlib.compress(source, 9)),
                           ('xz1', 2, lambda: lzma.compress(source, preset=1)),
                           ('xz6', 4, lambda: lzma.compress(source, preset=6))]:
        payload, et = timed(fn)
        arc = b'CTR1' + bytes([mode]) + payload
        restored, dt = timed(lambda: decode(arc))
        if restored != source:
            raise ValueError('control inverse mismatch')
        controls.append({'name': name, 'bytes': len(arc), 'encode': et, 'decode': dt})
    best = min(range(len(candidates)), key=lambda i: len(candidates[i]))
    archive_path.write_bytes(candidates[best])
    metrics = {'family': family, 'source_bytes': len(source), 'source_sha256': sha(source),
               'plaintext_bytes': len(gzip.decompress(source) if family == 'gzip' else C['plaintext'](source, 'bzip2')),
               'candidates': rows, 'selected_index': best, 'selected': rows[best], 'controls': controls,
               'strongest_control_including_original_bytes': min(len(source), *(c['bytes'] for c in controls)),
               'runtime': C['RUNTIME'], 'archive_sha256': sha(candidates[best]),
               'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               'cost_note': 'Candidate encode times include its regeneration and framing; gzip includes input decompression, bzip2 shares an initial decompression. Full selection phase costs are measured separately by bounded runner.'}
    archive_path.with_suffix('.metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')


if __name__ == '__main__':
    operation = sys.argv[1]
    if operation == 'validate':
        result = validate_fixtures()
        if len(sys.argv) == 4:
            Path(sys.argv[3]).write_bytes(b'CTR1\0' + Path(sys.argv[2]).read_bytes())
            Path(sys.argv[3]).with_suffix('.metrics.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
    elif operation in ['gzip', 'bzip2']:
        encode(Path(sys.argv[2]), Path(sys.argv[3]), operation)
    elif operation == 'decode':
        start, cpu = time.perf_counter(), time.process_time()
        b = decode(Path(sys.argv[2]).read_bytes())
        Path(sys.argv[3]).write_bytes(b)
        print(json.dumps({'restored_sha256': sha(b), 'bytes': len(b),
                          'decoder_wall_s': time.perf_counter()-start, 'decoder_cpu_s': time.process_time()-cpu,
                          'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
    else:
        raise ValueError('unknown operation')
