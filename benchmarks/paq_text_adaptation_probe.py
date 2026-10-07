"""Bounded text controls: LSTM expert and adaptive context-mixer learning rate.

Use pristine local PAQ v215 with no external dictionaries or pretrained state.
Each physical native archive is independently extracted and compared exactly.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import time
from benchmarks import competitive_codec as codec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--cpu',type=int,default=22)
    args=p.parse_args()
    os.sched_setaffinity(0,{args.cpu})
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    path=Path('benchmark-work/silesia/dickens');source=path.read_bytes();length=131072
    offsets=[0,len(source)//2-length//2,len(source)-length]
    binary=Path(codec.paq_binary('v215'))
    hashes={str(Path(x).resolve()):codec.sha(Path(x).read_bytes()) for x in [__file__,codec.__file__,binary]}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    rows=[]
    for off in offsets:
        data=source[off:off+length]
        for options in ('-4','-4A','-4L','-4LA'):
            folder=root/f'{off}-{options[1:]}';folder.mkdir()
            (root/'status.json').write_text(json.dumps(dict(phase='encode',offset=off,options=options,at=datetime.now(timezone.utc).isoformat()))+'\n')
            start=time.perf_counter();frame=codec.encode_paq(data,'v215',options);enc=time.perf_counter()-start
            (folder/'stream.cixc').write_bytes(frame)
            (root/'status.json').write_text(json.dumps(dict(phase='decode',offset=off,options=options,at=datetime.now(timezone.utc).isoformat()))+'\n')
            start=time.perf_counter();restored=codec.decode((folder/'stream.cixc').read_bytes());dec=time.perf_counter()-start
            if restored!=data or path.read_bytes()!=source:raise ValueError('text trial source restoration mismatch')
            if any(codec.sha(Path(x).read_bytes())!=h for x,h in hashes.items()):raise ValueError('text trial dependency changed')
            row=dict(file='dickens',offset=off,original_bytes=len(data),options=options,physical_bytes=len(frame),round_trip=True,
                input_sha256=codec.sha(data),restored_sha256=codec.sha(restored),frame_sha256=codec.sha(frame),source_hashes=hashes,
                revision=revision,encode_seconds=enc,decode_seconds=dec,complete_silesia_member=False,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                completed_at=datetime.now(timezone.utc).isoformat())
            (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('offset','options','physical_bytes','round_trip')}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=True,rows=rows),indent=2)+'\n')
    (root/'status.json').write_text(json.dumps(dict(phase='complete',at=datetime.now(timezone.utc).isoformat()))+'\n')


if __name__=='__main__':main()
