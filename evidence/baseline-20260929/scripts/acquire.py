#!/usr/bin/env python3
"""Download public evidence with resumable curl and hash every received byte.

Acquisition is never part of measured compression time. A completed file is
accepted only after expected length and any supplied digests have been checked.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def hashes(path):
    algorithms = {name: hashlib.new(name) for name in ('sha256', 'sha1', 'md5')}
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 << 20), b''):
            for algorithm in algorithms.values():
                algorithm.update(block)
    return {name: algorithm.hexdigest() for name, algorithm in algorithms.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url')
    parser.add_argument('output', type=Path)
    parser.add_argument('--bytes', type=int)
    parser.add_argument('--sha256')
    parser.add_argument('--sha1')
    parser.add_argument('--md5')
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output.with_name(args.output.name + '.part')
    record = dict(url=args.url, destination=str(args.output.absolute()),
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  expected_bytes=args.bytes,
                  expected_hashes={x: getattr(args, x) for x in ('sha256', 'sha1', 'md5') if getattr(args, x)})
    try:
        if not args.output.exists():
            required = max(0, (args.bytes or 0) - (partial.stat().st_size if partial.exists() else 0))
            free = shutil.disk_usage(args.output.parent).free
            if required + (5 << 30) > free:
                raise RuntimeError(f'Insufficient disk: {free} available, {required} additional bytes plus 5 GiB reserve required')
            command = ['curl', '--fail', '--location', '--continue-at', '-',
                       '--retry', '5', '--retry-delay', '5', '--connect-timeout', '30',
                       '--speed-time', '180', '--speed-limit', '1024',
                       '--user-agent', 'Mozilla/5.0', '--output', str(partial), args.url]
            record['command'] = command
            with args.record.with_suffix('.download.log').open('a') as log:
                subprocess.run(command, stdout=log, stderr=log, check=True)
            target = partial
        else:
            target = args.output
            record['reused_existing_download'] = True
        record['bytes'] = target.stat().st_size
        record.update(hashes(target))
        if args.bytes is not None and record['bytes'] != args.bytes:
            raise ValueError('Source length mismatch')
        for name, expected in record['expected_hashes'].items():
            if record[name] != expected:
                raise ValueError(f'Source {name} mismatch')
        if target == partial:
            os.rename(partial, args.output)
        record['status'] = 'VERIFIED DOWNLOAD'
    except Exception as exc:
        record['status'] = 'FAILED'
        record['error'] = repr(exc)
        raise
    finally:
        record['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        args.record.write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
