"""Physically qualify register log mixtures while proving native predictions unchanged."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import time
import zlib
from benchmarks import paq_register_log_probe as codec
from cix.multinomial import vencode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',default='results/leaderboard/ecoff-call-trace')
    parser.add_argument('--output',required=True)
    parser.add_argument('--modes',type=int,nargs='+',default=[0,1,2,3])
    args=parser.parse_args();reference=Path(args.reference).resolve();root=Path(args.output).resolve()
    proof=json.loads((reference/'complete.json').read_text());data=(reference/'source.bin').read_bytes()
    expected=(reference/'predictions.u32').read_bytes();baseline=(reference/'baseline.paq8px215').read_bytes()
    if not proof['round_trip'] or not proof['trace_equals_reference']:raise ValueError('unqualified reference')
    if (codec.sha(data)!=proof['input_sha256'] or codec.sha(expected)!=proof['trace_sha256']
        or codec.sha(baseline)!=proof['frame_sha256']):raise ValueError('changed reference')
    fixed_root=codec.ROOT/'results/leaderboard/paq-register-prior-qualified/1'
    fixed_proof=json.loads((fixed_root/'complete.json').read_text());fixed_payload=(fixed_root/'stream.paq8px215').read_bytes()
    if (not fixed_proof['round_trip'] or not fixed_proof['original_predictions_byte_identical']
        or fixed_proof['input_sha256']!=proof['input_sha256'] or codec.sha(fixed_payload)!=fixed_proof['paq_sha256']):
        raise ValueError('unqualified or mismatched fixed-prior reference')
    paths=[Path(__file__),Path(codec.__file__),codec.ROOT/'benchmarks/build_paq_register_log.py',
        codec.ROOT/'benchmarks/build_paq_register_prior.py',codec.ROOT/'benchmarks/native/CixLogRegisterPrior.hpp',
        codec.ROOT/'benchmarks/native/CixLogMath.hpp',codec.ROOT/'benchmarks/native/CixLogTables.hpp',codec.FORK,
        codec.FORK.parent.parent/'provenance.json',codec.ROOT/'cix/multinomial.py']
    hashes={str(p):codec.sha(p.read_bytes()) for p in paths}
    root.mkdir(parents=True,exist_ok=True);rows=[]
    for mode in args.modes:
        folder=root/str(mode);folder.mkdir();source=folder/'source.bin';source.write_bytes(data)
        archive=folder/'stream.paq8px215';trace=folder/'predictions.u32';env=codec.environment(mode)
        env['CIX_REGISTER_BASE_TRACE']=str(trace)
        t=time.perf_counter()
        with (folder/'encode.stdout').open('wb') as out,(folder/'encode.stderr').open('wb') as err:
            subprocess.run([str(codec.FORK),'-4','-simd','AVX2',str(source),str(archive)],check=True,env=env,stdout=out,stderr=err)
        enc=time.perf_counter()-t;payload=archive.read_bytes();actual=trace.read_bytes()
        if actual!=expected:raise ValueError('native PAQ predictions changed')
        if mode==0 and payload!=baseline:raise ValueError('disabled payload differs')
        if mode==3 and payload!=fixed_payload:raise ValueError('fixed prior control differs')
        frame=codec.MAGIC+bytes([mode])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
        framepath=folder/'stream.cixb';framepath.write_bytes(frame)
        t=time.perf_counter();restored=codec.decode(framepath.read_bytes());dec=time.perf_counter()-t
        if restored!=data:raise ValueError('register log restore mismatch')
        if any(codec.sha(Path(p).read_bytes())!=value for p,value in hashes.items()):raise ValueError('register dependency changed')
        row=dict(mode=mode,physical_bytes=len(frame),paq_bytes=len(payload),native_paq_bytes=len(baseline),
            frame_sha256=codec.sha(frame),paq_sha256=codec.sha(payload),input_sha256=codec.sha(data),
            restored_sha256=codec.sha(restored),trace_sha256=codec.sha(actual),
            original_predictions_byte_identical=True,round_trip=True,diagnostic_only=True,
            options='-4 -simd AVX2',encode_seconds=enc,decode_seconds=dec,
            child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,source_hashes=hashes,
            revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=codec.ROOT,text=True).strip())
        (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
        print(json.dumps({k:row[k] for k in ('mode','physical_bytes','paq_bytes','original_predictions_byte_identical','round_trip')}),flush=True)
    report=dict(complete=True,diagnostic_only=True,reference_proof=proof,fixed_prior_reference=fixed_proof,rows=rows,
        interpretation='Causal register log mixture tested with arithmetic coding retained. Any gain adds predictive information; it is not rank-coding superiority with identical information.')
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
