"""Physical controls for section/function alphabets and causal feedback."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import resource
import subprocess
import time
import zlib
import brotli
import _brotli
from cix.multinomial import vencode,vdecode
from benchmarks import ecoff_section_pointers as codec, competitive_codec as paq

MAGIC=b'CIXB\x0c'


def encode(data,mode=2,backend='brotli',options='-4'):
    raw,stats=codec.transform(data,mode)
    payload=brotli.compress(raw,quality=11,lgwin=24) if backend=='brotli' else paq.encode_paq(raw,'v215',options)
    return MAGIC+bytes([int(backend=='paq')])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload,dict(stats,transformed_sha256=paq.sha(raw))


def decode(frame):
    if frame[:5]!=MAGIC or frame[5]>1:raise ValueError('invalid relocated-pointer frame')
    n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');payload=frame[pos+4:]
    raw=paq.decode(payload) if frame[5] else brotli.decompress(payload);data=codec.inverse(raw)
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('pointer source checksum mismatch')
    return data


def worker(spec):
    path,mode,backend,options,output,whole=spec;source=Path(path);data=source.read_bytes()
    folder=Path(output)/f'{source.stem}-{mode}';folder.mkdir(parents=True,exist_ok=True)
    if (folder/'stream.cixb').exists():raise ValueError('preserve existing pointer trial')
    paths=[__file__,codec.__file__,codec.uniform.__file__,codec.parent.__file__,codec.parent.locator.__file__,codec.parent.parent.__file__,codec.parent.parent.parent.__file__,codec.parent.parent.parent.base.__file__,paq.__file__,'cix/multinomial.py']
    binary=Path(paq.paq_binary('v215')) if backend=='paq' else Path(_brotli.__file__)
    hashes={str(Path(p)):paq.sha(Path(p).read_bytes()) for p in [*paths,binary]};revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    t=time.perf_counter();frame,stats=encode(data,mode,backend,options);enc=time.perf_counter()-t
    (folder/'stream.cixb').write_bytes(frame);t=time.perf_counter();restored=decode((folder/'stream.cixb').read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('pointer stream restoration failed')
    if any(paq.sha(Path(p).read_bytes())!=digest for p,digest in hashes.items()):raise ValueError('pointer experiment dependency changed')
    if source.read_bytes()!=data:raise ValueError('pointer source changed')
    row=dict(stats,backend=backend,options=options,input_path=str(source),physical_bytes=len(frame),round_trip=True,complete_silesia_member=whole,
             input_sha256=paq.sha(data),restored_sha256=paq.sha(restored),frame_sha256=paq.sha(frame),source_hashes=hashes,
             backend_sha256=hashes[str(binary)],brotli_version=brotli.__version__,revision=revision,encode_seconds=enc,decode_seconds=dec,
             peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ['input_path','mode','physical_bytes','round_trip']}),flush=True)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--whole',action='store_true')
    p.add_argument('--manifest',default='results/leaderboard/ecoff-got-cohorts-v2/manifest.json');p.add_argument('--modes',nargs='+',type=int,default=list(range(7)))
    p.add_argument('--backend',choices=['brotli','paq'],default='brotli');p.add_argument('--options',default='-4');p.add_argument('--jobs',type=int,default=4);args=p.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    if args.whole:
        source=Path('benchmark-work/silesia/mozilla');manifest=dict(rows=[dict(path=str(source),sha256=paq.sha(source.read_bytes()))])
    else:manifest=json.loads(Path(args.manifest).read_text())
    specs=[]
    for row in manifest['rows']:
        if paq.sha(Path(row['path']).read_bytes())!=row['sha256']:raise ValueError('pointer cohort input mismatch')
        for mode in args.modes:
            specs.append((row['path'],mode,args.backend,args.options,str(root),args.whole))
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool:rows=list(pool.map(worker,specs))
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=not args.whole,fixture=manifest,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
