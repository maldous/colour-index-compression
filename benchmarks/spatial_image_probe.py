"""Complete-member spatial codec tournament; all emitted bytes are verified."""
import concurrent.futures,hashlib,json,time,resource
from pathlib import Path
from benchmarks.spatial_image_codec import regions,encode_region,decode
import imagecodecs


def worker(task):
    name,backend,effort=task;data=Path('benchmark-work/silesia',name).read_bytes();detected=regions(data)
    if len(detected)!=1:raise ValueError('expected one detected spatial region')
    start=time.perf_counter();blob=encode_region(data,detected[0],backend,effort);enc=time.perf_counter()-start
    start=time.perf_counter();restored=decode(blob);dec=time.perf_counter()-start
    if restored!=data:raise ValueError('spatial round trip failed')
    folder=Path('results/leaderboard/spatial-probe');folder.mkdir(exist_ok=True)
    label=f'{name}-{backend}-{effort}'
    (folder/(label+'.cixi')).write_bytes(blob)
    row=dict(file=name,backend=backend,effort=effort,region=detected[0],original=len(data),size=len(blob),input_sha256=hashlib.sha256(data).hexdigest(),frame_sha256=hashlib.sha256(blob).hexdigest(),round_trip=True,encode_seconds=enc,decode_seconds=dec,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,imagecodecs_version=imagecodecs.__version__,native_versions=imagecodecs.version(),source_sha256=hashlib.sha256(Path('benchmarks/spatial_image_codec.py').read_bytes()).hexdigest(),complete_member=True)
    (folder/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return row


def main():
    tasks=[(name,backend,effort) for name in ('mr','x-ray') for backend,effort in [('jxl',7),('jxl',9),('j2k',0),('jls',0)]]
    with concurrent.futures.ProcessPoolExecutor(4) as pool:
        for r in pool.map(worker,tasks):print(json.dumps(r),flush=True)

if __name__=='__main__':main()
