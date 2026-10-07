"""Focused same-CIX worker qualification; no evaluation corpus or ranking."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

job = Path(__file__).resolve().parent
config = json.loads((job / 'config.json').read_text())
raw = job / 'raw'
cargo = '/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo'
common = ['--locked', '--offline', '--manifest-path', str(Path(config['snapshot']) / 'Cargo.toml')]
for command in [[cargo, 'check', *common, '--all-targets'],
                [cargo, 'test', *common, '--lib', 'paq_worker::', '--', '--test-threads=4'],
                [cargo, 'build', *common, '--bin', 'cix']]:
    print('BUILD', command, flush=True)
    subprocess.run(command, check=True, stdin=subprocess.DEVNULL)

stage = Path(config['stage'])
stage.mkdir()
binary = stage / 'cix'
shutil.copy2(Path(config['target']) / 'debug/cix', binary)
libraries = stage / 'lib'
libraries.mkdir()
for variant in config['variants']:
    library = Path(variant['library'])
    assert hashlib.sha256(library.read_bytes()).hexdigest() == variant['qualification']['bridge_sha256']
    shutil.copy2(library, libraries / library.name)

cases = []
def case(name, command, success=True, environment=None):
    print('CASE', name, flush=True)
    result = subprocess.run([str(x) for x in command], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=90, env=environment or {'LC_ALL': 'C', 'OMP_NUM_THREADS': '1'})
    (raw / (name + '.stdout.log')).write_bytes(result.stdout)
    (raw / (name + '.stderr.log')).write_bytes(result.stderr)
    cases.append({'name': name, 'returncode': result.returncode, 'expected_success': success})
    (raw / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    assert (result.returncode == 0) == success, (name, result.returncode, result.stderr[-1000:])
    if success and command[0] == binary and '--internal-paq-worker-v1' in command:
        assert b'CIX_PAQ_WORKER_V1 status=ok' in result.stderr

def worker(variant, operation, source, output, memory=1_000_000_000, limit=1_000_000):
    return [binary, '--internal-paq-worker-v1', variant, operation, libraries,
            source, output, memory, limit, '-1', 2, 'none']

for entry in config['variants']:
    variant = entry['variant']
    source = Path(entry['source'])
    expected = Path(entry['archive'])
    directory = stage / variant
    directory.mkdir()
    archive = directory / 'worker.paq'
    forbidden_trace = directory / 'must-not-exist.trace'
    # Old research controls must not leak into the worker's codec state.
    env = {'LC_ALL': 'C', 'OMP_NUM_THREADS': '1', 'CIX_JOINT_DISCOUNT': '3',
           'CIX_REGISTER_BASE_TRACE': str(forbidden_trace)}
    case(variant + '-encode', worker(variant, 'encode', source, archive), environment=env)
    assert archive.read_bytes() == expected.read_bytes(), variant + ' archive differs'
    assert not forbidden_trace.exists()
    for name, payload in [('worker', archive), ('reference', expected)]:
        output = directory / (name + '-decoded.bin')
        case(variant + '-decode-' + name, worker(variant, 'decode', payload, output))
        assert output.read_bytes() == source.read_bytes()
    output = directory / 'reference-decodes-worker.bin'
    case(variant + '-reference-decode', [entry['reference'], '-d', '-simd', 'AVX2', archive, output])
    assert output.read_bytes() == source.read_bytes()
    case(variant + '-reject-existing', worker(variant, 'encode', source, archive), False)
    assert archive.read_bytes() == expected.read_bytes()
    symlink = directory / 'dangling'
    symlink.symlink_to(directory / 'missing')
    case(variant + '-reject-dangling', worker(variant, 'encode', source, symlink), False)
    assert symlink.is_symlink()
    limited = directory / 'limited.paq'
    case(variant + '-output-limit', worker(variant, 'encode', source, limited, limit=16), False)
    assert not limited.exists() or limited.stat().st_size <= 16

first = config['variants'][0]
case('extensionless-output', worker('v215', 'encode', first['source'], stage / 'extensionless'))
assert (stage / 'extensionless').read_bytes() == Path(first['archive']).read_bytes()
case('reject-trailing-separator', worker('v215', 'encode', first['source'], str(stage / 'new-directory') + '/'), False)
assert not (stage / 'new-directory').exists()
case('reject-backslash-path', worker('v215', 'encode', first['source'], str(stage / 'back') + chr(92) + 'slash'), False)
assert not (stage / 'back').exists()
case('reject-insufficient-memory', worker('v215', 'encode', first['source'], stage / 'too-small.paq', memory=1024), False)
case('reject-relative-library-path', [binary, '--internal-paq-worker-v1', 'v215', 'encode', 'lib',
    first['source'], stage / 'relative.paq', 1_000_000_000, 1_000_000, '-1', 2, 'none'], False)
case('reject-invalid-request', [binary, '--internal-paq-worker-v1', 'v215'], False)
case('ordinary-cli-version', [binary, '--version'])
summary = {
    'status': 'focused same-CIX worker passed; not full engine or RC qualification',
    'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
    'profile': 'Linux x86-64 AVX2, debug CIX, Release PAQ DSOs, level 1, two LSTM layers (LSTM not enabled)',
    'variants': [x['variant'] for x in config['variants']],
    'cases': cases,
}
(raw / 'qualification.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary), flush=True)
