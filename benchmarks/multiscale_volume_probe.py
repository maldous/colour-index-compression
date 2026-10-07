"""Bounded full-member tournament for multiscale image prediction."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import imagecodecs
from imagecodecs import _jpegxl
from benchmarks import multiscale_volume as codec, spatial_image_codec as spatial

ROOT = Path('results/leaderboard/multiscale-volume-20260928')


def sha(data): return hashlib.sha256(data).hexdigest()


def worker(spec):
    name, region_index, axes, levels, predictor, cpu = spec
    os.sched_setaffinity(0, {cpu})
    folder = ROOT / f'{name}-r{region_index}-a{axes}-l{levels}-p{predictor}'
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / 'stream.cixi').exists(): raise ValueError('preserve existing trial')
    data = (Path('benchmark-work/silesia') / name).read_bytes()
    source_hashes = {str(Path(p).resolve()): sha(Path(p).read_bytes()) for p in
        [__file__, codec.__file__, spatial.__file__, 'cix/multinomial.py', _jpegxl.__file__]}
    revision = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    region = spatial.regions(data)[region_index]
    t = time.perf_counter()
    frame, stats = codec.encode(data, region, axes, levels, predictor, effort=10)
    enc = time.perf_counter() - t
    (folder / 'stream.cixi').write_bytes(frame)
    t = time.perf_counter(); restored = codec.decode((folder / 'stream.cixi').read_bytes())
    dec = time.perf_counter() - t
    if restored != data: raise ValueError('full-member mismatch')
    for p, digest in source_hashes.items():
        if sha(Path(p).read_bytes()) != digest: raise ValueError('live source changed')
    row = dict(**stats, file=name, region=region, input_sha256=sha(data),
        frame_sha256=sha(frame), restored_sha256=sha(restored), original_bytes=len(data),
        complete_member=True, round_trip=True, source_hashes=source_hashes,
        encode_seconds=enc, decode_seconds=dec, cpu=cpu, revision=revision,
        imagecodecs_version=imagecodecs.__version__, native_versions=imagecodecs.version(),
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    temp = folder / 'complete.tmp'; temp.write_text(json.dumps(row,indent=2)+'\n')
    temp.replace(folder / 'complete.json')
    print(json.dumps({k:row[k] for k in ('file','axes','levels','predictor','physical_bytes','round_trip','encode_seconds')}),flush=True)
    return row


def run_lane(specs): return [worker(spec) for spec in specs]


def main():
    lanes = [
        [('mr',0,0,0,0,20), ('mr',0,1,3,0,20), ('mr',0,1,3,1,20)],
        [('mr',0,7,2,1,24), ('x-ray',1,0,0,0,24), ('x-ray',1,6,2,1,24)],
    ]
    ROOT.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(2) as pool:
        rows = [row for lane in pool.map(run_lane,lanes) for row in lane]
    incumbent = json.loads(Path('results/leaderboard/competitive-filtered-v19/complete.json').read_text())
    selected = {r['file']: r['size'] for r in incumbent['rows']}
    report = dict(complete=True,scored=False,rows=rows,incumbent=selected,
                  savings={name:selected[name]-min(r['physical_bytes'] for r in rows if r['file']==name)
                           for name in ('mr','x-ray')})
    (ROOT / 'complete.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['savings']),flush=True)


if __name__ == '__main__': main()
