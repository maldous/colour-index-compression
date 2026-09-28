"""Reuse only exact complete native-PAQ structural restoration proofs."""
import json
from pathlib import Path
import zlib
from benchmarks import ecoff_fields_probe as fields, ecoff_got_probe as got
from benchmarks import competitive_codec as backend
from cix.multinomial import vdecode

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[__file__,fields.__file__,fields.codec.__file__,fields.codec.base.__file__,got.__file__,got.codec.__file__,
         backend.__file__,str(ROOT/'cix/multinomial.py'),backend.paq_binary('v215')]


def eligible(data): return bool(fields.codec.base.objects(data))


def raw_transform(data,kind,mode):
    codec=fields.codec if kind=='fields' else got.codec
    raw,_=codec.transform(data,mode)
    if codec.inverse(raw)!=data: raise ValueError('structural transform failed current inversion')
    return raw


def qualify(data,folder,kind,mode,*,require_complete=True,options='-8'):
    if kind not in ('fields','got'): raise ValueError('unsupported structural family')
    folder=Path(folder);record=folder/'complete.json';row=json.loads(record.read_text());digest=backend.sha(data)
    if (not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member'))
        or row['input_sha256']!=digest or row['restored_sha256']!=digest or row['original_bytes']!=len(data)):
        raise ValueError('input or complete restoration evidence mismatch')
    if row['mode']!=mode or row['options']!=options: raise ValueError('structural profile mismatch')
    if kind=='fields' and require_complete and row['offset']!=0: raise ValueError('partial field probe')
    if kind=='got' and row['backend']!='paq': raise ValueError('expected native PAQ backend')
    module=fields if kind=='fields' else got
    required=[module.__file__,module.codec.__file__,fields.codec.__file__,fields.codec.base.__file__,backend.__file__,ROOT/'cix/multinomial.py']
    hashes={str(Path(p).resolve()):h for p,h in row['source_hashes'].items()}
    if any(str(Path(p).resolve()) not in hashes for p in required): raise ValueError('missing structural dependency proof')
    for p,h in hashes.items():
        if backend.sha(Path(p).read_bytes())!=h: raise ValueError('structural dependency changed')
    binary=Path(backend.paq_binary('v215'))
    if backend.sha(binary.read_bytes())!=row['backend_sha256']: raise ValueError('native backend changed')
    frame=(folder/'stream.cixb').read_bytes()
    if len(frame)!=row['physical_bytes'] or backend.sha(frame)!=row['frame_sha256']: raise ValueError('physical frame changed')
    if frame[:5]!=module.MAGIC: raise ValueError('structural frame family mismatch')
    offset=5
    if kind=='got':
        if frame[5:7]!=bytes([mode+2,1]): raise ValueError('GOT mode/backend header changed')
        offset=7
    n,pos=vdecode(frame,offset)
    if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data): raise ValueError('outer length/checksum changed')
    version,_=backend.unwrap_paq(frame[pos+4:])
    if version!='v215': raise ValueError('wrong native version')
    raw=raw_transform(data,kind,mode)
    if 'transformed_sha256' in row and backend.sha(raw)!=row['transformed_sha256']: raise ValueError('transformed input changed')
    return frame,dict(kind='Exact completed whole-frame restoration retained; all current input/frame/source/backend identities checked; structural transform recomputed and inverted',
        measurement=row,measurement_path=str(record.resolve()),measurement_sha256=backend.sha(record.read_bytes()),
        frame_sha256=backend.sha(frame),input_sha256=digest,transformed_sha256=backend.sha(raw),fresh_full_decode=False,
        verification_scope='The original frozen worker independently decoded this exact physical frame and compared every source byte. Repeating the multi-hour native decode is not required for unchanged artifacts.')


def addition(data,cache,kind,mode):
    if not eligible(data): return []
    import time
    start=time.perf_counter();proof=None
    if cache:frame,proof=qualify(data,cache,kind,mode)
    elif kind=='fields':frame,_=fields.encode(data,mode,'-8')
    else:frame,_=got.encode(data,mode,'paq','-8')
    return [(frame,dict(name=f'{kind}-constraints-paq-v215-8-mode{mode}',size=len(frame),encode_seconds=time.perf_counter()-start),proof)]
