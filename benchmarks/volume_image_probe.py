"""Complete MRI volume tournament; decoder parameters are fully framed."""
import concurrent.futures,hashlib,json,resource,time
from pathlib import Path
import imagecodecs
from benchmarks.spatial_image_codec import regions
from benchmarks.volume_image_codec import encode,decode


def worker(mode):
    data=Path('benchmark-work/silesia/mr').read_bytes();region=regions(data)[0]
    t=time.perf_counter();blob=encode(data,region,mode,9);enc=time.perf_counter()-t
    t=time.perf_counter();assert decode(blob)==data;dec=time.perf_counter()-t
    folder=Path('results/leaderboard/volume-probe');folder.mkdir(exist_ok=True)
    (folder/f'mr-mode{mode}.cixv').write_bytes(blob)
    row=dict(file='mr',mode=mode,effort=9,original=len(data),size=len(blob),region=region,input_sha256=hashlib.sha256(data).hexdigest(),frame_sha256=hashlib.sha256(blob).hexdigest(),round_trip=True,complete_member=True,encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,imagecodecs_version=imagecodecs.__version__,source_sha256=hashlib.sha256(Path('benchmarks/volume_image_codec.py').read_bytes()).hexdigest())
    (folder/f'mr-mode{mode}.json').write_text(json.dumps(row,indent=2)+'\n');return row


def main():
    with concurrent.futures.ProcessPoolExecutor(4) as pool:
        for r in pool.map(worker,range(6)):print(json.dumps(r),flush=True)

if __name__=='__main__':main()
