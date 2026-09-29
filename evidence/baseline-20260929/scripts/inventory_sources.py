#!/usr/bin/env python3
"""Inspect acquired public assets without guessing concatenation or extraction.

Tar/ZIP inventories preserve physical member order. A gzip inventory measures
the complete concatenated uncompressed stream, with a byte histogram and hash.
Nothing here confers NNLCB compatibility merely from a matching total length.
"""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile


def inventory(path,kind):
    with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    result=dict(path=str(path.absolute()),source_bytes=path.stat().st_size,source_sha256=sha,
        inspected_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),kind=kind)
    if kind=='gzip':
        h=hashlib.sha256();n=0;counts=Counter()
        with gzip.open(path,'rb') as f:
            while b:=f.read(8<<20):
                h.update(b);n+=len(b);counts.update(b)
        result.update(uncompressed_bytes=n,uncompressed_sha256=h.hexdigest(),
            distinct_byte_values=len(counts),byte_histogram={str(k):v for k,v in sorted(counts.items())})
    elif kind=='zip':
        with zipfile.ZipFile(path) as z:
            result['members']=[dict(name=x.filename,bytes=x.file_size,is_file=not x.is_dir()) for x in z.infolist()]
    elif kind=='tar':
        with tarfile.open(path,'r|*') as t:
            result['members']=[dict(name=x.name,bytes=x.size,is_file=x.isfile()) for x in t]
    if 'members' in result:
        result['sum_regular_member_bytes']=sum(m['bytes'] for m in result['members'] if m['is_file'])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--kind',choices=['zip','tar','gzip'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=inventory(args.source,args.kind)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('members','byte_histogram')}))
