#!/usr/bin/env python3
"""Remove only explicitly listed, SHA-256 verified duplicate CIX restorations.

Run under the shared measurement lock. Inputs, frames, checkpoints and logs are
preserved. An unexpected hash, open file or changing file is never removed.
"""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/user/src/colour-index-compression/benchmark-work/silesia/mozilla')
SHA = '657fc3764b0c75ac9de9623125705831ebbfbe08fed248df73bc2dc66e2a963b'
NAMES = (
    'cix-ecoff-v11-restored-20260928.bin',
    'cix-portfolio19-restored.bin',
    'cix-portfolio18-isolated-restored.bin',
    'cix-relocated-v12-restored-20260928.bin',
    'cix-portfolio15-isolation-restored.bin',
    'cix-pointer-feedback-v13-restored-20260928.bin',
    'cix-symbol-load-v15-restored-20260928.bin',
    'cix-section-pointer-v14-restored-20260928.bin',
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    if digest(SOURCE) != SHA:
        raise RuntimeError('Canonical preserved source did not match')
    if not shutil.which('fuser'):
        raise RuntimeError('Open-file check unavailable')
    receipt = ROOT / 'raw/cleanup-verified-restorations-20260929.json'
    if receipt.exists():
        raise RuntimeError('Existing cleanup receipt; do not overwrite')
    rows = []
    report = dict(source=str(SOURCE), source_sha256=SHA, entries=rows,
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  free_before=shutil.disk_usage(SOURCE.parent).free)
    for name in NAMES:
        path = Path('/tmp') / name
        row = dict(path=str(path), status='NOT REMOVED')
        rows.append(row)
        if path.is_symlink() or not path.is_file():
            row['reason'] = 'Missing or not a regular non-symlink file'
            continue
        before = path.stat()
        row.update(bytes=before.st_size, allocated_bytes=before.st_blocks*512)
        row['sha256'] = digest(path)
        after = path.stat()
        if row['sha256'] != SHA or (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            row['reason'] = 'Hash mismatch or file changed during inspection'
            continue
        result = subprocess.run(['fuser', '-s', '--', str(path)], capture_output=True)
        if result.returncode != 1 or result.stderr:
            row['reason'] = 'Open-file check reported use or uncertainty'
            continue
        row['status'] = 'VERIFIED DUPLICATE; REMOVAL PENDING'
        receipt.write_text(json.dumps(report, indent=2)+'\n')
        path.unlink()
        row['status'] = 'REMOVED VERIFIED DUPLICATE'
        receipt.write_text(json.dumps(report, indent=2)+'\n')
    report.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  removed_logical_bytes=sum(r.get('bytes',0) for r in rows if r['status']=='REMOVED VERIFIED DUPLICATE'),
                  free_after=shutil.disk_usage(SOURCE.parent).free)
    receipt.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
