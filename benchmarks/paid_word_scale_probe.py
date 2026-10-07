"""Complete-file Brotli controls for paid-dictionary cost amortization.

This is a cheap representation gate, not a forecast of its effect on PAQ.
"""
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import _brotli
from benchmarks import paid_word_transform as codec

ROOT=Path('results/leaderboard/paid-word-brotli-whole')


def worker(spec):
    name,cpu=spec;os.sched_setaffinity(0,{cpu});data=(Path('benchmark-work/silesia')/name).read_bytes()
    sources=[__file__,codec.__file__,codec.BINARY,codec.backend.__file__,'cix/multinomial.py',_brotli.__file__]
    hashes={str(Path(p).resolve()):codec.backend.sha(Path(p).read_bytes()) for p in sources}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=[]
    for mode in (0,1):
        folder=ROOT/f'{name}-{mode}';folder.mkdir(parents=True,exist_ok=True);path=folder/'stream.cixb'
        if path.exists():raise ValueError('preserve existing word trial')
        t=time.perf_counter();frame,stats=codec.encode(data,mode,'brotli');enc=time.perf_counter()-t
        path.write_bytes(frame);t=time.perf_counter();restored=codec.decode(path.read_bytes());dec=time.perf_counter()-t
        if restored!=data:raise ValueError('complete word stream failed restoration')
        if any(codec.backend.sha(Path(p).read_bytes())!=h for p,h in hashes.items()):raise ValueError('live source changed')
        row=dict(**stats,file=name,original_bytes=len(data),complete_member=True,round_trip=True,
            input_sha256=codec.backend.sha(data),restored_sha256=codec.backend.sha(restored),frame_sha256=codec.backend.sha(frame),
            source_hashes=hashes,revision=revision,encode_seconds=enc,decode_seconds=dec,cpu=cpu,
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps({k:row[k] for k in ('file','mode','physical_bytes','dictionary_bytes','round_trip','encode_seconds')}),flush=True)
    return rows


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(2) as pool:
        rows=[r for pair in pool.map(worker,[('webster',20),('dickens',24)]) for r in pair]
    report=dict(complete=True,scored=False,rows=rows,
        scope='Complete physical Brotli comparison with every dictionary byte charged. No inference about PAQ or the complete CIX total.')
    (ROOT/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
