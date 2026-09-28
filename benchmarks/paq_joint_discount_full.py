"""Complete-file physical qualification with persistent native progress logs."""
import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import zlib
from benchmarks import paq_joint_discount_probe as codec
from cix.multinomial import vencode,vdecode


def main():
    os.sched_setaffinity(0,{0})
    root=Path('results/leaderboard/paq-joint-discount-full8').resolve()
    if root.exists(): raise ValueError('preserve full experiment; never restart from a polling timeout')
    root.mkdir(parents=True); source=Path('benchmark-work/silesia/mozilla'); data=source.read_bytes()
    manifest=json.loads(Path('results/silesia-manifest.json').read_text()); item,=[r for r in manifest if Path(r['path']).name==source.name]
    if len(data)!=item['size'] or codec.sha(data)!=item['sha256']: raise ValueError('noncanonical full input')
    provenance=codec.FORK.parent.parent/'provenance.json'; build=json.loads(provenance.read_text())
    paths=[Path(__file__),Path(codec.__file__),codec.FORK,provenance,codec.ROOT/'cix/multinomial.py',
        Path(codec.transform.__file__),Path(codec.transform.uniform.__file__),Path(codec.transform.parent.__file__),
        Path(codec.transform.parent.locator.__file__),Path(codec.transform.parent.parent.__file__),
        Path(codec.transform.parent.parent.parent.__file__),Path(codec.transform.parent.parent.parent.base.__file__)]
    hashes={str(p):codec.sha(p.read_bytes()) for p in paths}
    for path,h in build['source_hashes'].items():
        if codec.sha(Path(path).read_bytes())!=h: raise ValueError('native source changed')
        hashes[path]=h
    if codec.sha(codec.FORK.read_bytes())!=build['binary_sha256']: raise ValueError('native binary changed')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=codec.ROOT,text=True).strip()
    def status(phase,**extra):
        value=dict(phase=phase,pid=os.getpid(),cpu=0,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),input_sha256=codec.sha(data),**extra)
        temp=root/'status.tmp';temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(root/'status.json')
    mode=2;status('transform');start=time.perf_counter();raw,stats=codec.transform.transform(data,4)
    if codec.transform.inverse(raw)!=data: raise ValueError('full structural transform failed')
    transformed=root/'source.bin';transformed.write_bytes(raw);archive=root/'stream.paq8px215';status('encode')
    with (root/'encode.log').open('wb') as log:
        subprocess.run([str(codec.FORK),'-8','-simd','AVX2',str(transformed),str(archive)],env=codec.environment(mode),check=True,stdout=log,stderr=log)
    payload=archive.read_bytes();frame=codec.MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    artifact=root/'stream.cixb';artifact.write_bytes(frame);enc=time.perf_counter()-start
    status('decode',encoded_bytes=len(frame));start=time.perf_counter();physical=artifact.read_bytes()
    if physical[:5]!=codec.MAGIC or physical[5]!=mode: raise ValueError('stored full frame header changed')
    n,pos=vdecode(physical,6);crc=int.from_bytes(physical[pos:pos+4],'big')
    # Decode the payload extracted from the actual stored frame, independently of encoder buffers.
    decode_archive=root/'decode-input.paq8px215';decode_archive.write_bytes(physical[pos+4:]);decoded=root/'restored-structure.bin'
    with (root/'decode.log').open('wb') as log:
        subprocess.run([str(codec.binary(physical[5])),'-d','-simd','AVX2',str(decode_archive),str(decoded)],env=codec.environment(physical[5]),check=True,stdout=log,stderr=log)
    restored=codec.transform.inverse(decoded.read_bytes());dec=time.perf_counter()-start
    if n!=len(restored) or zlib.crc32(restored)!=crc or restored!=data: raise ValueError('full frame failed exact restoration')
    for path,h in hashes.items():
        if codec.sha(Path(path).read_bytes())!=h: raise ValueError('full codec dependency changed')
    row=dict(complete=True,complete_silesia_member=True,diagnostic_only=False,file='mozilla',mode=mode,options='-8 -simd AVX2',
        original_bytes=len(data),physical_bytes=len(frame),input_sha256=codec.sha(data),restored_sha256=codec.sha(restored),
        transformed_sha256=codec.sha(raw),frame_sha256=codec.sha(frame),paq_sha256=codec.sha(payload),round_trip=True,parent_stats=stats,
        encode_seconds=enc,decode_seconds=dec,source_hashes=hashes,revision=revision,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        verification='Independent native decoder reads payload extracted from stored physical CIXB1d frame, then inverse structural transform, outer length/CRC and byte-for-byte original comparison. No source, prediction trace or cache used by decoder.',
        completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (root/'complete.json').write_text(json.dumps(row,indent=2)+'\n');status('complete',physical_bytes=len(frame),round_trip=True)
    print(json.dumps({k:row[k] for k in ('physical_bytes','round_trip','encode_seconds','decode_seconds')}),flush=True)


if __name__=='__main__': main()
