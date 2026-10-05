#!/usr/bin/env python3
"""Root-leased execution of the frozen CIX-128 module candidate."""
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
CANDIDATE = JOB.parent / 'graph-residual-parity-v2'
ROOTS = [WORK, Path('/home/user/src/cix-managed-service'),
         Path('/home/user/src/output/cix-comic-cast'),
         Path('/home/user/Documents/Codex/2026-10-05/task/cix-managed-service'),
         Path('/home/user/.local/share/cix-operations/backups/2026-10-05-management-accepted'),
         Path('/home/user/.local/share/cix-operations/restore-drill-2026-10-05-management-accepted'),
         CANDIDATE, JOB.parent / 'graph-residual-parity-v1',
         JOB.parent / 'graph-residual-parity-execution-v1', ROOT / 'rust/cix-native/tests/graph_residual_parity.rs',
         ROOT / 'rust/cix-native/tests/fixtures/graph_residual_parity', JOB,
         Path('/home/user/.codex/generated_images/01a10bd3-d549-7573-891d-ea921df85469')]


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
            'total_bytes': sum(row['bytes'] for row in rows)}


def verify():
    assert sha(CANDIDATE / 'candidate-manifest.json') == '5266a975dce4847954f6998688c214a7f8e838497b8a3da9952c17ea2355c333'
    for manifest in [CANDIDATE / 'candidate-manifest.json', CANDIDATE / 'read-only-reference-manifest.json',
                     JOB.parent / 'graph-residual-parity-v1/tool-inputs.json']:
        for name, expected in json.loads(manifest.read_text()).items():
            assert sha(Path(name)) == expected, name
    for name, expected in json.loads((JOB / 'execution-inputs.json').read_text()).items():
        assert sha(Path(name)) == expected, name


def main():
    assert os.environ.get('CIX_RELEASE_LEASE') == '1', 'root scheduler required'
    admission = json.loads((JOB / 'admission.json').read_text())
    assert admission['comment_id'] and admission['other_reservation_bytes'] == 10000000
    verify()
    before = allocated()
    assert before['total_bytes'] + 150000000 + admission['other_reservation_bytes'] <= 4000000000
    assert not OUT.exists(), 'immutable run identity already used'
    OUT.mkdir()
    scratch = OUT / 'scratch'
    evidence = OUT / 'evidence'
    scratch.mkdir()
    evidence.mkdir()
    (OUT / 'before.json').write_text(json.dumps(before, indent=2) + '\n')
    env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C',
           'CIX_GRAPH_SCRATCH': str(scratch), 'CIX_GRAPH_EVIDENCE': str(evidence),
           'CIX_GRAPH_ADMISSION': admission['comment_id']}
    command = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-net', '--unshare-pid',
               '--ro-bind', '/', '/', '--dev-bind', '/dev/null', '/dev/null', '--proc', '/proc',
               '--size', '99999744', '--tmpfs', str(scratch),
               '--bind', str(evidence), str(evidence), '--', '/usr/bin/python3', '-B', str(JOB / 'worker.py')]
    child = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(timeout=172)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate()
        (OUT / 'timeout.txt').write_text('outer namespace exceeded 172 seconds; process group killed\n')
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
    receipt = {'status': 'PASS' if child.returncode == 0 else 'FAILED', 'returncode': child.returncode,
               'admission': admission, 'before': before, 'after': after,
               'tmpfs_bytes': 99999744, 'evidence_cap_bytes': 45000000,
               'cgroup_contract': 'scheduler core 8, 1GB rounded to pages, no swap, CPUQuota=100%, 180s wall',
               'candidate_unchanged': True, 'scratch_after_namespace_teardown': list(scratch.iterdir()),
               'no_product_changes': True, 'scope': 'exact five-module closure only'}
    assert not receipt['scratch_after_namespace_teardown']
    assert after['total_bytes'] + admission['other_reservation_bytes'] <= 4000000000
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'returncode': child.returncode, 'out': str(OUT)}), flush=True)
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
