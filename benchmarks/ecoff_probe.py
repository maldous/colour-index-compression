"""Independent PAQ comparisons of derived ECOFF-table constraints."""
import argparse
import concurrent.futures
import json
import resource
import subprocess
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_constraints as codec,competitive_codec as backend

MAGIC=b'CIXB\x01'
REGIONS=[(4274176,73728),(35383296,147456),(47712256,180224)]


def encode(data,mode=3,options='-4'):
    raw,stats=codec.transform(data,mode)
    payload=backend.encode_paq(raw,'v215',options)
    return MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload,stats


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('invalid ECOFF frame')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big')
    data=codec.inverse(backend.decode(frame[pos+4:]))
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('ECOFF source checksum mismatch')
    return data


def worker(spec):
    offset,length,mode,options,output=spec;folder=Path(output)/f'{offset}-{mode}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'stream.cixb').exists():raise ValueError('preserve existing ECOFF trial')
    source=Path('benchmark-work/silesia/mozilla');data=source.read_bytes()[offset:offset+length]
    paths=[__file__,codec.__file__,backend.__file__,'cix/multinomial.py']
    hashes={str(Path(p)):backend.sha(Path(p).read_bytes()) for p in paths};binary_hash=backend.sha(Path(backend.paq_binary('v215')).read_bytes())
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();t=time.perf_counter()
    if mode==-1:frame=backend.encode_paq(data,'v215',options);stats=dict(mode=mode,original_bytes=len(data),control='ordinary PAQ physical stream')
    else:frame,stats=encode(data,mode,options)
    enc=time.perf_counter()-t;(folder/'stream.cixb').write_bytes(frame);t=time.perf_counter()
    restored=backend.decode((folder/'stream.cixb').read_bytes()) if mode==-1 else decode((folder/'stream.cixb').read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('ECOFF physical stream failed independent restoration')
    for path,digest in hashes.items():
        if backend.sha(Path(path).read_bytes())!=digest:raise ValueError('ECOFF experiment source changed')
    if backend.sha(Path(backend.paq_binary('v215')).read_bytes())!=binary_hash:raise ValueError('backend changed')
    row=dict(**stats,file='mozilla',offset=offset,options=options,physical_bytes=len(frame),round_trip=True,
        complete_silesia_member=offset==0 and len(data)==source.stat().st_size,
        input_sha256=backend.sha(data),frame_sha256=backend.sha(frame),restored_sha256=backend.sha(restored),
        source_hashes=hashes,backend_sha256=binary_hash,revision=revision,encode_seconds=enc,decode_seconds=dec,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['offset','mode','physical_bytes','round_trip','encode_seconds','decode_seconds']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--modes',nargs='+',type=int,default=[-1,0,1,2,3]);p.add_argument('--options',default='-4');p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--whole',action='store_true');args=p.parse_args();root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    regions=[(0,51220480)] if args.whole else REGIONS
    specs=[(off,n,mode,args.options,str(root)) for off,n in regions for mode in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=not args.whole,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
