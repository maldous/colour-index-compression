"""Add complete section/function pointer constraints to qualified portfolio24."""
import json
from pathlib import Path
import sys
import time
import zlib
from benchmarks import competitive_prediction_v24 as parent
from benchmarks import competitive_successor as successor
from benchmarks import ecoff_section_pointer_probe as framed
from benchmarks.qualified_prediction_paq import POINTER_SOURCES

paq=framed.paq
NAME='CIX competitive section-constrained and online-LSTM portfolio 25'
DEPENDENCIES=[framed.__file__,framed.codec.__file__,framed.codec.uniform.__file__,*POINTER_SOURCES,paq.paq_binary('v215')]
SOURCES=[__file__,successor.__file__,*DEPENDENCIES]


def qualify(data,folder):
    folder=Path(folder);record=folder/'complete.json';row=json.loads(record.read_text());digest=paq.sha(data)
    if (not row.get('round_trip') or not row.get('complete_silesia_member')
        or row['input_sha256']!=digest or row['restored_sha256']!=digest or row['original_bytes']!=len(data)):
        raise ValueError('section complete restoration mismatch')
    if (row['mode'],row['backend'],row['options'])!=(4,'paq','-8'):
        raise ValueError('section representation mismatch')
    hashes={str(Path(p).resolve()):h for p,h in row['source_hashes'].items()}
    # POINTER_SOURCES contains its standalone wrapper, which is not called by
    # this transform. Its other dependencies are all required in the proof.
    required=[p for p in DEPENDENCIES if Path(p).name!='ecoff_pointer_delta_probe.py']
    if any(str(Path(p).resolve()) not in hashes for p in required):raise ValueError('missing section dependency')
    if any(paq.sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('section dependency changed')
    frame=(folder/'stream.cixb').read_bytes()
    if len(frame)!=row['physical_bytes'] or paq.sha(frame)!=row['frame_sha256']:raise ValueError('section frame changed')
    if frame[:6]!=framed.MAGIC+b'\x01':raise ValueError('section frame family/backend mismatch')
    n,pos=framed.vdecode(frame,6)
    if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data):raise ValueError('section framing mismatch')
    if paq.unwrap_paq(frame[pos+4:])[0]!='v215':raise ValueError('section native version mismatch')
    raw,_=framed.codec.transform(data,4)
    if paq.sha(raw)!=row['transformed_sha256'] or framed.codec.inverse(raw)!=data:raise ValueError('section transform reproduction/inversion failed')
    return frame,dict(kind='Exact complete independently decoded section/PAQ frame; current identities checked and transform recomputed/inverted',
        measurement=row,measurement_path=str(record.resolve()),measurement_sha256=paq.sha(record.read_bytes()),
        frame_sha256=paq.sha(frame),input_sha256=digest,transformed_sha256=paq.sha(raw),fresh_full_decode=False)


def additions(data,cache=None):
    if not framed.codec.fields(data,4):return []
    start=time.perf_counter();proof=None
    if cache:frame,proof=qualify(data,cache)
    else:frame,_=framed.encode(data,4,'paq','-8')
    return [(frame,dict(name='section-constraints-paq-v215-8-mode4',size=len(frame),encode_seconds=time.perf_counter()-start),proof)]


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame,selection['selected']=candidate,row['name']
    return frame,selection


def decode(frame):return parent.decode(frame)


if __name__=='__main__':successor.main(sys.modules[__name__])
