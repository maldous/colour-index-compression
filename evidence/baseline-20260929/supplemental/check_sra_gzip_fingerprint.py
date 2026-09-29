#!/usr/bin/env python3
"""Source-identification diagnostic, not a baseline performance measurement.

A matching rounded compressed size is corroborating evidence, never proof of
byte-for-byte NNLCB equivalence. No CIX configuration or input is changed.
Run with the shared measurement lock. Retain hashes and remove verified scratch.
"""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT/'raw/D28-normalized-gzip-fingerprint.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    if RECORD.exists():
        raise RuntimeError('Existing diagnostic; do not overwrite or select a favorable repeat')
    prep=json.loads((ROOT/'raw/prepare-D28-normalized-default.json').read_text())
    source=Path(prep['output']['path'])
    binary=next(r for r in json.loads((ROOT/'manifests/compressor-binaries.json').read_text()) if r['algorithm']=='gzip')
    assert sha(source)==prep['output']['sha256']
    assert sha(Path(binary['path']))==binary['sha256']
    archive=source.parent/'source-fingerprint.gz'
    if archive.exists():
        raise RuntimeError('Unexpected existing diagnostic archive')
    row=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='STARTED',
             purpose='NNLCB source fingerprint only; excluded from baseline performance tables',
             source=prep['output'],compressor_identity=binary,
             command=[binary['path'],'-9','-n','-c',str(source)],timeout_seconds=1200,
             script_sha256=sha(Path(__file__)))
    try:
        RECORD.write_text(json.dumps(row,indent=2)+'\n')
        with archive.open('xb') as out:
            result=subprocess.run(row['command'],stdout=out,stderr=subprocess.PIPE,timeout=1200)
        row['returncode']=result.returncode
        row['stderr']=result.stderr.decode(errors='replace')
        if result.returncode:
            raise RuntimeError('gzip did not complete')
        row['compressed_bytes']=archive.stat().st_size
        row['compressed_sha256']=sha(archive)
        with gzip.open(archive,'rb') as stream:
            row['decompressed_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
        if row['decompressed_sha256'] != prep['output']['sha256']:
            raise RuntimeError('Source diagnostic restoration mismatch')
        refs=json.loads((ROOT/'tables/nnlcb-published-per-dataset.json').read_text())
        reference=next(r for r in refs if r['dataset_id']=='D28' and r['algorithm']=='GZip')
        row['published_reference']=reference
        row['candidate_CS_MiB']=row['compressed_bytes']/1048576
        row['delta_from_published_rounded_CS_bytes']=row['compressed_bytes']-reference['CS_reported_MegaBytes']*1048576
        row['within_one_reported_MiB_millesimal']=abs(row['delta_from_published_rounded_CS_bytes'])<1048.576
        row['interpretation']='Corroborating or contradictory source evidence only. Different filename/header/version choices may affect gzip size; matching a rounded size does not establish identical inputs.'
        row['status']='VERIFIED SOURCE DIAGNOSTIC; NOT A BASELINE RESULT'
        archive.unlink()
        row['archive_retention']='Verified scratch removed after hashing and independent gzip reconstruction; pinned source and commands retained'
    except Exception as exc:
        row['status']='FAILED'
        row['error']=repr(exc)
        raise
    finally:
        row['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        RECORD.write_text(json.dumps(row,indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k not in ('source','compressor_identity')}),flush=True)


if __name__=='__main__':
    main()
