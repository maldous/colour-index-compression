"""Add bounded PAQ trials to inputs without the database-specific candidate.

The size/structure gate is an encoder compute policy. It uses no filename or
corpus hash. Optional caches must prove complete independent extraction; the
ordinary encoder computes PAQ directly from the input.
"""
import json
import sys
import time
from pathlib import Path
from benchmarks import competitive_chemical as parent
from benchmarks import competitive_database_portfolio as database
from benchmarks import competitive_codec as paq
from benchmarks import paq_reference_run as reference

NAME='CIX competitive structural/bounded-PAQ portfolio 7'
SOURCES=[__file__,reference.__file__]
MAX_BYTES=12<<20


def eligible(data):return len(data)<=MAX_BYTES and not database.recognizes(data)


def qualify(data,root):
    digest=paq.sha(data);matches=[]
    for record in Path(root).glob('*/result.json'):
        row=json.loads(record.read_text())
        if row['identity']['input_sha256']==digest:matches.append((record,row))
    if len(matches)!=1:raise ValueError('one complete PAQ cache entry required for this input')
    record,row=matches[0];policy=row['identity']['policy']
    if (policy['version'],policy['options'],policy['simd'])!=('v216','-8','AVX2'):raise ValueError('PAQ cache policy mismatch')
    if (not row['round_trip'] or row['restored_sha256']!=digest or row['original']!=len(data)
        or row['identity']['original']!=len(data)):raise ValueError('PAQ extraction evidence mismatch')
    if paq.sha(Path(paq.paq_binary('v216')).read_bytes())!=policy['binary_sha256']:raise ValueError('PAQ backend changed')
    if paq.sha(Path(reference.__file__).read_bytes())!=policy['runner_sha256']:raise ValueError('PAQ reference verifier changed')
    original=(record.parent/'stream.paq8px216').read_bytes()
    if len(original)!=row['size'] or paq.sha(original)!=row['archive_sha256']:raise ValueError('PAQ archive changed')
    frame=paq.wrap_paq(original,'v216')
    if paq.unwrap_paq(frame)!=('v216',original) or len(frame)!=len(original):raise ValueError('PAQ header substitution changed payload')
    measurement=dict(row,decode_seconds=row['decode']['wall_seconds'],encode_seconds=row['encode']['wall_seconds'])
    proof=dict(kind='complete PAQ extraction reused; six-byte wrapper inverted to the identical archive',
        measurement=measurement,measurement_path=str(record.resolve()),measurement_sha256=paq.sha(record.read_bytes()),
        frame_sha256=paq.sha(frame),input_sha256=digest,archive_payload_unchanged=True,
        structural_stage_recomputed_and_inverted='only the fixed six-byte CIX/PAQ header substitution')
    return frame,proof


def additions(data,cache=None):
    if not eligible(data):return []
    t=time.perf_counter();proof=None
    if cache:frame,proof=qualify(data,cache)
    else:frame=paq.encode_paq(data,'v216','-8')
    return [(frame,dict(name='paq-v216-8-under-12MiB-nondatabase',size=len(frame),encode_seconds=time.perf_counter()-t),proof)]


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):return parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
