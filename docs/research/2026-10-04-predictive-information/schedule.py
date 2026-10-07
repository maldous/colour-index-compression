"""Root-owned bounded CPI1 phases using the existing global scheduler lease."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
BASE = ROOT / 'benchmark-work/predictive-information'
sys.path.insert(0, str(ROOT))
from benchmarks import cix_rust_perf_audit as audit
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build', 'selfcheck', 'development', 'train', 'heldout', 'evaluate', 'validate', 'verify'])
    parser.add_argument('--attempt', default='v1')
    args = parser.parse_args()
    freeze = json.loads((AREA / 'freeze.json').read_text())
    for relative, expected in freeze['hashes'].items():
        if not relative.startswith('git:'):
            assert audit.sha256(ROOT / relative) == expected, relative
    raw = AREA / 'raw'
    raw.mkdir(exist_ok=True)
    scheduler = WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=2147483648, max_temp_bytes=536870912)
    lock = scheduler._wave_lock_path().open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    leases = scheduler._lease_cores([{'physical_core': [_core(8)]}])
    original_run = subprocess.run
    def quota(command, *positional, **keywords):
        if isinstance(command, list) and command[:3] == ['sudo', '-n', 'systemd-run']:
            command = command[:3] + ['--property=CPUQuota=100%'] + command[3:]
        return original_run(command, *positional, **keywords)
    subprocess.run = quota
    deps = ROOT / 'benchmark-work/release-d3a2/target/release-lto/deps'
    command = ['/usr/bin/env', 'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1', 'CIX_PREDICTIVE_LEASE=1']
    if args.phase == 'build':
        command += [f'CIX_TRACE_SOURCE={BASE}/source', '/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc',
                    '--edition=2021', '-O', '-A', 'dead_code', str(ROOT / 'rust/cix-native/experiments/predictive-information/trace.rs'),
                    '--extern', f'num_bigint={deps}/libnum_bigint-98d97ecffaac23ba.rlib', '--extern', f'num_traits={deps}/libnum_traits-62d94157db5bd7b9.rlib',
                    '-L', f'dependency={deps}', '-o', str(BASE / 'build/trace')]
    elif args.phase == 'selfcheck':
        command += [str(BASE / 'build/trace'), 'selfcheck']
    else:
        script = 'verify.py' if args.phase == 'verify' else 'run.py' if args.phase in ['development', 'heldout'] else 'analyse.py'
        command += ['/usr/bin/python3', str(AREA / script), args.phase]
    wall = 300 if args.phase in ['build', 'selfcheck', 'validate'] else 1200 if args.phase in ['development', 'heldout'] else 600
    budget = {'wall_seconds': wall, 'max_rss_bytes': 2147483648, 'max_temp_bytes': 536870912}
    unit = 'cix-cpi1-' + args.phase + '-' + args.attempt
    cgroup = raw / (unit + '.cgroup')
    wrapped = audit.affinity_wrapped(['/usr/bin/time', '-v', '-o', str(raw / (unit + '.time')), *command], raw / (unit + '.affinity'), cgroup)
    try:
        result = audit.execute_phase(unit=unit, command=wrapped, work=BASE, destination=raw, budget=budget, cpu=[8], inaccessible=[], input_bytes=0)
        audit.write_json(raw / (unit + '.result.json'), result)
        assert audit.phase_ok(result) and audit.cgroup_ok(cgroup.read_text(), [8], budget), result
    finally:
        for lease in leases:
            lease.close()
        lock.close()


if __name__ == '__main__':
    main()
