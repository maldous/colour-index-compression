#!/usr/bin/env python3
"""Snapshot the qualified Python environment without relying on future pip state."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def snapshot(root):
    rows={}
    for p in sorted(root.rglob('*')):
        relative=str(p.relative_to(root))
        if p.is_symlink():rows[relative]={'symlink':str(p.readlink())}
        elif p.is_file():rows[relative]={'bytes':p.stat().st_size,'sha256':digest(p)}
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    if args.manifest.exists():raise FileExistsError('A frozen snapshot must not be overwritten')
    if not args.destination.exists():shutil.copytree(args.source,args.destination,symlinks=True)
    original=snapshot(args.source);copied=snapshot(args.destination)
    if copied!=original:raise ValueError('Copied Python environment differs from qualified source')
    python=args.destination/'bin/python'
    row=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source=str(args.source),path=str(args.destination),python=str(python),
        python_binary_sha256=digest(python),files=copied,
        note='Identical byte snapshot of the qualified environment. Namespace mounts it read-only; every file and symlink is rechecked before CIX runs. System interpreter binary is separately hashed. Never resolve the command path out of the virtual environment.')
    args.manifest.write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(dict(files=len(copied),python=str(python),python_sha256=row['python_binary_sha256'])))
