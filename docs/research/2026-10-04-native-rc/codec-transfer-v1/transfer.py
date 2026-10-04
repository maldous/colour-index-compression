#!/usr/bin/env python3
"""Bounded exact recompression by a paid plaintext and compressed-byte residual.

Research only: runtime-pinned references, not native codec-token predictors.
"""
import argparse
import bz2
import ctypes as ct
import ctypes.util
import hashlib
import json
import lzma
import platform
import resource
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

import brotli

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'benchmark-work/codec-transfer-v1'
LIMIT = 2 * 1024 * 1024
Z = ct.CDLL(ctypes.util.find_library('zstd'))


def bind(name, result, args):
    f = getattr(Z, name)
    f.restype, f.argtypes = result, args
    return f


zver = bind('ZSTD_versionString', ct.c_char_p, [])
zbound = bind('ZSTD_compressBound', ct.c_size_t, [ct.c_size_t])
zerr = bind('ZSTD_isError', ct.c_uint, [ct.c_size_t])
zname = bind('ZSTD_getErrorName', ct.c_char_p, [ct.c_size_t])
zcreate = bind('ZSTD_createCCtx', ct.c_void_p, [])
zfree = bind('ZSTD_freeCCtx', ct.c_size_t, [ct.c_void_p])
zparam = bind('ZSTD_CCtx_setParameter', ct.c_size_t, [ct.c_void_p, ct.c_int, ct.c_int])
zcompress = bind('ZSTD_compress2', ct.c_size_t,
                 [ct.c_void_p, ct.c_void_p, ct.c_size_t, ct.c_void_p, ct.c_size_t])
zdecompress = bind('ZSTD_decompress', ct.c_size_t,
                   [ct.c_void_p, ct.c_size_t, ct.c_void_p, ct.c_size_t])


def checked(n):
    if zerr(n):
        raise ValueError(zname(n).decode())
    return n


def libversion(name, function):
    lib = ct.CDLL(ctypes.util.find_library(name))
    f = getattr(lib, function)
    f.restype = ct.c_char_p
    return f().decode()


RUNTIME = {'python': sys.version, 'machine': platform.machine(),
           'zlib': zlib.ZLIB_RUNTIME_VERSION, 'brotli': brotli.__version__,
           'lzma': libversion('lzma', 'lzma_version_string'),
           'bzip2': libversion('bz2', 'BZ2_bzlibVersion'), 'zstd': zver().decode()}
RUNTIME_ID = hashlib.sha256(json.dumps(RUNTIME, sort_keys=True).encode()).digest()
RECIPES = []
for preset in [0, 1, 6, 9 | lzma.PRESET_EXTREME]:
    for check in [lzma.CHECK_CRC32, lzma.CHECK_CRC64]:
        RECIPES.append({'family': 'xz', 'preset': preset, 'check': check})
for level in [1, 9]:
    RECIPES.append({'family': 'bzip2', 'level': level})
for level in [-131072, 3, 19, 22]:
    for checksum in [0, 1]:
        RECIPES.append({'family': 'zstd', 'level': level, 'checksum': checksum,
                        'content_size': 1, 'workers': 0})
for quality in [0, 5, 11]:
    RECIPES.append({'family': 'brotli', 'quality': quality, 'lgwin': 22, 'mode': 0})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reference(plain, rid):
    r = RECIPES[rid]
    if r['family'] == 'xz':
        return lzma.compress(plain, preset=r['preset'], check=r['check'])
    if r['family'] == 'bzip2':
        return bz2.compress(plain, compresslevel=r['level'])
    if r['family'] == 'brotli':
        return brotli.compress(plain, quality=r['quality'], lgwin=r['lgwin'], mode=r['mode'])
    context = zcreate()
    if not context:
        raise MemoryError('ZSTD context')
    try:
        # Values from installed zstd.h: compressionLevel=100, contentSizeFlag=200,
        # checksumFlag=201, nbWorkers=400. One-shot input size is known.
        for key, value in [(100, r['level']), (200, 1), (201, r['checksum']), (400, 0)]:
            checked(zparam(context, key, value))
        dest = ct.create_string_buffer(zbound(len(plain)))
        source = ct.create_string_buffer(plain)
        n = checked(zcompress(context, dest, len(dest), source, len(plain)))
        return dest.raw[:n]
    finally:
        checked(zfree(context))


def plaintext(data, family):
    if family == 'xz':
        p = lzma.decompress(data)
    elif family == 'bzip2':
        p = bz2.decompress(data)
    elif family == 'brotli':
        p = brotli.decompress(data)
    elif family == 'zstd':
        dest = ct.create_string_buffer(LIMIT + 1)
        src = ct.create_string_buffer(data)
        n = checked(zdecompress(dest, len(dest), src, len(data)))
        p = dest.raw[:n]
    else:
        raise ValueError('unsupported family')
    if len(p) > LIMIT:
        raise ValueError('plaintext size exceeds frozen bound')
    return p


def residual(source, ref):
    n = min(len(source), len(ref))
    return bytes(a ^ b for a, b in zip(source[:n], ref[:n])) + source[n:]


def encode(source, px, plain_length, ref, rid, inner_preset):
    e = residual(source, ref)
    # Recipe, inner coder, original size, plaintext size, inner stream length,
    # and a runtime identity are ALL inside the paid archive.
    body = struct.pack('<BBQQQ', rid, inner_preset, len(source), plain_length, len(px))
    body += RUNTIME_ID + px + e
    return b'CTR1\x03' + lzma.compress(body, preset=1), e


def decode(archive):
    if archive[:4] != b'CTR1':
        raise ValueError('bad magic')
    mode = archive[4]
    if mode == 0:
        return archive[5:]
    if mode == 1:
        return zlib.decompress(archive[5:])
    if mode in [2, 4]:
        return lzma.decompress(archive[5:])
    if mode != 3:
        raise ValueError('bad mode')
    b = lzma.decompress(archive[5:])
    rid, preset, n, pn, pxn = struct.unpack('<BBQQQ', b[:26])
    if preset not in [1, 6] or b[26:58] != RUNTIME_ID:
        raise ValueError('reference runtime or coder mismatch')
    if n > LIMIT or pn > LIMIT or len(b) != 58 + pxn + n:
        raise ValueError('invalid body length')
    p = lzma.decompress(b[58:58 + pxn])
    if len(p) != pn:
        raise ValueError('plaintext length mismatch')
    ref = b'' if rid == 255 else reference(p, rid)
    # E has exactly n bytes; ignore only excess regenerated reference bytes.
    return residual(b[58 + pxn:], ref)


def tiny():
    checks = 0
    for source, ref in [(b'', b''), (b'abc', b'abcd'), (b'abcdef', b'a'),
                        (b'abc', b''), (b'', b'ab'), (b'abc', b'zyx')]:
        assert residual(residual(source, ref), ref) == source
        checks += 1
    data = bytes(range(256)) * 2 + b'transfer fixture ' * 100
    for rid, r in enumerate(RECIPES):
        source = reference(data, rid)
        assert plaintext(source, r['family']) == data
        a, _ = encode(source, lzma.compress(data, preset=1), len(data), source, rid, 1)
        assert decode(a) == source
        checks += 1
    # Constructed fixtures exercise exact recipes but are excluded from real wins.
    return {'checks': checks, 'generated_fixtures_excluded_from_real_results': True}


def timed(fn):
    wall, cpu = time.perf_counter(), time.process_time()
    value = fn()
    return value, {'wall_s': time.perf_counter() - wall, 'cpu_s': time.process_time() - cpu}


def run():
    plan = json.loads((HERE / 'plan.json').read_text())
    assert plan['source_sha256'] == sha(Path(__file__).read_bytes())
    assert plan['recipes'] == RECIPES and plan['runtime'] == RUNTIME
    OUT.mkdir(exist_ok=False)
    validation = tiny()
    result = {'experiment': 'codec-transfer-v1', 'scope': plan['scope'], 'runtime': RUNTIME,
              'plan_sha256': sha((HERE / 'plan.json').read_bytes()),
              'source_sha256': plan['source_sha256'], 'validation': validation, 'rows': []}
    for item in plan['inputs']:
        source = (ROOT / item['path']).read_bytes()
        assert len(source) == item['bytes'] and sha(source) == item['sha256']
        p, dt = timed(lambda: plaintext(source, item['family']))
        assert len(p) == item['plaintext_bytes'] and sha(p) == item['plaintext_sha256']
        row = {'input': item, 'original_decode': dt, 'candidates': [], 'fresh': []}
        pcs = {v: timed(lambda v=v: lzma.compress(p, preset=v)) for v in [1, 6]}
        controls = {'stored': b'CTR1\0' + source, 'zlib9': b'CTR1\1' + zlib.compress(source, 9),
                    'xz1': b'CTR1\2' + lzma.compress(source, preset=1),
                    'xz6': b'CTR1\4' + lzma.compress(source, preset=6)}
        row['controls_bytes'] = {k: len(v) for k, v in controls.items()}
        row['paid_plaintext_components'] = {str(v): {'bytes': len(x[0]), **x[1]} for v, x in pcs.items()}
        best = None
        for rid, r in enumerate(RECIPES):
            if r['family'] != item['family']:
                continue
            ref, rt = timed(lambda rid=rid: reference(p, rid))
            assert plaintext(ref, item['family']) == p
            for preset, (px, pt) in pcs.items():
                (a, e), et = timed(lambda: encode(source, px, len(p), ref, rid, preset))
                restored, it = timed(lambda: decode(a))
                assert restored == source
                cell = {'recipe_id': rid, 'recipe': r, 'inner_xz_preset': preset,
                        'archive_bytes': len(a), 'reference_bytes': len(ref),
                        'reference_exact': ref == source, 'residual_nonzero_bytes': sum(v != 0 for v in e),
                        'residual_xz1_bytes': len(lzma.compress(e, preset=1)),
                        'reference_encode': rt, 'outer_encode': et, 'decode': it,
                        'component_encode_cpu_s': pt['cpu_s'] + rt['cpu_s'] + et['cpu_s']}
                row['candidates'].append(cell)
                if best is None or len(a) < len(best[0]):
                    best = (a, cell)
        # Ablation: identical framing and paid plaintext, but original compressed
        # bytes used as the residual with an empty reference. Not a competitor.
        row['empty_reference_ablation_bytes'] = {
            str(v): len(encode(source, x[0], len(p), b'', 255, v)[0]) for v, x in pcs.items()}
        row['best'] = best[1]
        control_name = min(controls, key=lambda k: len(controls[k]))
        for name, archive in [('reconstruction', best[0]), ('control-' + control_name, controls[control_name])]:
            q = OUT / (item['id'] + '.' + name + '.ctr')
            q.write_bytes(archive)
            before = time.perf_counter()
            run = subprocess.run([sys.executable, str(Path(__file__)), '--inverse', str(q), item['sha256']],
                                 capture_output=True, text=True, timeout=25)
            if run.returncode:
                raise AssertionError(run.stdout + run.stderr)
            fresh = json.loads(run.stdout)
            fresh.update({'kind': name, 'path': str(q.relative_to(ROOT)), 'archive_bytes': len(archive),
                          'archive_sha256': sha(archive), 'process_wall_s': time.perf_counter() - before})
            row['fresh'].append(fresh)
        result['rows'].append(row)
        (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'completed': item['id'], 'original_bytes': len(source),
                          'reconstruction_bytes': len(best[0]), 'best_control_bytes': len(controls[control_name]),
                          'reference_exact': best[1]['reference_exact']}), flush=True)
    result['all_exact'] = True
    result['candidate_count'] = sum(len(r['candidates']) for r in result['rows'])
    (OUT / 'results.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inverse', nargs=2, metavar=('ARCHIVE', 'SHA256'))
    args = parser.parse_args()
    if args.inverse:
        archive, expected = args.inverse
        start = time.perf_counter()
        restored = decode(Path(archive).read_bytes())
        if sha(restored) != expected:
            raise ValueError('original compressed-byte hash mismatch')
        print(json.dumps({'exact': True, 'restored_sha256': sha(restored),
                          'decoder_wall_s': time.perf_counter() - start,
                          'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
    else:
        run()
