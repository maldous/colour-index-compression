"""Finish the current benchmark, then stop its queue under its exclusive lock.

This is a one-shot response to the user's Hutter-only mission replacement.
It never modifies the frozen harness, kills a running measurement, or deletes
payloads. A successor created while waiting for the lock is retained as NOT RUN.
"""
import datetime
import fcntl
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUN = Path('/home/user/src/cix-baseline-runs/controlled-v1')
UNIT = 'cix-evidence-baseline-20260929.service'
EXPECTED_INVOCATION = '8736a2b36f0640a0a6e96e57365b8645'
CURRENT = RUN / 'D1/paq8px-r1/result.json'
RECEIPT = ROOT / 'raw/hutter-only-baseline-stop-20260929.json'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def properties():
    output = subprocess.check_output(['systemctl', '--user', 'show', UNIT,
        '--property=MainPID,InvocationID,ActiveState,SubState'], text=True)
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def write(path, value):
    tmp = path.with_suffix('.writing')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def main():
    if RECEIPT.exists():
        raise RuntimeError('Preserve the existing receipt; no implicit repeat')
    before = properties()
    if before.get('InvocationID') != EXPECTED_INVOCATION:
        raise RuntimeError('Unexpected service invocation; manual review required')
    state = dict(requested_utc=now(), status='WAITING FOR ATOMIC BENCHMARK',
        reason='User replaced previous competition and broad baseline with Hutter Prize only',
        service_before=before, current_result=str(CURRENT))
    write(RECEIPT, state)
    with (ROOT / 'raw/measurement.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = json.loads(CURRENT.read_text())
        if not current.get('finished_utc') or current['status'] == 'STARTED':
            raise RuntimeError('Atomic result is not finalized; do not stop service')
        state['atomic_result'] = current
        current_service = properties()
        if current_service.get('MainPID') != '0':
            if current_service.get('InvocationID') != EXPECTED_INVOCATION:
                raise RuntimeError('Service changed while waiting')
            # No benchmark can be running while this lock is held. Stop the
            # scheduler, including a successor waiting for this same lock.
            subprocess.run(['systemctl', '--user', 'stop', UNIT], check=True)
        state['service_after'] = properties()
        if state['service_after'].get('MainPID') != '0':
            raise RuntimeError('Service did not stop')
        state['unstarted_successors'] = []
        for result_path in sorted(RUN.glob('D*/*/result.json')):
            if 'interrupted' in str(result_path):
                continue
            result = json.loads(result_path.read_text())
            if result.get('status') != 'STARTED':
                continue
            # A stopped successor must have no measured phase or archive.
            if any((result_path.parent / name).exists() for name in
                   ('encode.timing.json', 'decode.timing.json', 'archive.bin', 'archive.zpaq')):
                raise RuntimeError('Unexpected partial successor; preserve and review')
            state['unstarted_successors'].append(dict(path=str(result_path), original=result))
            result.update(status='NOT RUN', finished_utc=now(),
                failure_reason='User switched exclusively to Hutter Prize before this measurement began')
            write(result_path, result)
        state.update(status='STOPPED AT SAFE CHECKPOINT', finished_utc=now())
        write(RECEIPT, state)
        write(RUN / 'suite-state.json', dict(status=state['status'], updated_utc=now(),
            reason=state['reason'], last_completed_result=str(CURRENT),
            automatic_resume=False, receipt=str(RECEIPT)))
    print(json.dumps({key: state[key] for key in ('status', 'finished_utc')}))


if __name__ == '__main__':
    main()
