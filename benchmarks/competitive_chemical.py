"""Reproducible PAQ-backed coordinate constraints and qualified cache reuse."""
import json
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode,vdecode
from benchmarks import competitive_fixed_database as parent
from benchmarks import sdf_geometry as geometry,sdf_geometry_probe as framed
from benchmarks.competitive_codec import sha,paq_binary

NAME='CIX competitive grid/database/chemical portfolio 6'
SOURCES=[__file__,geometry.__file__,framed.__file__]


def recognizes(data):
    end=data.find(geometry.SEP,0,1<<20)
    if end<0:return False
    try:geometry.layout(data[:end].splitlines(keepends=True))
    except (ValueError,IndexError):return False
    return True


def encode_frame(data,options='-8'):
    transformed,_=geometry.encode(data,2,2)
    with tempfile.TemporaryDirectory(prefix='cix-chemical-') as folder:
        source=Path(folder)/'input.sdfg';archive=Path(folder)/'stream.paq8px215';source.write_bytes(transformed)
        subprocess.run([paq_binary('v215'),options,'-simd','AVX2',str(source),str(archive)],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return framed.MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+archive.read_bytes()


def qualify(data,folder,options='-8',require_complete=True):
    """Reuse an exact fully restored stream, never an unfinished archive.

    The cheap structural stage is recomputed from the current input and inverted
    again. It must equal the actual source previously passed to the pinned PAQ
    binary. The original full-frame extraction evidence is retained verbatim.
    """
    folder=Path(folder);record=folder/'complete.json';row=json.loads(record.read_text())
    if not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member')):raise ValueError('unqualified chemical trial')
    if (row['mode'],row['representation'],row['options'],row['offset'])!=(2,2,options,0):raise ValueError('chemical policy mismatch')
    if len(data)!=row['original_bytes'] or sha(data)!=row['input_sha256']:raise ValueError('chemical input mismatch')
    if sha(Path(geometry.__file__).read_bytes())!=row['codec_source_sha256']:raise ValueError('chemical codec changed')
    if sha(Path(paq_binary('v215')).read_bytes())!=row['backend_sha256']:raise ValueError('chemical backend changed')
    frame=(folder/'stream.cixg').read_bytes()
    if len(frame)!=row['physical_bytes'] or sha(frame)!=row['frame_sha256']:raise ValueError('chemical frame changed')
    if frame[:5]!=framed.MAGIC:raise ValueError('chemical magic mismatch')
    n,pos=vdecode(frame,5)
    if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data):raise ValueError('chemical framing mismatch')
    if frame[pos+4:]!=(folder/'stream.paq8px215').read_bytes():raise ValueError('chemical archive changed')
    transformed,_=geometry.encode(data,2,2)
    if sha(transformed)!=row['transformed_sha256'] or transformed!=(folder/'input.sdfg').read_bytes():raise ValueError('chemical transform changed')
    if geometry.decode(transformed)!=data:raise ValueError('chemical structural inversion failed')
    proof=dict(kind='completed independent full-frame decode reused',measurement=row,
        measurement_path=str(record.resolve()),measurement_sha256=sha(record.read_bytes()),
        decoder_source_sha256=sha(Path(framed.__file__).read_bytes()),
        structural_stage_recomputed_and_inverted=True,frame_sha256=sha(frame),input_sha256=sha(data))
    return frame,proof


def additions(data,cache=None):
    if not recognizes(data):return []
    start=time.perf_counter();proof=None
    if cache:frame,proof=qualify(data,cache)
    else:frame=encode_frame(data)
    return [(frame,dict(name='bonded-coordinate-palette-paq-v215-8',size=len(frame),encode_seconds=time.perf_counter()-start),proof)]


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
