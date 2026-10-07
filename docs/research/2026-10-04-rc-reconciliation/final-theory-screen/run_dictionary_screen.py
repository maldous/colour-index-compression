"""Frozen finite screen, with real data kept separate from synthetic controls."""
import hashlib
import json
import math
import random
import resource
import subprocess
import sys
import time
from pathlib import Path
import count_dictionary as c

AREA = Path(__file__).resolve().parent
NAMES = ['raw', 'count', 'dictionary', 'function', 'zstd', 'count_zstd',
         'dictionary_zstd', 'function_zstd', 'zlib', 'xz']


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')


def pack_words(words):
    w = c.Writer()
    for word in words:
        w.put(word, 31)
    return w.finish()


def validate():
    checked = 0
    for n in range(13):
        for x in range(1 << n):
            assert c.unrank(c.rank(x), x.bit_count(), n) == x
            checked += 1
    for k in range(32):
        total = c.COMB[31][k]
        for r in set((0, total-1, total//2)):
            x = c.unrank(r, k)
            assert x.bit_count() == k and c.rank(x) == r
            checked += 1
    words = [x ^ mask for k in range(10, 16) for x in c.DICTIONARY[k] for mask in (0, c.MASK)]
    rng = random.Random(202610041)
    for k in range(32):
        words.extend(c.unrank(rng.randrange(c.COMB[31][k]), k) for _ in range(50))
    controls = [b'', b'\x00', b'\xff', bytes(range(256)), pack_words(words)]
    for size in range(18):
        controls.append(bytes(rng.randrange(256) for _ in range(size)))
    frames = 0
    for data in controls:
        for archive in c.archives(data)[0].values():
            assert c.decode(archive) == data
            frames += 1
    archive = c.archives(b'a'*100)[0][2]
    invalid = [archive[:i] for i in (0, 3, 12, 13, len(archive)-1)] + [archive+b'\0', archive[:12]+bytes([archive[12]^1])+archive[13:]]
    for bad in invalid:
        try:
            c.decode(bad)
        except (ValueError, IndexError):
            continue
        raise AssertionError('accepted invalid frame')
    return dict(exhaustive_small_rank_and_boundary_checks=checked, control_frames=frames,
                generator_patterns_with_both_colours=len(words)-32*50, malformed_rejected=len(invalid))


def sample(data, name, scope):
    started = time.perf_counter()
    result, stats = c.archives(data)
    elapsed = time.perf_counter()-started
    folder = AREA/'output'/name
    folder.mkdir(parents=True, exist_ok=False)
    rows = {}
    for mode, archive in sorted(result.items()):
        path = folder/(NAMES[mode]+'.cg31'); path.write_bytes(archive)
        restored = folder/'restored.bin'
        start = time.perf_counter()
        subprocess.run([sys.executable, str(AREA/'count_dictionary.py'), 'decode', str(path), str(restored)], check=True, timeout=10)
        duration = time.perf_counter()-start
        assert restored.read_bytes() == data
        restored.unlink()
        rows[NAMES[mode]] = dict(bytes=len(archive), sha256=hashlib.sha256(archive).hexdigest(),
                               fresh_roundtrip=True, decode_process_seconds=duration, path=str(path))
    bestcontrol = min(rows[k]['bytes'] for k in ('raw','count','zstd','count_zstd','function','function_zstd','zlib','xz'))
    bestdict = min(rows[k]['bytes'] for k in ('dictionary','dictionary_zstd'))
    out = dict(name=name, scope=scope, source_bytes=len(data), source_sha256=hashlib.sha256(data).hexdigest(),
               combined_encoding_seconds=elapsed, frames=rows, token_statistics=stats,
               dictionary_saving_against_best_control=bestcontrol-bestdict,
               passes_gate=bestdict <= .995*bestcontrol and bestcontrol-bestdict >= 64)
    print(json.dumps(dict(sample=name, scope=scope, best_control_bytes=bestcontrol,
                          best_dictionary_bytes=bestdict, gate=out['passes_gate'])), flush=True)
    return out


def main():
    started = time.perf_counter()
    plan = json.loads((AREA/'plan.json').read_text())
    for name, sha in plan['sources'].items():
        assert hashlib.sha256((AREA/name).read_bytes()).hexdigest() == sha
    tests = validate()
    print(json.dumps(dict(stage='controls_passed', **tests)), flush=True)
    rows = []
    rng = random.Random(202610042)
    words = [c.generate(rng.randrange(10,16), rng.randrange(31), rng.randrange(1,16)) ^ (c.MASK if rng.randrange(2) else 0) for _ in range(8192)]
    rows.append(sample(pack_words(words), 'generated_progressions', 'synthetic_positive'))
    words = []
    for _ in range(8192):
        k = rng.randrange(10,16)
        words.append(c.unrank(rng.randrange(c.COMB[31][k]), k) ^ (c.MASK if rng.randrange(2) else 0))
    rows.append(sample(pack_words(words), 'uniform_middle_counts', 'synthetic_matched_null'))
    rows.append(sample(bytes(rng.randrange(256) for _ in range(65536)), 'uniform_bytes', 'synthetic_null'))
    for item in plan['inputs']:
        data = Path(item['path']).read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
        data = data[item['offset']:item['offset']+item['length']]
        rows.append(sample(data, item['name'], 'historically_exposed_silesia_sample'))
    maths = []
    for k in range(16):
        count = math.comb(31,k)
        width = (count-1).bit_length()
        maths.append(dict(k=k, patterns=count, conditional_rank_bits=width, five_bit_metadata_total=5+width,
                          dictionary_patterns=465 if k>=10 else 0,
                          dictionary_fraction=465/count if k>=10 else 0,
                          full_dictionary_u32_bytes=4*count,
                          collision_free_generator_index_lower_bound=width))
    result = dict(plan_sha256=hashlib.sha256((AREA/'plan.json').read_bytes()).hexdigest(), validation=tests,
                  math=maths, rows=rows, wall_seconds=time.perf_counter()-started,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  comparison_limit='No CIX release or public specialist benchmark; fixed arithmetic-progression family only.')
    dump(AREA/'results.json', result)
    print(json.dumps(dict(stage='finished', wall_seconds=result['wall_seconds'], samples=len(rows))), flush=True)


if __name__ == '__main__':
    main()
