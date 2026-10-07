"""Physical heavy-atom prediction tournament, with standalone restoration."""
import argparse
import concurrent.futures
import json
import resource
import subprocess
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode,vdecode
from benchmarks import sdf_heavy as codec,sdf_hydrogen,sdf_geometry
from benchmarks import competitive_codec as backend

MAGIC=b'CIXK\x01'


def encode(data,model=2,representation=0,options='-4'):
    raw,stats=codec.encode(data,model,representation)
    payload=backend.encode_paq(raw,'v215',options)
    frame=MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return frame,dict(**stats,physical_bytes=len(frame),transformed_sha256=backend.sha(raw))


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid framed heavy geometry stream')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big')
    data=codec.decode(backend.decode(frame[pos+4:]))
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('heavy frame source checksum mismatch')
    return data


def worker(spec):
    offset,length,model,rep,options,output=spec;folder=Path(output)/f'{offset}-{model}-{rep}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'stream.cixk').exists():raise ValueError('preserve existing heavy trial')
    source=Path('benchmark-work/silesia/nci');data=source.read_bytes()[offset:offset+length]
    paths=[__file__,codec.__file__,sdf_hydrogen.__file__,sdf_geometry.__file__,backend.__file__,'cix/multinomial.py']
    hashes={str(Path(p)):backend.sha(Path(p).read_bytes()) for p in paths}
    binary_hash=backend.sha(Path(backend.paq_binary('v215')).read_bytes())
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    t=time.perf_counter();frame,stats=encode(data,model,rep,options);enc=time.perf_counter()-t
    (folder/'stream.cixk').write_bytes(frame);t=time.perf_counter();restored=decode((folder/'stream.cixk').read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('heavy frame failed independent exact restoration')
    for path,digest in hashes.items():
        if backend.sha(Path(path).read_bytes())!=digest:raise ValueError('heavy experiment source changed')
    if backend.sha(Path(backend.paq_binary('v215')).read_bytes())!=binary_hash:raise ValueError('heavy backend changed')
    row=dict(**stats,file='nci',offset=offset,options=options,round_trip=True,
        complete_silesia_member=offset==0 and len(data)==source.stat().st_size,
        input_sha256=backend.sha(data),frame_sha256=backend.sha(frame),restored_sha256=backend.sha(restored),
        source_hashes=hashes,backend_sha256=binary_hash,revision=revision,encode_seconds=enc,decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ['model','representation','offset','physical_bytes','round_trip','encode_seconds','decode_seconds']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--bytes',type=int,default=65536);p.add_argument('--offsets',nargs='+',type=int,default=[0,16776722,33487909])
    p.add_argument('--models',nargs='+',type=int,default=[0,1,2,3]);p.add_argument('--representations',nargs='+',type=int,default=[0])
    p.add_argument('--options',default='-4');p.add_argument('--jobs',type=int,default=4);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    specs=[(off,args.bytes,m,r,args.options,str(root)) for off in args.offsets for m in args.models for r in args.representations]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
