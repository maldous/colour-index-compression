"""Finite reversible coordinate search; all seed/prefix/fallback costs paid."""
import hashlib
import json
import lzma
from pathlib import Path
import random
import struct
import subprocess
import sys
import time
import zlib
import count_dictionary as c

AREA = Path(__file__).resolve().parent
PARAMS = []
for seed in range(32):
    h = hashlib.sha256(b'CIX projection closure v1\x00'+bytes([seed])).digest()
    a = int.from_bytes(h[:4], 'big') & c.MASK | 1
    b = int.from_bytes(h[4:8], 'big') & c.MASK
    r1, r2, r3 = (1+h[i] % 30 for i in (8, 9, 10))
    PARAMS.append((a, b, r1, r2, r3, pow(a, -1, 1 << 31)))


def forward(x, seed):
    if seed == 0:
        return x
    a, b, r1, r2, r3, _ = PARAMS[seed]
    x ^= x >> r1
    x = (x*a+b) & c.MASK
    x = ((x << r2) | (x >> (31-r2))) & c.MASK
    return x ^ (x >> r3)


def undo_xor(x, r):
    y = x
    for s in range(r, 31, r):
        y ^= x >> s
    return y


def inverse(x, seed):
    if seed == 0:
        return x
    a, b, r1, r2, r3, inva = PARAMS[seed]
    x = undo_xor(x, r3)
    x = ((x >> r2) | (x << (31-r2))) & c.MASK
    x = ((x-b)*inva) & c.MASK
    return undo_xor(x, r1)


def words_of(data):
    r = c.Reader(data)
    n, tail = divmod(len(data)*8, 31)
    words = [r.get(31) for _ in range(n)]
    last = r.get(tail) if tail else 0
    r.end()
    return words, last, tail


def packed(words):
    w = c.Writer()
    for x in words:
        w.put(x, 31)
    return w.finish()


def basis_of(xs):
    anchor, basis = xs[0], []
    for x in xs[1:]:
        r = x ^ anchor
        for v in basis:
            if r & (1 << (v.bit_length()-1)):
                r ^= v
        if r:
            basis.append(r)
            basis.sort(reverse=True)
    return anchor, basis


def basis_code(xs, out):
    anchor, basis = basis_of(xs)
    d = len(basis)
    cost = 1+31+5+31*d+(len(xs)-1)*d
    if cost >= 1+31*len(xs):
        out.put(0, 1)
        for x in xs:
            out.put(x, 31)
        return False, d
    out.put(1, 1); out.put(anchor, 31); out.put(d, 5)
    for v in basis:
        out.put(v, 31)
    for x in xs[1:]:
        r, coeff = x ^ anchor, 0
        for j, v in enumerate(basis):
            if r & (1 << (v.bit_length()-1)):
                coeff |= 1 << j; r ^= v
        assert not r
        out.put(coeff, d)
    return True, d


def representation(words, last, tail, mode, views):
    out = c.Writer()
    group = 1 if mode == 3 else 64
    stats = dict(groups=0, selected=0, seed_counts={}, dimension_counts={})
    for start in range(0, len(words), group):
        xs = words[start:start+group]
        m = len(xs)
        stats['groups'] += 1
        if mode == 4:
            chosen, d = basis_code(xs, out)
            stats['selected'] += int(chosen)
            stats['dimension_counts'][d] = stats['dimension_counts'].get(d, 0)+1
            continue
        best = (1+31*m, None)
        for seed in (range(1) if mode == 1 else range(32)):
            ys = views[seed][start:start+m]
            allbits = varying = 0
            for y in ys:
                allbits |= y
                varying |= y ^ ys[0]
            for kind, d in ((0, allbits.bit_length()), (1, varying.bit_length())):
                cost = 2+(0 if mode == 1 else 5)+5+m*d+(31-d if kind else 0)
                if cost < best[0]:
                    best = cost, (seed, kind, d)
        if best[1] is None:
            out.put(0, 1)
            for x in xs:
                out.put(x, 31)
            continue
        seed, kind, d = best[1]
        out.put(1, 1); out.put(kind, 1)
        if mode != 1:
            out.put(seed, 5)
        out.put(d, 5)
        ys = views[seed][start:start+m]
        if kind:
            out.put(ys[0] >> d, 31-d)
        for y in ys:
            out.put(y & ((1 << d)-1), d)
        stats['selected'] += 1
        stats['seed_counts'][seed] = stats['seed_counts'].get(seed, 0)+1
        stats['dimension_counts'][d] = stats['dimension_counts'].get(d, 0)+1
    if tail:
        out.put(last, tail)
    return out.finish(), stats


def unrepresent(payload, size, mode):
    r, out = c.Reader(payload), c.Writer()
    n, tail = divmod(size*8, 31)
    group = 1 if mode == 3 else 64
    for start in range(0, n, group):
        m = min(group, n-start)
        if not r.get(1):
            xs = [r.get(31) for _ in range(m)]
        elif mode == 4:
            anchor, d = r.get(31), r.get(5)
            basis = [r.get(31) for _ in range(d)]
            xs = [anchor]
            for _ in range(m-1):
                coeff, x = r.get(d), anchor
                for j, v in enumerate(basis):
                    if (coeff >> j) & 1:
                        x ^= v
                xs.append(x)
        else:
            kind = r.get(1)
            seed = 0 if mode == 1 else r.get(5)
            d = r.get(5)
            prefix = r.get(31-d) << d if kind else 0
            xs = [inverse(prefix | r.get(d), seed) for _ in range(m)]
        for x in xs:
            out.put(x, 31)
    if tail:
        out.put(r.get(tail), tail)
    r.end()
    return out.finish()


def frame(data, mode, payload):
    return b'SP31'+struct.pack('>BII', mode, len(data), zlib.crc32(data))+payload


def encode(data):
    words, last, tail = words_of(data)
    views = [[forward(x, seed) for x in words] for seed in range(32)]
    frames = {0: frame(data, 0, data), 5: frame(data, 5, c.zcompress(data)),
              10: frame(data, 10, lzma.compress(data, preset=1))}
    stats = {}
    for mode in (1, 2, 3, 4):
        payload, stats[mode] = representation(words, last, tail, mode, views)
        frames[mode] = frame(data, mode, payload)
        frames[mode+5] = frame(data, mode+5, c.zcompress(payload))
    return frames, stats


def decode(archive):
    if len(archive) < 13 or archive[:4] != b'SP31':
        raise ValueError('invalid SP31 frame')
    mode, size, crc = struct.unpack('>BII', archive[4:13])
    if size > 1048576:
        raise ValueError('research limit')
    payload = archive[13:]
    if mode in range(5, 10):
        payload = c.zdecompress(payload, (size*8//31*32+30+7)//8)
        mode -= 5
    elif mode == 10:
        d = lzma.LZMADecompressor(); payload = d.decompress(payload, max_length=size+1)
        if not d.eof or d.unused_data:
            raise ValueError('invalid xz payload')
        mode = 0
    data = payload if mode == 0 else unrepresent(payload, size, mode) if mode in range(1, 5) else None
    if data is None or len(data) != size or zlib.crc32(data) != crc:
        raise ValueError('wrong restoration')
    return data


NAMES = ['raw','identity_group','seed_group','seed_word','affine_basis',
         'zstd','identity_group_zstd','seed_group_zstd','seed_word_zstd','affine_basis_zstd','xz']


def sample(data, name, scope):
    start = time.perf_counter(); frames, stats = encode(data)
    encode_seconds = time.perf_counter()-start
    folder = AREA/'projection-output'/name
    folder.mkdir(parents=True, exist_ok=False)
    rows = {}
    for mode, archive in sorted(frames.items()):
        path = folder/(NAMES[mode]+'.sp31'); path.write_bytes(archive)
        restored = folder/'restored.bin'
        start = time.perf_counter()
        subprocess.run([sys.executable, __file__, 'decode', str(path), str(restored)], check=True, timeout=10)
        assert restored.read_bytes() == data
        restored.unlink()
        rows[NAMES[mode]] = dict(bytes=len(archive), sha256=hashlib.sha256(archive).hexdigest(),
                               fresh_roundtrip=True, decode_seconds=time.perf_counter()-start, path=str(path))
    controls = ['raw','identity_group','affine_basis','zstd','identity_group_zstd','affine_basis_zstd','xz']
    candidates = ['seed_group','seed_word','seed_group_zstd','seed_word_zstd']
    bestcontrol = min(rows[k]['bytes'] for k in controls)
    bestcandidate = min(rows[k]['bytes'] for k in candidates)
    out = dict(name=name, scope=scope, source_bytes=len(data), source_sha256=hashlib.sha256(data).hexdigest(),
               combined_encode_seconds=encode_seconds, frames=rows, stats=stats,
               saving_vs_best_control=bestcontrol-bestcandidate,
               passes_gate=bestcandidate <= .995*bestcontrol and bestcontrol-bestcandidate >= 64)
    print(json.dumps(dict(name=name, best_control=bestcontrol, best_seed=bestcandidate, gate=out['passes_gate'])), flush=True)
    return out


def main():
    start = time.perf_counter()
    plan = json.loads((AREA/'projection-plan.json').read_text())
    for name, sha in plan['sources'].items():
        assert hashlib.sha256((AREA/name).read_bytes()).hexdigest() == sha
    rng = random.Random(202610043)
    checks = 0
    for seed in range(32):
        for x in [0, c.MASK, 1, 1<<30] + [rng.randrange(1 << 31) for _ in range(100)]:
            assert inverse(forward(x, seed), seed) == x
            assert forward(inverse(x, seed), seed) == x
            checks += 2
    for n in list(range(9))+[247,248,249]:
        data = bytes(rng.randrange(256) for _ in range(n))
        for archive in encode(data)[0].values():
            assert decode(archive) == data
            checks += 1
    rows = []
    seed = 7
    words = [inverse(rng.randrange(1 << 17), seed) for _ in range(4096)]
    rows.append(sample(packed(words), 'hidden_seed_space', 'constructed_17dimensional_positive'))
    words = [rng.randrange(1 << 17) for _ in range(4096)]
    rows.append(sample(packed(words), 'visible_low_dimension', 'identity_coordinate_control'))
    rows.append(sample(bytes(rng.randrange(256) for _ in range(16384)), 'uniform_bytes', 'synthetic_null'))
    for item in plan['inputs']:
        data = Path(item['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'] and len(data) == item['bytes']
        rows.append(sample(data[item['offset']:item['offset']+item['length']], item['name'], 'exposed_silesia_sample'))
    result = dict(plan_sha256=hashlib.sha256((AREA/'projection-plan.json').read_bytes()).hexdigest(),
                  exact_inverse_checks=checks, rows=rows, wall_seconds=time.perf_counter()-start,
                  scope='32 fixed seed-selected bijections, coordinate subspaces/affine basis, groups64 and per-word; not arbitrary functions/manifolds.')
    (AREA/'projection-results.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(stage='finished', seconds=result['wall_seconds'])), flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'decode':
        Path(sys.argv[3]).write_bytes(decode(Path(sys.argv[2]).read_bytes()))
    else:
        main()
