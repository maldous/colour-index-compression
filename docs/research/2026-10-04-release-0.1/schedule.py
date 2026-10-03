"""Root-owned release phases with existing global WaveScheduler lease."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks import cix_rust_perf_audit as audit
from benchmarks import hutter_bounded_runner as bounded

def live_directory_bytes(root):
    # Build tools atomically rename/remove files while the supervisor samples.
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except FileNotFoundError:
            continue
    return total

bounded.directory_bytes = live_directory_bytes
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core


def run(spec):
    name = spec['id']
    assert name.replace('-', '').isalnum()
    cpus = spec.get('cpus', [8])
    assert 0 < len(cpus) <= 4 and len({_core(c) for c in cpus}) == len(cpus)
    budget = dict(wall_seconds=spec.get('wall_seconds', 1200),
                  max_rss_bytes=spec.get('memory_bytes', 6_000_000_000),
                  max_temp_bytes=spec.get('temp_bytes', 4_000_000_000))
    assert budget['max_rss_bytes'] <= 12_000_000_000
    assert budget['max_temp_bytes'] <= 4_000_000_000
    # Linux memory.max rounds down to page size. Record the enforced value.
    budget['max_rss_bytes'] = budget['max_rss_bytes'] // 4096 * 4096
    raw = AREA / 'raw' / name
    raw.mkdir(parents=True, exist_ok=False)
    work = Path(spec['work'])
    work.mkdir(parents=True, exist_ok=True)
    scheduler = WaveScheduler(ROOT, max_jobs=1,
        max_memory_bytes=budget['max_rss_bytes'], max_temp_bytes=budget['max_temp_bytes'])
    lock = scheduler._wave_lock_path().open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    leases = scheduler._lease_cores([{'physical_core': [_core(c) for c in cpus]}])
    original_run = subprocess.run
    def quota(command, *positional, **keywords):
        if isinstance(command, list) and command[:3] == ['sudo', '-n', 'systemd-run']:
            command = command[:3] + [f'--property=CPUQuota={len(cpus)*100}%'] + command[3:]
        return original_run(command, *positional, **keywords)
    subprocess.run = quota
    unit = 'cix-rel01-' + name
    command = ['/usr/bin/env', 'OPENBLAS_NUM_THREADS=1', 'OMP_NUM_THREADS=1',
               'CIX_RELEASE_LEASE=1', *spec.get('env', []), *spec['command']]
    wrapped = audit.affinity_wrapped(['/usr/bin/time', '-v', '-o', str(raw/'time.txt'), *command], raw/'affinity.txt', raw/'cgroup.txt')
    audit.write_json(raw/'spec.json', spec)
    try:
        result = audit.execute_phase(unit=unit, command=wrapped, work=work,
            destination=raw, budget=budget, cpu=cpus, inaccessible=[], input_bytes=spec.get('input_bytes', 0))
        result['cgroup_verified'] = audit.cgroup_ok((raw/'cgroup.txt').read_text(), cpus, budget)
        audit.write_json(raw/'result.json', result)
        print(json.dumps(result), flush=True)
        return 0 if audit.phase_ok(result) and result['cgroup_verified'] else 1
    finally:
        # Never release a global lease while a child survives a supervisor error.
        original_run(["sudo", "-n", "systemctl", "stop", unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        for lease in leases:
            lease.close()
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('spec')
    args = parser.parse_args()
    sys.exit(run(json.loads(Path(args.spec).read_text())))
