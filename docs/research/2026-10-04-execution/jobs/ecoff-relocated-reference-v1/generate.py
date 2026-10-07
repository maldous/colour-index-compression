#!/usr/bin/python3
"""CIX134: one synthetic USTAR carrier; raw ECRP1 reference goldens only."""
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import struct
import sys
import tarfile
import time

os.sched_setaffinity(0, {9})
resource.setrlimit(resource.RLIMIT_AS, (500_000_000, 500_000_000))
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
OUT = ROOT / 'rust/cix-native/tests/fixtures/ecoff_relocated_reference'
REFS = [ROOT / 'runtime/cix_runtime/__init__.py', ROOT / 'runtime/cix_runtime/legacy/__init__.py'] + [ROOT / ('runtime/cix_runtime/legacy/' + n + '.py') for n in ['ecoff_relocated_pointers', 'ecoff_got', 'ecoff_fields', 'ecoff_constraints', 'multinomial']]
TEMPLATE = ROOT / 'rust/cix-native/tests/fixtures/address_relations/source.bin'
PROVENANCE = [ROOT / 'rust/cix-native/tests/fixtures/address_relations/manifest.json', ROOT / 'benchmark-work/native-rc-check-v1/execution-address-fixture-v5/generate.py']

def sha(data):
    return hashlib.sha256(data).hexdigest()

def pins():
    return {str(p): sha(p.read_bytes()) for p in REFS + [TEMPLATE] + PROVENANCE + [Path('/usr/bin/python3').resolve()]}

def main():
    started = time.monotonic()
    before = pins()
    source = TEMPLATE.read_bytes()
    assert len(source) == 1224 and sha(source) == '77634c99d0c781323b7d72fd004b87cbebaad236b62f98240360b8e526516115'
    assert not OUT.exists(), 'output must be absent; no overwrite or rerun'
    from cix_runtime.legacy import ecoff_relocated_pointers as ref
    carrier = io.BytesIO()
    layout = [('local-hit', 0x1000, 0x1000), ('shared-hit', 0x2000, 0x1000), ('literal-escape', 0x3000, 0x9999), ('undefined-symbol', 0, 0x1000)]
    with tarfile.open(fileobj=carrier, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, symbol, pointer in layout:
            blob = bytearray(source)
            for position in (0x490, 0x4a8):
                struct.pack_into('<Q', blob, position, symbol)
            struct.pack_into('<Q', blob, 0x470, pointer)
            member = tarfile.TarInfo(name)
            member.size = len(blob)
            member.mode = 0o644
            member.uid = member.gid = member.mtime = 0
            member.uname = member.gname = ''
            archive.addfile(member, io.BytesIO(blob))
    original = carrier.getvalue()
    assert len(original) <= 16384
    local = ref.candidates(original, False)
    shared = ref.candidates(original, True)
    assert len(local) == len(shared) == 4
    assert [c for _, _, c in local] == [0, 0, 0, 1]
    def hits(fields):
        return [struct.unpack_from('<Q', original, p)[0] in options for p, options, _ in fields]
    assert hits(local) == [True, False, False, False]
    assert hits(shared) == [True, True, False, True]
    OUT.mkdir(parents=True)
    (OUT / 'original.tar').write_bytes(original)
    rows = []
    for flag in (False, True):
        for mode in range(6):
            raw, stats = ref.transform(original, mode, flag)
            assert stats['mapped_pointers'] == 4
            assert stats['in_candidates'] == (3 if flag else 1)
            assert stats['exception_bytes'] == ((8 if flag else 24) if mode >= 2 else 0)
            assert ref.inverse(raw) == original
            name = f'mode{mode}-shared{int(flag)}.raw'
            (OUT / name).write_bytes(raw)
            rows.append({'file': name, 'raw_sha256': sha(raw), 'original_sha256': sha(original), 'inverse_exact': True, **stats})
    assert before == pins(), 'input drift'
    imported = sorted(n for n in sys.modules if n.startswith('cix_runtime'))
    assert imported == sorted(['cix_runtime', 'cix_runtime.legacy'] + ['cix_runtime.legacy.' + n for n in ['ecoff_relocated_pointers', 'ecoff_got', 'ecoff_fields', 'ecoff_constraints', 'multinomial']])
    record = {'schema': 'cix.ecoff-relocated-reference.v1', 'claim': '00dd4300-0a00-475f-8fc7-472d6365a1af', 'scope': 'synthetic raw transform/inverse only; native and backend/archive checks UNRUN', 'input_pins_before_after': before, 'interpreter': sys.version, 'generator_sha256': sha(Path(__file__).read_bytes()), 'carrier_bytes': len(original), 'carrier_sha256': sha(original), 'layout': layout, 'local_hit_flags': hits(local), 'shared_hit_flags': hits(shared), 'undefined_contexts': [c for _, _, c in local], 'imported_cix_modules': imported, 'vectors': rows, 'elapsed_seconds': time.monotonic() - started, 'maxrss_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'future_native_tests_only': ['reject invalid trailer, invalid metadata size/model/shared flag, wrong membership length, truncated exception and unused metadata', 'reject output budget below original length before output allocation; reference has no budget API'], 'outer_wire_spec_only': 'CIXB binary 0a; backend byte 0 Brotli / 1 PAQ; varint original length; big-endian CRC32; actual backend payload. No compressed frame generated.'}
    (OUT / 'manifest.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    files = [Path(__file__)] + sorted(OUT.iterdir())
    bound = {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in files}
    (JOB / 'artifact-manifest.json').write_text(json.dumps(bound, indent=2, sort_keys=True) + '\n')
    allocated = sum(p.stat().st_blocks * 512 for p in [JOB, OUT] + files + [JOB / 'artifact-manifest.json'])
    assert allocated <= 5_000_000
    print(json.dumps({'vectors': len(rows), 'carrier_bytes': len(original), 'allocated_bytes': allocated, 'manifest_sha256': sha((JOB / 'artifact-manifest.json').read_bytes()), 'elapsed_seconds': record['elapsed_seconds'], 'maxrss_KiB': record['maxrss_KiB']}))

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        (JOB / 'FAILURE.json').write_text(json.dumps({'type': type(exc).__name__, 'error': str(exc), 'native_backend_archive': 'UNRUN'}) + '\n')
        raise
