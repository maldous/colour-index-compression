#!/usr/bin/env python3
"""Execute existing standalone Rust contracts under the root scheduler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time

ROOT = Path('/home/user/src/colour-index-compression')
JOB = Path(__file__).resolve().parent
TOOLCHAIN = Path('/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin')
parser = argparse.ArgumentParser()
parser.add_argument('--root-admission', required=True)
args = parser.parse_args()
assert args.root_admission


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    for name in ('source-inputs.json', 'tool-inputs.json', 'execution-inputs.json'):
        for path, expected in json.loads((JOB / name).read_text()).items():
            assert sha(Path(path)) == expected, path


verify()
RUN = Path(os.environ['CIX_CHECK_SCRATCH']) / 'run'
RUN.mkdir(exist_ok=False)
(RUN / 'tmp').mkdir()
start = time.monotonic()
deadline = start + 85
os.sched_setaffinity(0, {10})
ENV = {'PATH': str(TOOLCHAIN) + ':/usr/bin:/bin', 'HOME': str(RUN),
       'TMPDIR': str(RUN / 'tmp'), 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
commands = []
groups = []


def child_limits():
    os.sched_setaffinity(0, {10})
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


def run(command, label):
    assert time.monotonic() < deadline, 'inner wall budget exhausted'
    log = RUN / (label + '.log')
    with log.open('wb') as stream:
        child = subprocess.Popen(command, cwd=JOB, env=ENV, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True,
                                 preexec_fn=child_limits)
        stopped = None
        try:
            while child.poll() is None:
                if time.monotonic() >= deadline:
                    stopped = '85-second inner deadline'
                elif log.stat().st_size >= 1000000:
                    stopped = '1 MB diagnostic limit'
                if stopped:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    break
                time.sleep(0.02)
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    commands.append({'label': label, 'command': command, 'exit': child.returncode,
                     'stopped': stopped, 'log_sha256': sha(log)})
    if stopped:
        raise RuntimeError(stopped)
    assert child.returncode == 0, f'{label}: exit {child.returncode}'
    return log.read_text()


result = {'admission': args.root_admission, 'scope': 'standalone foundations only',
          'benchmarks': 'STOPPED', 'service_auth_enforcement': 'UNQUALIFIED',
          'full_cli_sdk_text_migration': 'UNQUALIFIED'}
try:
    contracts = [('i18n', 'tests/i18n_contract.rs', 10),
                 ('managed-policy', 'src/managed_sdk/mod.rs', 8)]
    for label, relative, expected_count in contracts:
        group = {'name': label, 'expected_tests': expected_count, 'status': 'UNRUN',
                 'source': str(ROOT / 'rust/cix-native' / relative)}
        groups.append(group)
        try:
            binary = RUN / (label + '-tests')
            run([str(TOOLCHAIN / 'rustc'), '--test', '--edition=2021',
                 '--crate-name', label.replace('-', '_') + '_contract',
                 '-C', 'debuginfo=0', '-C', 'opt-level=0', group['source'],
                 '-o', str(binary)], label + '-compile')
            group.update(compile='PASS', binary_sha256=sha(binary))
            log = run([str(binary), '--test-threads=1'], label + '-tests')
            counts = re.search(r'test result: ok\. (\d+) passed; (\d+) failed; '
                               r'(\d+) ignored; (\d+) measured; (\d+) filtered out', log)
            assert counts and tuple(map(int, counts.groups())) == (expected_count, 0, 0, 0, 0), label
            group.update(status='PASS', passed=expected_count, failed=0, filtered=0)
        except Exception as error:
            group.update(status='FAILED', error=str(error))
            # A second independent contract may still run once; neither is retried.
            if time.monotonic() >= deadline:
                raise
    verify()
    result['status'] = 'PASS' if all(g['status'] == 'PASS' for g in groups) else 'FAILED'
except BaseException as error:
    result.update(status='FAILED', error=str(error))
finally:
    result.update(groups=groups, commands=commands,
                  elapsed_seconds=time.monotonic() - start,
                  source_unchanged=True if result.get('status') == 'PASS' else 'see outer verification')
    (RUN / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
sys.exit(0 if result['status'] == 'PASS' else 1)
