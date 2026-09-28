"""Portfolio 19: qualified CIX structure plus reversible PAQ filter candidates."""
import json
from pathlib import Path
import sys
import time
import brotli
import _brotli
from benchmarks import competitive_pdata_symbols as parent, ecoff_filtered as framed
from benchmarks.competitive_codec import sha, paq_binary

NAME='CIX competitive filtered structural portfolio 19'
MODES=[0,1,2]
SOURCES=[__file__,framed.__file__,framed.native.__file__,*parent.SOURCES,
         'benchmarks/build_paq_store_state.py',str(framed.FORK),
         str(framed.ROOT/'benchmark-work/references/paq8px-cix-store-state/provenance.json')]


def eligible(data):return parent.eligible(data)


def qualify(data,folder,require_complete=True):
    folder=Path(folder);record=folder/'complete.json';row=json.loads(record.read_text());digest=sha(data)
    if (not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member'))
        or row['input_sha256']!=digest or row['restored_sha256']!=digest or row['original_bytes']!=len(data)):
        raise ValueError('filtered input/restoration evidence mismatch')
    if row['mode'] not in MODES or row['brotli_version']!=brotli.__version__:raise ValueError('filtered policy mismatch')
    required=[framed.__file__,framed.native.__file__,framed.FORK,paq_binary('v216'),_brotli.__file__,
              *parent.SOURCES,'benchmarks/build_paq_store_state.py','cix/multinomial.py',
              framed.ROOT/'benchmark-work/references/paq8px-cix-store-state/provenance.json']
    hashes={str(Path(p).resolve()):h for p,h in row['source_hashes'].items()}
    if any(str(Path(p).resolve()) not in hashes for p in required):raise ValueError('missing filtered dependency proof')
    if any(sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('filtered dependency changed')
    frame=(folder/'stream.cixb').read_bytes()
    if len(frame)!=row['physical_bytes'] or sha(frame)!=row['frame_sha256']:raise ValueError('filtered artifact mismatch')
    if frame[:6]!=framed.MAGIC+bytes([row['mode']]):raise ValueError('filtered mode mismatch')
    raw=framed.structure.transform(data,1)[0] if row['mode']!=2 else data
    if sha(raw)!=row['structural_sha256']:raise ValueError('filtered structural reproduction mismatch')
    start=time.perf_counter();restored=framed.decode(frame);elapsed=time.perf_counter()-start
    if restored!=data:raise ValueError('filtered fresh restoration failed')
    if any(sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('filtered dependency changed during decode')
    return frame,dict(kind='qualified complete artifact; structure recomputed and independent decode repeated',
        measurement=dict(row,original_decode_seconds=row['decode_seconds'],decode_seconds=elapsed),
        measurement_path=str(record.resolve()),measurement_sha256=sha(record.read_bytes()),
        frame_sha256=sha(frame),input_sha256=digest,fresh_full_decode=True)


def additions(data,cache=None):
    if not eligible(data):return []
    found={}
    if cache:
        for record in Path(cache).glob('*/complete.json'):
            row=json.loads(record.read_text());mode=row['mode']
            if row['input_sha256']==sha(data) and mode in MODES:
                if mode in found:raise ValueError('duplicate filtered candidate')
                found[mode]=record.parent
        if set(found)!=set(MODES):raise ValueError('all three full filtered candidates required')
    out=[]
    for mode in MODES:
        start=time.perf_counter();proof=None
        if cache:frame,proof=qualify(data,found[mode])
        else:frame,_=framed.encode(data,mode)
        out.append((frame,dict(name=f'cix-paq-filters-brotli11-mode{mode}',size=len(frame),encode_seconds=time.perf_counter()-start),proof))
    return out


def encode(data,**kwargs):
    frame,selection=parent.encode(data,**kwargs)
    for candidate,row,_ in additions(data):
        selection['trials'].append(row)
        if len(candidate)<len(frame):frame=candidate;selection['selected']=row['name']
    return frame,selection


def decode(frame):return framed.decode(frame) if frame[:5]==framed.MAGIC else parent.decode(frame)


if __name__=='__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
