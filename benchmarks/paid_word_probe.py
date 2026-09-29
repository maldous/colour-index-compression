"""Matched PAQ controls for fully paid learned word replacement."""
import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import time
from benchmarks import paid_word_transform as codec


def main():
    os.sched_setaffinity(0,{20})
    root=Path('results/leaderboard/paid-word-paq-regions');root.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path('results/leaderboard/prose-fixtures/manifest.json').read_text())
    sources=[__file__,codec.__file__,codec.BINARY,codec.backend.__file__,'cix/multinomial.py',codec.backend.paq_binary('v215')]
    hashes={str(Path(p).resolve()):codec.backend.sha(Path(p).read_bytes()) for p in sources}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
    for fixture in manifest['rows']:
        source=Path(fixture['path']);data=source.read_bytes()
        if codec.backend.sha(data)!=fixture['sha256']:raise ValueError('fixture changed')
        for mode in (0,1):
            folder=root/f'{source.stem}-{mode}';folder.mkdir(exist_ok=True)
            frame_path=folder/'stream.cixb'
            if frame_path.exists():raise ValueError('preserve existing trial')
            t=time.perf_counter();frame,stats=codec.encode(data,mode,'paq','-4');enc=time.perf_counter()-t
            frame_path.write_bytes(frame);t=time.perf_counter();restored=codec.decode(frame_path.read_bytes());dec=time.perf_counter()-t
            if restored!=data:raise ValueError('word transform failed complete restoration')
            if any(codec.backend.sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('live source changed')
            row=dict(**stats,fixture=fixture,input_sha256=codec.backend.sha(data),frame_sha256=codec.backend.sha(frame),
                restored_sha256=codec.backend.sha(restored),round_trip=True,complete_member=False,
                diagnostic_only=True,source_hashes=hashes,revision=revision,encode_seconds=enc,decode_seconds=dec,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print(json.dumps({k:row[k] for k in ('fixture','mode','physical_bytes','dictionary_bytes','round_trip')}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,diagnostic_only=True,scored=False,rows=rows),indent=2)+'\n')


if __name__=='__main__': main()
