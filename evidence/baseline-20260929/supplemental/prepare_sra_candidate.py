#!/usr/bin/env python3
"""Inspect default full-quality SRA export; never confer NNLCB qualification.

This is a source-acquisition investigation, added after the controlled schedule
was frozen. It changes neither the benchmark harness nor any compressor.
Execute with the same exclusive measurement lock as timed runs.
"""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
STORAGE = Path('/home/user/src/cix-baseline-data')
TOOLS = Path('/home/user/src/cix-baseline-tools')
WORK = STORAGE / 'preparation/ERR7091247-normalized-default-20260929'
RECORD = ROOT / 'raw/prepare-D28-normalized-default.json'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    WORK.mkdir(parents=True, exist_ok=False)
    row = dict(started_utc=now(), status='STARTED', dataset_id='D28',
               purpose='Investigate default FASTQ export of full-quality normalized SRA',
               qualification='NOT EXACTLY REPRODUCED; requires independent source-definition review',
               expected_nnlcb_bytes=1926041160, expected_paper_alphabet_size=32,
               script_sha256=digest(Path(__file__)))
    try:
        source = STORAGE / 'sources/ERR7091247.sra'
        archive = TOOLS / 'sratoolkit.3.4.1-ubuntu64.tar.gz'
        row['sources'] = []
        for path, expected in (
            (source, '2fe9f63183a778019cf341f511544227cdbc738b690e72fdfc55b8e847430800'),
            (archive, 'b950362c054765a4184af41947f022f040e94e964862017c0ecb0b0273db3596'),
        ):
            sha = digest(path)
            row['sources'].append(dict(path=str(path), bytes=path.stat().st_size, sha256=sha))
            if sha != expected:
                raise ValueError('Pinned source hash mismatch: ' + str(path))
        if shutil.disk_usage(WORK).free < 8 << 30:
            raise RuntimeError('Need 8 GiB available, including 5 GiB reserve')
        unpacked = WORK / 'tools'
        unpacked.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(unpacked, filter='data')
        toolkit = unpacked / 'sratoolkit.3.4.1-ubuntu64'
        binary = toolkit / 'bin/fastq-dump'
        row['binary_sha256'] = digest(binary)
        for option, name in (('--version', 'version.txt'), ('--help', 'help.txt')):
            command = [str(binary), option]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=30, check=True)
            (WORK / name).write_text(result.stdout)
        output = WORK / 'output'
        output.mkdir()
        command = ['bwrap', '--unshare-user', '--unshare-pid', '--unshare-net', '--die-with-parent',
                   '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
                   '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
                   '--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache',
                   '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
                   '--ro-bind', str(toolkit), '/toolkit',
                   '--ro-bind', str(source), '/source/ERR7091247.sra',
                   '--bind', str(output), '/work', '--chdir', '/work', '--',
                   '/toolkit/bin/fastq-dump', '/source/ERR7091247.sra']
        row['command'] = command
        row['preparation'] = 'Default fastq-dump 3.4.1, local pinned normalized SRA, no content or header options, no network'
        RECORD.write_text(json.dumps(row, indent=2) + '\n')
        with (WORK / 'stdout.log').open('w') as stdout, (WORK / 'stderr.log').open('w') as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=1200)
        row['returncode'] = result.returncode
        if result.returncode:
            raise RuntimeError('fastq-dump failed; see preserved stderr')
        files = list(output.iterdir())
        if len(files) != 1 or files[0].suffix != '.fastq':
            raise RuntimeError('Unexpected output layout; preserve without concatenation')
        counts = collections.Counter()
        sha = hashlib.sha256()
        size = 0
        with files[0].open('rb') as stream:
            while block := stream.read(8 << 20):
                size += len(block)
                sha.update(block)
                counts.update(block)
        row['output'] = dict(path=str(files[0]), bytes=size, sha256=sha.hexdigest(),
                             distinct_byte_values=len(counts),
                             byte_histogram={str(k): v for k, v in sorted(counts.items())})
        row['published_length_matches'] = size == row['expected_nnlcb_bytes']
        row['published_alphabet_matches'] = len(counts) == row['expected_paper_alphabet_size']
        row['status'] = 'PREPARED CANDIDATE; NOT AUTOMATICALLY QUALIFIED'
    except Exception as exc:
        row['status'] = 'FAILED'
        row['error'] = repr(exc)
        raise
    finally:
        row['finished_utc'] = now()
        RECORD.write_text(json.dumps(row, indent=2) + '\n')
        print(json.dumps({k: v for k, v in row.items() if k != 'output'}), flush=True)


if __name__ == '__main__':
    main()
