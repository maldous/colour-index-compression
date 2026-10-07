"""Small fixed eight-way complete X-ray orientation tournament."""
import concurrent.futures
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path
import imagecodecs
from benchmarks import oriented_image_codec as codec
from benchmarks.spatial_image_codec import regions


def worker(mode):
    source=Path('benchmark-work/silesia/x-ray');data=source.read_bytes();region=regions(data)[0]
    t=time.perf_counter();blob=codec.encode(data,region,mode);enc=time.perf_counter()-t
    folder=Path('results/leaderboard/orientation-probe');folder.mkdir(parents=True,exist_ok=True)
    frame=folder/f'x-ray-{mode}.cixo';frame.write_bytes(blob)
    t=time.perf_counter();restored=codec.decode(frame.read_bytes());dec=time.perf_counter()-t
    if restored!=data:raise ValueError('orientation round trip failed')
    digest=lambda b:hashlib.sha256(b).hexdigest()
    result=dict(file=source.name,mode=mode,effort=10,region=region,original=len(data),size=len(blob),
        input_sha256=digest(data),frame_sha256=digest(blob),round_trip=True,complete_member=True,
        encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        source_sha256=digest(Path(codec.__file__).read_bytes()),spatial_source_sha256=digest(Path('benchmarks/spatial_image_codec.py').read_bytes()),
        imagecodecs_version=imagecodecs.__version__,revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    frame.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    with concurrent.futures.ProcessPoolExecutor(4,max_tasks_per_child=1) as pool:list(pool.map(worker,range(8)))
