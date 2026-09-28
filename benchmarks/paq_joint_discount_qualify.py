"""Qualify causal discount with identical underlying memory-aware PAQ traces."""
import concurrent.futures
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import zlib
from benchmarks import paq_joint_discount_probe as codec
from benchmarks.paq_joint_log_collect import verified_rows
from benchmarks import paq_joint_log_probe as prior
from cix.multinomial import vencode, vdecode


def worker(spec):
    mode,cpu,root=spec; os.sched_setaffinity(0,{cpu}); root=Path(root); folder=root/str(mode); folder.mkdir()
    source_path=Path('results/leaderboard/ecoff-call-trace/source.bin'); data=source_path.read_bytes()
    raw,stats=codec.transform.transform(data,4); source=folder/'source.bin'; source.write_bytes(raw)
    provenance=codec.FORK.parent.parent/'provenance.json'; build=json.loads(provenance.read_text())
    paths=[Path(__file__),Path(codec.__file__),codec.FORK,provenance,codec.ROOT/'cix/multinomial.py',
        Path(codec.transform.__file__),Path(codec.transform.uniform.__file__),Path(codec.transform.parent.__file__),
        Path(codec.transform.parent.locator.__file__),Path(codec.transform.parent.parent.__file__),
        Path(codec.transform.parent.parent.parent.__file__),Path(codec.transform.parent.parent.parent.base.__file__)]
    hashes={str(p):codec.sha(p.read_bytes()) for p in paths}
    for p,h in build['source_hashes'].items():
        if codec.sha(Path(p).read_bytes())!=h: raise ValueError('native build source changed')
        hashes[p]=h
    if codec.sha(codec.FORK.read_bytes())!=build['binary_sha256']: raise ValueError('native build changed')
    archive=folder/'stream.paq8px215'; trace=folder/'predictions.u32'; env=codec.environment(mode)
    env['CIX_REGISTER_BASE_TRACE']=str(trace.resolve()); started=time.perf_counter()
    with (folder/'encode.stdout').open('wb') as out,(folder/'encode.stderr').open('wb') as err:
        subprocess.run([str(codec.FORK),'-4','-simd','AVX2',str(source),str(archive)],check=True,env=env,stdout=out,stderr=err)
    enc=time.perf_counter()-started; payload=archive.read_bytes()
    frame=codec.MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    framepath=folder/'stream.cixb'; framepath.write_bytes(frame)
    started=time.perf_counter(); restored=codec.decode(framepath.read_bytes()); dec=time.perf_counter()-started
    if restored!=data: raise ValueError('discounted source restoration failed')
    for p,h in hashes.items():
        if codec.sha(Path(p).read_bytes())!=h: raise ValueError('discount dependency changed')
    row=dict(mode=mode,physical_bytes=len(frame),paq_bytes=len(payload),frame_sha256=codec.sha(frame),paq_sha256=codec.sha(payload),
        input_path=str(source_path),input_sha256=codec.sha(data),restored_sha256=codec.sha(restored),transformed_sha256=codec.sha(raw),parent_stats=stats,
        trace_sha256=codec.sha(trace.read_bytes()),trace_bytes=trace.stat().st_size,round_trip=True,diagnostic_only=True,
        options='-4 -simd AVX2',encode_seconds=enc,decode_seconds=dec,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        source_hashes=hashes,revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=codec.ROOT,text=True).strip())
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ('mode','physical_bytes','round_trip')}),flush=True); return row


def main():
    root=Path('results/leaderboard/paq-joint-discount-qualified').resolve()
    if root.exists(): raise ValueError('preserve existing qualification')
    controls,proof=verified_rows(Path('results/leaderboard/paq-joint-log-pilot'),prior)
    expected=Path(controls[3]['artifact']).read_bytes(); _,pos=vdecode(expected,6); expected=expected[pos+4:]
    root.mkdir(parents=True)
    with concurrent.futures.ProcessPoolExecutor(3,max_tasks_per_child=1) as pool:
        rows=list(pool.map(worker,[(1,18,str(root)),(2,0,str(root)),(3,22,str(root))]))
    trace=(root/'1/predictions.u32').read_bytes()
    if any((root/str(m)/'predictions.u32').read_bytes()!=trace for m in (2,3)): raise ValueError('underlying PAQ prediction stream changed')
    if (root/'1/stream.paq8px215').read_bytes()!=expected: raise ValueError('persistent joint control changed')
    for row in rows:
        if row['input_sha256']!=controls[3]['input_sha256'] or row['transformed_sha256']!=controls[3]['transformed_sha256']:
            raise ValueError('unmatched qualified source')
    report=dict(complete=True,diagnostic_only=True,scored=False,rows=rows,original_predictions_byte_identical=True,
        persistent_control_byte_identical=True,retained_control=controls[3],retained_control_proof=proof,
        interpretation='Explicit causal forgetting changes register expert weights. Same native memory-feedback PAQ predictions and source bytes across all arms; arithmetic coding retained. No hard state-space elimination or identical-information entropy-coder superiority claimed.')
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(persistent_bytes=rows[0]['physical_bytes'],discount31_bytes=rows[1]['physical_bytes'],discount127_bytes=rows[2]['physical_bytes'],all_traces_identical=True)),flush=True)


if __name__=='__main__': main()
