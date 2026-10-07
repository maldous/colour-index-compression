#!/usr/bin/env python3
"""Execute inside a bounded tmpfs; export and verify a bounded recovery bundle."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tarfile

JOB = Path(__file__).resolve().parent
SCRATCH = Path(os.environ['CIX_CHECK_SCRATCH'])
EVIDENCE = Path(os.environ['CIX_CHECK_EVIDENCE'])
CAP = 18000000


def allocated():
    seen = set()
    total = 0
    for p in [EVIDENCE, *EVIDENCE.rglob('*')]:
        s = p.lstat()
        key = (s.st_dev, s.st_ino)
        if key not in seen:
            total += s.st_blocks * 512
            seen.add(key)
    return total


def write(name, data):
    assert len(data) <= 1000000
    assert allocated() + ((len(data) + 4095) // 4096 + 2) * 4096 <= CAP - 1000000
    (EVIDENCE / name).write_bytes(data)


class BoundedArchive:
    def __init__(self, target, cap):
        self.file = target.open('xb')
        self.cap = cap
        self.count = 0

    def write(self, data):
        if self.count + len(data) > self.cap:
            raise RuntimeError('compressed recovery bundle exceeds reserved bytes')
        n = self.file.write(data)
        self.count += n
        return n

    def flush(self):
        self.file.flush()

    def close(self):
        self.file.close()


def main():
    # A mount of the requested size must exist before the resolver runs.
    stat = os.statvfs(SCRATCH)
    assert stat.f_blocks * stat.f_frsize <= 170000000
    status = {'scope': 'remaining actual CLI and focused library test qualification', 'artifact_export': 'not_started'}
    sys.argv = [str(JOB / 'scheduled_recipe.py'), '--root-admission', os.environ['CIX_CHECK_ADMISSION']]
    code = 1
    try:
        runpy.run_path(str(JOB / 'scheduled_recipe.py'), run_name='__main__')
        code = 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    except BaseException as e:
        status['launch_error'] = repr(e)
    run = SCRATCH / 'run'
    try:
        files = {}
        for p in sorted(run.rglob('*')):
            if p.is_file() and not p.is_symlink():
                h = hashlib.sha256()
                with p.open('rb') as f:
                    for block in iter(lambda: f.read(1048576), b''):
                        h.update(block)
                files[str(p.relative_to(run))] = {'sha256': h.hexdigest(), 'bytes': p.stat().st_size}
        write('artifact-manifest.json', (json.dumps(files, indent=2) + '\n').encode())
        result = run / 'result.json'
        if result.exists():
            write('result.json', result.read_bytes())
        for name in ['activated-artifacts.json','build-script-results.json','isolated-Cargo.lock']:
            p = run / name
            if p.exists():
                write(name, p.read_bytes())
        # Always keep small raw logs directly accessible, even if bundling fails.
        for p in sorted(run.glob('*.log')):
            write(p.name, p.read_bytes())
        target = EVIDENCE / 'scratch-recovery.tar.gz'
        sink = BoundedArchive(target, min(17000000, CAP - allocated() - 1000000))
        try:
            with gzip.GzipFile(filename='', mode='wb', fileobj=sink, compresslevel=1, mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode='w|') as tar:
                    tar.add(run, arcname='run', recursive=True)
        finally:
            sink.close()
        found = {}
        with tarfile.open(target, 'r:gz') as tar:
            for member in tar:
                if member.isfile() or member.islnk():
                    f = tar.extractfile(member)
                    h = hashlib.sha256()
                    size = 0
                    for block in iter(lambda: f.read(1048576), b''):
                        h.update(block)
                        size += len(block)
                    found[str(Path(member.name).relative_to('run'))] = {'sha256': h.hexdigest(), 'bytes': size}
        assert found == files, 'recovery bundle does not reproduce scratch files'
        status.update(artifact_export='verified', archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                      archive_bytes=target.stat().st_size, files=len(files))
    except BaseException as e:
        status.update(artifact_export='FAILED', export_error=repr(e))
        code = 1
    status.update(exit_code=code, evidence_allocated_bytes=allocated())
    write('export-receipt.json', (json.dumps(status, indent=2) + '\n').encode())
    assert allocated() <= CAP
    print(json.dumps(status), flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
