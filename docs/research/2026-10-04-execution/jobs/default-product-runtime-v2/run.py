#!/usr/bin/env python3
"""Root-leased complete default release CLI build and runtime qualification."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path('/home/user/src/colour-index-compression')
JOB = Path(__file__).resolve().parent
WORK = ROOT / 'benchmark-work/native-rc-check-v1'
OUT = WORK / JOB.name
ROOTS = [Path(p) for p in json.loads((JOB/'capacity-roots.json').read_text())]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def allocated():
    lines = subprocess.check_output(['du', '-sx', '--block-size=1', *map(str, ROOTS)], text=True).splitlines()
    rows = [{'bytes': int(line.split('\t', 1)[0]), 'path': line.split('\t', 1)[1]} for line in lines]
    return {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'rows': rows,
            'retained_git_delta_bytes': 2486272, 'total_bytes': sum(row['bytes'] for row in rows) + 2486272}


def verify():
    for manifest in [JOB/'source-inputs.json', JOB/'tool-inputs.json', JOB/'execution-inputs.json', JOB/'header-inputs.json', JOB/'provider-inputs.json']:
        for name, expected in json.loads(manifest.read_text()).items():
            assert sha(Path(name)) == expected, name
    for name, row in json.loads((JOB/'readonly-cache-inputs.json').read_text()).items():
        assert sha(Path(name)) == row['sha256'], name


def main():
    assert os.environ.get('CIX_RELEASE_LEASE') == '1', 'root scheduler required'
    admission = json.loads((JOB / 'admission.json').read_text())
    assert admission['comment_id'] and admission['other_reservation_bytes'] == 10000000
    verify()
    network = subprocess.check_output(['/usr/bin/systemctl', 'show', 'cix-rel01-execution-default-product-runtime-v2.service', '--property=PrivateNetwork', '--property=NoNewPrivileges'], text=True)
    assert 'PrivateNetwork=yes' in network.splitlines(), network
    before = allocated()
    assert before['total_bytes'] + 240000000 + admission['other_reservation_bytes'] <= 4000000000
    assert not OUT.exists(), 'immutable run identity already used'
    OUT.mkdir()
    scratch = OUT / 'scratch'
    evidence = OUT / 'evidence'
    scratch.mkdir()
    evidence.mkdir()
    (OUT / 'network-properties.txt').write_text(network)
    (OUT / 'network-namespace.txt').write_text(os.readlink('/proc/self/ns/net') + '\n')
    (OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
    env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C',
           'CIX_CHECK_SCRATCH': str(scratch), 'CIX_CHECK_EVIDENCE': str(evidence),
           'CIX_CHECK_ADMISSION': admission['comment_id']}
    command = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-pid', '--unshare-net',
               '--ro-bind', '/', '/', '--dev-bind', '/dev/null', '/dev/null', '--proc', '/proc',
               '--size', '219996160', '--tmpfs', str(scratch),
               '--bind', str(evidence), str(evidence), '--', '/usr/bin/python3', '-B', str(JOB / 'worker.py')]
    child = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(timeout=290)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate()
        (OUT / 'timeout.txt').write_text('outer namespace exceeded 290 seconds; process group killed\n')
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    assert len(stdout) <= 1000000 and len(stderr) <= 1000000, 'unexpected worker diagnostic volume'
    (OUT / 'worker.stdout').write_bytes(stdout)
    (OUT / 'worker.stderr').write_bytes(stderr)
    after = allocated()
    verify()
    outer_bytes = int(subprocess.check_output(['du','-sx','--block-size=1',str(JOB)],text=True).split()[0]) + sum(p.stat().st_blocks*512 for p in OUT.iterdir() if p.is_file()) + 8192
    assert outer_bytes <= 2000000, outer_bytes
    receipt = {'status': 'PASS' if child.returncode == 0 else 'FAILED', 'returncode': child.returncode,
               'admission': admission, 'before': before, 'after': after,
               'tmpfs_bytes': 219996160, 'evidence_cap_bytes': 18000000,
               'cgroup_contract': 'scheduler core 10, 6GB rounded to pages, no swap, CPUQuota=100%, 300s wall',
               'source_unchanged': True, 'outer_allocated_bytes': outer_bytes, 'scratch_after_namespace_teardown': list(scratch.iterdir()),
               'no_product_changes': True, 'scope': 'Actual default release library/CLI build and bounded CLI runtime qualification; no server/fullRC proof'}
    assert not receipt['scratch_after_namespace_teardown']
    assert after['total_bytes'] + admission['other_reservation_bytes'] <= 4000000000
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'returncode': child.returncode, 'out': str(OUT)}), flush=True)
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
