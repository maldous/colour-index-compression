"""Full-member physical same-information correction-group tournaments."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import _brotli
from benchmarks import grid_conditional_corrections as codec
from benchmarks.competitive_codec import sha
from cix import multinomial

SOURCES = [__file__, codec.__file__, codec.grid.__file__, codec.feedback.__file__,
           codec.bounded.__file__, multinomial.__file__, _brotli.__file__]


def worker(spec):
    context, coding, cpu, output = spec
    os.sched_setaffinity(0, {cpu})
    folder = Path(output)/f'{context}-{coding}'
    folder.mkdir(parents=True, exist_ok=False)
    source = Path('benchmark-work/silesia/sao')
    data = source.read_bytes()
    hashes = {str(Path(p).resolve()): sha(Path(p).read_bytes()) for p in SOURCES}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    start = time.perf_counter()
    frame, stats = codec.encode(data, context, coding)
    enc = time.perf_counter()-start
    (folder/'stream.cixb').write_bytes(frame)
    start = time.perf_counter()
    restored = codec.decode((folder/'stream.cixb').read_bytes())
    dec = time.perf_counter()-start
    if restored != data or source.read_bytes() != data:
        raise ValueError('complete source did not restore')
    if any(sha(Path(p).read_bytes()) != h for p, h in hashes.items()):
        raise ValueError('experiment dependency changed')
    row = dict(stats, original_bytes=len(data), round_trip=True, complete_silesia_member=True,
        input_sha256=sha(data), restored_sha256=sha(restored), frame_sha256=sha(frame),
        encode_seconds=enc, decode_seconds=dec, source_hashes=hashes, revision=revision,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        completed_at=datetime.now(timezone.utc).isoformat())
    (folder/'complete.json').write_text(json.dumps(row, indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ('context','coding','physical_bytes','round_trip')}), flush=True)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    pairs = [(0,0),(1,0),(2,0),(3,0),(1,1),(1,2),(2,1),(2,2)]
    with concurrent.futures.ProcessPoolExecutor(2, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, [(a,b,20+2*(i%2),str(root)) for i,(a,b) in enumerate(pairs)]))
    (root/'complete.json').write_text(json.dumps(dict(complete=True, rows=rows), indent=2)+'\n')


if __name__ == '__main__':
    main()
