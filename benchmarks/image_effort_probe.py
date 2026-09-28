"""Full-member image effort tournament, with independent decode and provenance."""
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path

import imagecodecs
from benchmarks import spatial_image_codec as spatial
from benchmarks import volume_image_codec as volume


def digest(data):
    return hashlib.sha256(data).hexdigest()


def worker(spec):
    name, kind, mode, effort = spec
    data = Path('benchmark-work/silesia', name).read_bytes()
    region = spatial.regions(data)[0]
    t = time.perf_counter()
    if kind == 'volume':
        blob = volume.encode(data, region, mode, effort)
        decoder, extension, module = volume.decode, 'cixv', volume
    else:
        blob = spatial.encode_region(data, region, kind, effort)
        decoder, extension, module = spatial.decode, 'cixi', spatial
    enc = time.perf_counter() - t
    folder = Path('results/leaderboard/image-effort')
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f'{name}-{kind}-{mode}-{effort}.{extension}'
    output.write_bytes(blob)
    t = time.perf_counter()
    restored = decoder(output.read_bytes())
    dec = time.perf_counter() - t
    if restored != data:
        raise ValueError('complete member restoration failed')
    row = dict(file=name, kind=kind, mode=mode, effort=effort, region=region,
               original=len(data), size=output.stat().st_size, complete_member=True,
               input_sha256=digest(data), frame_sha256=digest(blob), round_trip=True,
               encode_seconds=enc, decode_seconds=dec,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
               imagecodecs_version=imagecodecs.__version__,
               source_sha256=digest(Path(module.__file__).read_bytes()),
               revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
    output.with_suffix('.json').write_text(json.dumps(row, indent=2)+'\n')
    print(json.dumps(row), flush=True)
    return row


def main():
    specs = [('mr', 'volume', 3, n) for n in (7, 9, 10, 11)]
    specs += [('x-ray', 'jxl', 0, n) for n in (7, 9, 10, 11)]
    specs += [('x-ray', 'jls', 0, 0), ('x-ray', 'j2k', 0, 0)]
    with concurrent.futures.ProcessPoolExecutor(4, max_tasks_per_child=1) as pool:
        list(pool.map(worker, specs))


if __name__ == '__main__':
    main()
