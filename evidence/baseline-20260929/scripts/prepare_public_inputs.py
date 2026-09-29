#!/usr/bin/env python3
"""Exact extraction only for unambiguously defined canonical single streams.

This deliberately does not guess how NNLCB concatenated multi-file corpora.
"""
import argparse
import bz2
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def copy_stream(reader,destination,max_bytes=None):
    digest=hashlib.sha256();size=0
    partial=destination.with_name(destination.name+'.preparing')
    if destination.exists() or partial.exists():raise FileExistsError('Existing preparation is preserved')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with partial.open('xb') as output:
        while data:=reader.read(8<<20):
            if max_bytes is not None and size+len(data)>max_bytes:raise ValueError('Expanded input exceeds predeclared limit')
            if shutil.disk_usage(destination.parent).free < len(data)+(5<<30):raise OSError('Less than 5 GiB disk reserve')
            output.write(data);digest.update(data);size+=len(data)
    partial.rename(destination)
    return size,digest.hexdigest()


def prepare_zip(name,ident,storage):
    acquired=json.loads((ROOT/'raw'/('acquire-'+name+'.json')).read_text())
    assert acquired['status']=='VERIFIED DOWNLOAD'
    source=storage/'sources'/(name+'.zip')
    with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==acquired['sha256']
    destination=storage/'inputs'/name
    if destination.exists():
        with destination.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        size=destination.stat().st_size
    else:
        with zipfile.ZipFile(source) as archive,archive.open(name) as reader:
            size,digest=copy_stream(reader,destination)
    manifest=ROOT/'manifests/nnlcb-datasets.json';rows=json.loads(manifest.read_text())
    row=next(r for r in rows if r['dataset_id']==ident)
    assert size==row['expected_bytes']
    row.update(compatibility='EXACT',compatibility_explanation='Unmodified named canonical ZIP member from the exact NNLCB URL.',
               path=str(destination),obtained_bytes=size,sha256=digest,source_artifact_sha256=acquired['sha256'],
               preparation=f'python3 scripts/prepare_public_inputs.py {name} --storage {storage}')
    manifest.write_text(json.dumps(rows,indent=2)+'\n')
    return row


def prepare_wikipedia(storage,wait):
    record=ROOT/'raw/acquire-enwiki-20260901.json'
    while not record.exists():
        if not wait:raise RuntimeError('Download has not completed')
        time.sleep(10)
    acquired=json.loads(record.read_text());assert acquired['status']=='VERIFIED DOWNLOAD', acquired
    source=Path(acquired['destination'])
    with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==acquired['sha256']
    destination=storage/'inputs/enwiki-20260901-pages-articles-multistream.xml'
    # BZ2File reads concatenated bzip2 members, preserving the combined XML.
    with bz2.open(source,'rb') as reader:size,digest=copy_stream(reader,destination)
    row=dict(dataset_id='WIKIPEDIA-20260901',name='English Wikipedia pages/articles XML, 2026-09-01',
             snapshot='20260901',evidence_layer='entire modern English Wikipedia',source_artifacts=[acquired],
             path=str(destination),obtained_bytes=size,sha256=digest,
             representation='Complete decompression of all concatenated bzip2 streams in the official combined pages-articles-multistream XML; no filtering or transformation.',
             scope='Wikimedia pages/articles content XML for English Wikipedia. Not full revision histories, media binaries or every administrative namespace.',
             preparation=f'python3 scripts/prepare_public_inputs.py wikipedia --storage {storage}',
             compatibility='Not an NNLCB dataset')
    (ROOT/'manifests/wikipedia-input.json').write_text(json.dumps([row],indent=2)+'\n')
    return row


def prepare_backup(storage):
    """NNLCB's exact linked TRACE archive already contains the named 1GB asset."""
    acquired=json.loads((ROOT/'raw/acquire-D20.json').read_text())
    assert acquired['status']=='VERIFIED DOWNLOAD'
    source=storage/'sources/nnlcb-backup-download.bin'
    with source.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==acquired['sha256']
    destination=storage/'inputs/backup_1GB'
    with tarfile.open(source,'r|gz') as archive:
        found=False
        for member in archive:
            if member.name!='backup_1GB':continue
            assert member.isfile() and member.size==1_000_000_000
            if found:raise ValueError('Duplicate prepared backup member')
            found=True
            if destination.exists():
                with destination.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
                size=destination.stat().st_size
            else:
                with archive.extractfile(member) as reader:
                    size,digest=copy_stream(reader,destination,max_bytes=1_000_000_000)
        assert found and size==1_000_000_000
    manifest=ROOT/'manifests/nnlcb-datasets.json';rows=json.loads(manifest.read_text())
    row=next(r for r in rows if r['dataset_id']=='D20')
    row.update(compatibility='EXACT',
               compatibility_explanation='Unmodified named backup_1GB member already prepared in the exact TRACE archive linked by NNLCB. Its1000000000 bytes match the definition; no new random extraction or concatenation was performed.',
               path=str(destination),obtained_bytes=size,sha256=digest,
               source_artifact_sha256=acquired['sha256'],source_member='backup_1GB',
               preparation=f'python3 scripts/prepare_public_inputs.py backup --storage {storage}')
    manifest.write_text(json.dumps(rows,indent=2)+'\n')
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset',choices=['enwik8','text8','enwik9','wikipedia','backup'])
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--wait',action='store_true')
    args=parser.parse_args()
    if args.dataset=='wikipedia':row=prepare_wikipedia(args.storage,args.wait)
    elif args.dataset=='backup':row=prepare_backup(args.storage)
    else:row=prepare_zip(args.dataset,{'enwik8':'D13','text8':'D14','enwik9':'D21'}[args.dataset],args.storage)
    print(json.dumps(row,indent=2))
