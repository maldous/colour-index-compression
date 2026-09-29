"""Measure the unchanged frozen competitive CLI on canonical enwik9.

This harness does not change codec selection, consult benchmark caches, or
claim Prize eligibility. Each phase includes normal input/output and encode
includes the CLI's existing internal verification. Independent decode follows.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

CANONICAL_SHA = '159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def rss_tree(pid):
    pending, seen, total = [pid], set(), 0
    while pending:
        p = pending.pop()
        if p in seen:
            continue
        seen.add(p)
        try:
            for line in Path(f'/proc/{p}/status').read_text().splitlines():
                if line.startswith('VmRSS:'):
                    total += int(line.split()[1]) * 1024
            pending.extend(map(int, Path(f'/proc/{p}/task/{p}/children').read_text().split()))
        except (OSError, ValueError):
            pass
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--python', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--freeze-manifest', type=Path, required=True)
    p.add_argument('--phase-timeout', type=int, default=259200)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    temp = a.output / 'temporary'
    temp.mkdir()
    archive, restored = a.output / 'enwik9.cix', a.output / 'enwik9.restored'
    frozen = json.loads(a.freeze_manifest.read_text())
    record = dict(status='PREFLIGHT', created_at=now(), source_commit=frozen['source_commit'],
        policy='unchanged CIX competitive portfolio 26', input_bytes=a.source.stat().st_size,
        input_sha256=None, full_round_trip=False, prize_score_bytes=None,
        phase_timeout_seconds=a.phase_timeout, cpu_affinity=sorted(os.sched_getaffinity(0)),
        resources='one CPU; cgroup MemoryMax 10000000000; swap disabled',
        timing_scope='CLI encode includes existing internal full decode; external decode measured separately',
        package_status='not yet a self-contained licensed public Hutter submission', phases=[])
    save(a.output / 'status.json', record)
    try:
        if record['input_bytes'] != 1000000000 or digest(a.source) != CANONICAL_SHA:
            raise ValueError('canonical enwik9 identity mismatch')
        record['input_sha256'] = CANONICAL_SHA
        for rel, expected in frozen['runtime_files'].items():
            if digest(a.runtime / rel) != expected:
                raise ValueError(f'frozen runtime changed: {rel}')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1',
                   TMPDIR=str(temp), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
        for phase, src, dest in [('encode', a.source, archive), ('decode', archive, restored)]:
            command = [str(a.python), '-m', 'benchmarks.competitive_cli', phase, str(src), str(dest)]
            timing = a.output / f'{phase}.time'
            timed = ['/usr/bin/time', '-f', 'wall_seconds=%e\nuser_seconds=%U\nsystem_seconds=%S\npeak_rss_kib=%M\ncpu_percent=%P\nexit_status=%x', '-o', str(timing), *command]
            report = dict(phase=phase, started_at=now(), command=command, completed=False,
                          peak_sampled_tree_rss_bytes=0, peak_sampled_temp_bytes=0)
            record['status'] = phase.upper() + '_RUNNING'
            record['phases'].append(report)
            save(a.output / 'status.json', record)
            start = time.monotonic()
            last_write = 0
            with (a.output / f'{phase}.json').open('xb') as out, (a.output / f'{phase}.stderr').open('xb') as err:
                process = subprocess.Popen(timed, cwd=a.runtime, env=env, stdout=out, stderr=err, start_new_session=True)
                report['pid'] = process.pid
                while process.poll() is None:
                    elapsed = time.monotonic() - start
                    report['peak_sampled_tree_rss_bytes'] = max(report['peak_sampled_tree_rss_bytes'], rss_tree(process.pid))
                    report['peak_sampled_temp_bytes'] = max(report['peak_sampled_temp_bytes'], sum(x.stat().st_size for x in temp.rglob('*') if x.is_file()))
                    if elapsed > a.phase_timeout or shutil.disk_usage(a.output).free < 10 * (1 << 30):
                        report['limit_reason'] = 'phase timeout' if elapsed > a.phase_timeout else 'less than 10 GiB free disk'
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                        break
                    if elapsed - last_write >= 30:
                        report['elapsed_seconds'] = elapsed
                        report['observed_at'] = now()
                        save(a.output / 'status.json', record)
                        last_write = elapsed
                    time.sleep(1)
                report['exit_code'] = process.wait()
            report['wall_seconds'] = time.monotonic() - start
            report['finished_at'] = now()
            report['completed'] = report['exit_code'] == 0 and 'limit_reason' not in report
            save(a.output / f'{phase}-measurement.json', report)
            if not report['completed']:
                raise RuntimeError(f'{phase} failed: {report}')
            report['output_bytes'] = dest.stat().st_size
            report['output_sha256'] = digest(dest)
            save(a.output / f'{phase}-measurement.json', report)
            save(a.output / 'status.json', record)
        if restored.stat().st_size != 1000000000 or digest(restored) != CANONICAL_SHA:
            raise ValueError('independent complete decode hash mismatch')
        for rel, expected in frozen['runtime_files'].items():
            if digest(a.runtime / rel) != expected:
                raise ValueError(f'frozen runtime changed during run: {rel}')
        record.update(status='VERIFIED_COMPLETE_ARCHIVE', completed_at=now(), full_round_trip=True,
            archive_bytes=archive.stat().st_size, archive_sha256=digest(archive),
            restored_sha256=CANONICAL_SHA, compressed_percent=archive.stat().st_size()/10000000)
        save(a.output / 'complete.json', record)
        save(a.output / 'status.json', record)
    except BaseException as exc:
        record.update(status='FAILED', failed_at=now(), error=repr(exc))
        save(a.output / 'failure.json', record)
        save(a.output / 'status.json', record)
        raise


if __name__ == '__main__':
    main()
