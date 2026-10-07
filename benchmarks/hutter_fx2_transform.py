"""Materialize and independently invert the full winning Wikipedia transform.

This prepares representative model inputs, not a compressed CIX result. It
pins upstream source, verifies the entire canonical input and inverse hash,
runs decoder without source/order access, and preserves all artifact identities.
The caller must hold the shared measurement lock and stop the old baseline.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path('/home/user/src/cix-hutter-reference-sources/fx2-cmix')
REVISION = '04c5806f99b9b0fa8572be8c8063b4324ec405de'
CANONICAL = Path('/home/user/src/cix-baseline-data/inputs/enwik9')
SHA = '159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def identity(path):
    return dict(bytes=path.stat().st_size, sha256=digest(path))


def write(path, value):
    temp = path.with_suffix('.writing')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def run(command, folder, name, cpu):
    # All subprocesses inherit one-core placement. GNU time includes I/O.
    wrapped = ['taskset', '-c', str(cpu), '/usr/bin/time', '-f', '%e %U %S %M',
               '-o', str(folder / (name + '.time')), *command]
    begin = time.monotonic()
    with (folder / (name + '.log')).open('wb') as log:
        r = subprocess.run(wrapped, cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                           timeout=1800, check=False)
    record = dict(command=wrapped, exit_code=r.returncode,
                  wall_seconds=time.monotonic() - begin)
    timing = (folder / (name + '.time')).read_text().splitlines()[-1].split()
    record['supervisor_resources'] = dict(inner_wall_seconds=float(timing[0]),
        user_seconds=float(timing[1]), system_seconds=float(timing[2]), peak_rss_kib=int(timing[3]))
    if name in ('encode', 'decode'):
        # /usr/bin/time outside a PID namespace observes the bubblewrap
        # supervisor, not the isolated transform's CPU/RSS. Read its inner log.
        timing = (folder / name / 'workload.time').read_text().splitlines()[-1].split()
        record['resource_measurement_scope'] = 'native transform process; GNU time inside namespace'
    else:
        record['resource_measurement_scope'] = 'build process and descendants; GNU time'
    record.update(inner_wall_seconds=float(timing[0]), user_seconds=float(timing[1]),
                  system_seconds=float(timing[2]), peak_rss_kib=int(timing[3]))
    write(folder / (name + '.json'), record)
    if r.returncode:
        raise RuntimeError(f'{name} failed: see retained log')
    return record


def namespace(binary, folder, args, original=None):
    command = ['bwrap', '--unshare-user', '--unshare-pid', '--unshare-net',
               '--die-with-parent', '--ro-bind', '/usr', '/usr',
               '--symlink', 'usr/bin', '/bin', '--ro-bind', '/lib', '/lib',
               '--ro-bind', '/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
               '--ro-bind', str(binary), '/transform', '--bind', str(folder), '/work',
               '--bind', str(folder / 'temp'), '/tmp', '--chdir', '/work']
    if original is not None:
        command += ['--ro-bind', str(original), '/canonical-enwik9']
    return command + ['--', '/usr/bin/time', '-f', '%e %U %S %M',
                      '-o', '/work/workload.time', '/transform', *args]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--cpu', type=int, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    state = dict(status='STARTED', qualifying=False, research_only=True,
                 started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(out / 'result.json', state)
    try:
        if shutil.disk_usage(out).free < 25_000_000_000:
            raise RuntimeError('Need 25 GB free before full transform preparation')
        current = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(UPSTREAM), 'status', '--porcelain'], text=True)
        if current != REVISION or dirty:
            raise RuntimeError('Upstream reference changed')
        source = identity(CANONICAL)
        if source != dict(bytes=1_000_000_000, sha256=SHA):
            raise RuntimeError('Canonical enwik9 identity mismatch')
        tracked = subprocess.check_output(['git', '-C', str(UPSTREAM), 'ls-files', '-z']).split(b'\0')
        files = {n.decode(): identity(UPSTREAM / n.decode()) for n in tracked if n}
        native = ROOT / 'benchmarks/native_hutter_fx2_transform.cpp'
        state.update(input=source, upstream_revision=current, upstream_files=files,
                     driver=identity(native), runner=identity(Path(__file__)),
                     cix_revision=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
                     compiler=subprocess.check_output(['clang++', '--version'], text=True))
        write(out / 'result.json', state)
        binary = out / 'transform'
        state['build'] = run(['clang++', '-O3', '-std=c++17', '-I',
                             str(UPSTREAM / 'src/readalike_prepr'), str(native), '-o', str(binary)],
                            out, 'build', args.cpu)
        state['binary'] = identity(binary)
        enc, dec = out / 'encode', out / 'decode'
        for folder in (enc, dec):
            (folder / 'temp').mkdir(parents=True)
        order = UPSTREAM / 'src/readalike_prepr/data/new_article_order'
        shutil.copyfile(order, enc / '.new_article_order')
        state['article_order'] = identity(order)
        state['encode'] = run(namespace(binary, enc, ['encode', '/canonical-enwik9'], CANONICAL),
                              out, 'encode', args.cpu)
        transformed = enc / '.ready4cmix'
        state['transformed'] = identity(transformed)
        write(out / 'result.json', state)
        os.link(transformed, dec / '.input_decomp')
        state['decode'] = run(namespace(binary, dec, ['decode']), out, 'decode', args.cpu)
        restored = dec / 'enwik9_restored'
        state['restored'] = identity(restored)
        if state['restored'] != source:
            raise RuntimeError('Full transform inverse did not restore canonical enwik9')
        state['artifacts'] = {str(f.relative_to(out)): identity(f)
                              for d in (enc, dec) for f in sorted(d.iterdir()) if f.is_file()}
        # Remove only this completed invocation's reproducible intermediates;
        # retain transformed stream, upstream, logs and every physical hash.
        state['removed_after_full_verification'] = []
        for d in (enc, dec):
            for f in sorted(d.iterdir()):
                if f.is_file() and f != transformed and f.name != 'workload.time':
                    f.unlink()
                    state['removed_after_full_verification'].append(str(f.relative_to(out)))
        state.update(status='VERIFIED FULL TRANSFORM ONLY', round_trip=True,
                     compressed_score_bytes=None,
                     note='No entropy coding or CIX/Hutter score. Full source transform is now available for representative predictor experiments.')
    except BaseException as exc:
        state.update(status='FAILED', error=repr(exc))
        raise
    finally:
        state['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(out / 'result.json', state)


if __name__ == '__main__':
    main()
