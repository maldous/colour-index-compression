"""Physical template controls using complete streams and exact restoration."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import subprocess
import time
import zlib
import brotli
import _brotli
from cix import multinomial
from benchmarks import ecoff_function_templates as codec, competitive_codec as paq

MAGIC=b'CIXB\x22'
SOURCES=[__file__,codec.__file__,codec.parent.__file__,codec.parent.locator.__file__,
         codec.parent.parent.__file__,codec.parent.parent.parent.__file__,
         codec.parent.parent.parent.base.__file__,paq.__file__,multinomial.__file__]


def encode(data,mode,backend,options):
    raw,stats=codec.transform(data,mode)
    if codec.inverse(raw)!=data:raise ValueError('template raw inversion failed')
    payload=paq.encode_paq(raw,'v215',options) if backend=='paq' else brotli.compress(raw,quality=11,lgwin=24)
    return MAGIC+bytes([backend=='paq'])+multinomial.vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload,dict(stats,transformed_sha256=paq.sha(raw))


def decode(frame):
    if frame[:5]!=MAGIC or frame[5]>1:raise ValueError('invalid template frame')
    n,pos=multinomial.vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big')
    raw=paq.decode(frame[pos+4:]) if frame[5] else brotli.decompress(frame[pos+4:])
    data=codec.inverse(raw)
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('template source checksum mismatch')
    return data


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--whole',action='store_true');p.add_argument('--modes',nargs='+',type=int,default=[0,1,2])
    p.add_argument('--backend',choices=['brotli','paq'],default='brotli');p.add_argument('--options',default='-4')
    args=p.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    binary=paq.paq_binary('v215') if args.backend=='paq' else _brotli.__file__
    hashes={str(Path(x).resolve()):paq.sha(Path(x).read_bytes()) for x in [*SOURCES,binary]}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
    sources=[Path('benchmark-work/silesia/mozilla')] if args.whole else [Path(x['path']) for x in json.loads(Path('results/leaderboard/ecoff-got-cohorts-v2/manifest.json').read_text())['rows']]
    for source in sources:
        data=source.read_bytes()
        for mode in args.modes:
            folder=root/f'{source.stem}-{mode}';folder.mkdir();t=time.perf_counter()
            frame,stats=encode(data,mode,args.backend,args.options);enc=time.perf_counter()-t
            (folder/'stream.cixb').write_bytes(frame);t=time.perf_counter();restored=decode((folder/'stream.cixb').read_bytes());dec=time.perf_counter()-t
            if restored!=data or source.read_bytes()!=data:raise ValueError('template physical restoration failed')
            if any(paq.sha(Path(x).read_bytes())!=h for x,h in hashes.items()):raise ValueError('template dependency changed')
            row=dict(stats,mode=mode,backend=args.backend,options=args.options,source_hashes=hashes,
                physical_bytes=len(frame),original_bytes=len(data),input_path=str(source),input_sha256=paq.sha(data),restored_sha256=paq.sha(restored),frame_sha256=paq.sha(frame),
                round_trip=True,complete_silesia_member=args.whole,encode_seconds=enc,decode_seconds=dec,
                revision=revision,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,completed_at=datetime.now(timezone.utc).isoformat())
            (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('input_path','mode','physical_bytes','round_trip','template_source_bytes','changed_words')}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=not args.whole,rows=rows),indent=2)+'\n')


if __name__=='__main__':main()
