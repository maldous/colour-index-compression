"""Measure complete local codec references for the user-facing comparison table."""
import bz2
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import statistics
import time
import brotli
import zstandard


def main():
    os.sched_setaffinity(0,{20})
    root=Path('results/leaderboard/silesia-speed-reference-20260928')
    if root.exists(): raise ValueError('preserve reference measurements')
    root.mkdir(parents=True)
    published=json.loads(Path('results/leaderboard/published.json').read_text())
    corpus=published['verified_corpus']; code=Path(__file__); code_hash=hashlib.sha256(code.read_bytes()).hexdigest()
    specs=[('gzip','gzip level9,mtime0',lambda x:gzip.compress(x,compresslevel=9,mtime=0),gzip.decompress),
        ('bzip2','bzip2 level9',lambda x:bz2.compress(x,compresslevel=9),bz2.decompress),
        ('zstd','zstd1.5.7 level22',zstandard.ZstdCompressor(level=22).compress,zstandard.ZstdDecompressor().decompress),
        ('xz','XZ/LZMA2 preset9 extreme',lambda x:lzma.compress(x,preset=9|lzma.PRESET_EXTREME),lzma.decompress),
        ('brotli','Brotli1.2.0 quality11 lgwin24',lambda x:brotli.compress(x,quality=11,lgwin=24),brotli.decompress)]
    completed=[]
    for name,options,encode,decode in specs:
        directory=root/name; directory.mkdir(); rows=[]
        for item in corpus:
            source=Path('benchmark-work/silesia')/item['name']; data=source.read_bytes()
            if len(data)!=item['size'] or hashlib.md5(data).hexdigest()!=item['md5']: raise ValueError('noncanonical source')
            artifact=directory/(item['name']+'.bin')
            start=time.perf_counter(); frame=encode(data); artifact.write_bytes(frame); enc=time.perf_counter()-start
            times=[]
            for _ in range(3):
                start=time.perf_counter(); restored=decode(artifact.read_bytes()); times.append(time.perf_counter()-start)
                if restored!=data: raise ValueError('reference restore mismatch')
            row=dict(file=item['name'],original_bytes=len(data),physical_bytes=len(frame),round_trip=True,
                input_sha256=hashlib.sha256(data).hexdigest(),restored_sha256=hashlib.sha256(restored).hexdigest(),
                frame_sha256=hashlib.sha256(frame).hexdigest(),encode_seconds=enc,decode_seconds=statistics.median(times),decode_samples_seconds=times)
            rows.append(row);(directory/(item['name']+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        total=sum(r['original_bytes'] for r in rows); enc=sum(r['encode_seconds'] for r in rows); dec=sum(r['decode_seconds'] for r in rows)
        report=dict(complete=True,algorithm=name,options=options,original_bytes=total,physical_bytes=sum(r['physical_bytes'] for r in rows),
            ratio=sum(r['physical_bytes'] for r in rows)/total,compression_MBps=total/1e6/enc,decompression_MBps=total/1e6/dec,
            encode_seconds=enc,decode_seconds=dec,rows=rows,source_sha256=code_hash,cpu_affinity=[20],platform=platform.platform(),
            method='12 canonical files independently compressed; physical archives retained; three exact decodes each, median per file. Original MB per second. One encode measurement per file, in a concurrent research workload. E-core20 on i9-13900K. File output/read included, source read and comparison excluded.',
            versions=dict(python=platform.python_version(),brotli=brotli.__version__,zstandard=zstandard.__version__,zstd_library='.'.join(map(str,zstandard.ZSTD_VERSION))))
        if hashlib.sha256(code.read_bytes()).hexdigest()!=code_hash: raise ValueError('reference runner changed')
        (directory/'complete.json').write_text(json.dumps(report,indent=2)+'\n');completed.append(report)
        print(json.dumps({k:report[k] for k in ('algorithm','physical_bytes','compression_MBps','decompression_MBps')}),flush=True)
    (root/'complete.json').write_text(json.dumps(dict(complete=True,rows=completed),indent=2)+'\n')


if __name__=='__main__': main()
