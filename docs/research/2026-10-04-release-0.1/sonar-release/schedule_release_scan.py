#!/usr/bin/env python3
"""Root-only scheduler for the hash-bound CIX 0.1 export Sonar scan."""
import fcntl
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/user/src/colour-index-compression')
EXPORT = Path('/home/user/src/cix-0.1-release')
AREA = ROOT / 'docs/research/2026-10-04-release-0.1/sonar-release'
HARNESS = AREA / 'run_release_scan.py'
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core

spec = importlib.util.spec_from_file_location('release_sonar_harness', HARNESS)
harness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(harness)

if not EXPORT.is_dir() or not (EXPORT / 'Cargo.toml').is_file():
    raise RuntimeError('standalone release export is absent')
source_tree, source_files = harness.source_tree_digest(EXPORT)
lease_path = AREA / 'lease.json'
clippy_dir = AREA.parent / 'raw/cargo-clippy-v2'
clippy_path = clippy_dir / 'cix-rel01-cargo-clippy-v2.stdout.log'
clippy_result = clippy_dir / 'result.json'
output_path = AREA / 'run-v1'
if output_path.exists():
    raise RuntimeError('refusing to overwrite an existing release Sonar receipt')
if not clippy_path.is_file() or not clippy_result.is_file():
    raise RuntimeError('missing root-scheduled clean Clippy v2 receipt')
if json.loads(clippy_result.read_text()).get('exit_code') != 0:
    raise RuntimeError('root-scheduled Clippy v2 did not pass')

scheduler = WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=6_442_450_944, max_temp_bytes=4_000_000_000)
scheduler.state.mkdir(exist_ok=True)
lock = scheduler._wave_lock_path().open('a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
leases = scheduler._lease_cores([{'physical_core': [_core(cpu) for cpu in (24, 25)]}])
try:
    lease_path.write_text(json.dumps({
        'status': 'ACTIVE',
        'reserved_cpus': [24, 25],
        'memory_reserved': 6_442_450_944,
        'temporary_max': 4_000_000_000,
        'swap': 0,
        'source_tree': source_tree,
        'source_file_count': len(source_files),
        'clippy_receipt': str(clippy_result),
        'clippy_raw_sha256': harness.digest(clippy_path),
    }, indent=2) + '\n')
    if harness.source_tree_digest(EXPORT)[0] != source_tree:
        raise RuntimeError('release export changed before Sonar dispatch')
    scan = subprocess.run(
        [
            sys.executable, str(HARNESS),
            '--lease', str(lease_path),
            '--source', str(EXPORT),
            '--expected-tree', source_tree,
            '--clippy-json', str(clippy_path),
            '--out', str(output_path),
        ],
        stdout=(AREA / 'launch-v1.stdout.log').open('w'),
        stderr=(AREA / 'launch-v1.stderr.log').open('w'),
        timeout=900,
    )
    (AREA / 'launch-v1-result.json').write_text(json.dumps({'exit': scan.returncode}) + '\n')
    if scan.returncode != 0:
        raise RuntimeError('release Sonar scan failed')
finally:
    subprocess.run(
        ['docker', 'stop', 'cix-scanner-release-0-1', 'cix-sonarqube-release-0-1'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    lease_path.write_text(json.dumps({'status': 'RELEASED'}) + '\n')
    for lease in leases:
        lease.close()
    lock.close()
