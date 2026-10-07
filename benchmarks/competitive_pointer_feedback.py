"""Add causal pointer feedback after complete independent restoration."""
import json
from pathlib import Path
import sys
import time
import brotli
import _brotli
from benchmarks import competitive_relocated as parent, ecoff_pointer_delta_probe as framed
from benchmarks.competitive_codec import sha

NAME='CIX competitive pointer-feedback portfolio 13'
MODES=list(range(6))
SOURCES=[__file__,framed.__file__,framed.codec.__file__,framed.codec.locator.__file__,framed.codec.parent.__file__,framed.codec.parent.parent.__file__,framed.codec.parent.parent.base.__file__]


def eligible(data):
    return bool(framed.codec.locator.candidates(data))


def qualify(data,folder,require_complete=True):
    folder=Path(folder);record=folder/'complete.json';row=json.loads(record.read_text());digest=sha(data)
    if (not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member'))
        or row['input_sha256']!=digest or row['restored_sha256']!=digest or row['original_bytes']!=len(data)):
        raise ValueError('pointer input/restoration evidence mismatch')
    if row['mode'] not in MODES or row['backend']!='brotli' or row['brotli_version']!=brotli.__version__:
        raise ValueError('pointer cache policy mismatch')
    binary=Path(_brotli.__file__);binary_hash=sha(binary.read_bytes())
    if binary_hash!=row['backend_sha256']:raise ValueError('pointer backend changed')
    for path,value in row['source_hashes'].items():
        if sha(Path(path).read_bytes())!=value:raise ValueError('pointer source changed')
    frame=(folder/'stream.cixb').read_bytes()
    if len(frame)!=row['physical_bytes'] or sha(frame)!=row['frame_sha256']:raise ValueError('pointer artifact mismatch')
    if frame[:6]!=framed.MAGIC+b'\0':raise ValueError('pointer backend framing mismatch')
    raw,_=framed.codec.transform(data,row['mode'])
    if sha(raw)!=row['transformed_sha256']:raise ValueError('pointer transform reproduction mismatch')
    t=time.perf_counter();restored=framed.decode(frame);elapsed=time.perf_counter()-t
    if restored!=data or sha(binary.read_bytes())!=binary_hash:raise ValueError('pointer fresh restoration/backend mismatch')
    measurement=dict(row,original_decode_seconds=row['decode_seconds'],decode_seconds=elapsed)
    return frame,dict(kind='source-qualified complete artifact; transform recomputed and full standalone decode repeated',
                      measurement=measurement,measurement_path=str(record.resolve()),measurement_sha256=sha(record.read_bytes()),
                      frame_sha256=sha(frame),input_sha256=digest,transformed_sha256=sha(raw),fresh_full_decode=True)


def additions(data,cache=None):
    if not eligible(data):return []
    found={}
    if cache:
        digest=sha(data)
        for record in Path(cache).glob('*/complete.json'):
            row=json.loads(record.read_text());key=row['mode']
            if row.get('input_sha256')==digest and key in MODES:
                if key in found:raise ValueError('duplicate pointer cache candidate')
                found[key]=record.parent
        if set(found)!=set(MODES):raise ValueError('all six complete pointer-feedback candidates required')
    out=[]
    for mode in MODES:
        t=time.perf_counter();proof=None
        if cache:frame,proof=qualify(data,found[mode])
        else:frame,_=framed.encode(data,mode,'brotli')
        out.append((frame,dict(name=f'pointer-feedback-brotli11-mode{mode}',size=len(frame),encode_seconds=time.perf_counter()-t),proof))
    return out


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):
    return framed.decode(frame) if frame[:5]==framed.MAGIC else parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
