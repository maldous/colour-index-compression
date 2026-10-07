"""Measure causal register log mixtures with all model/framing costs counted."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time
import zlib
from cix.multinomial import vencode, vdecode
from benchmarks.competitive_codec import paq_binary, sha

ROOT = Path(__file__).resolve().parents[1]
FORK = ROOT/'benchmark-work/references/paq8px-cix-register-log/build-local/paq8px'
MAGIC = b'CIXB\x1b'


def environment(mode):
    env = {k:v for k,v in os.environ.items() if not k.startswith('CIX_')}
    if mode < 4: env['CIX_REGISTER_LOG'] = str(mode)
    return env


def binary(mode): return Path(paq_binary('v215')) if mode == 4 else FORK


def encode(data, mode=1, options='-4'):
    if mode not in range(5): raise ValueError('invalid register log mode')
    raw, stats = data, {}
    with tempfile.TemporaryDirectory(prefix='cix-register-log-') as folder:
        folder = Path(folder); source = folder/'source.bin'; archive = folder/'stream.paq8px215'; source.write_bytes(raw)
        subprocess.run([str(binary(mode)),options,'-simd','AVX2',str(source),str(archive)],check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment(mode))
        payload = archive.read_bytes()
    frame = MAGIC + bytes([mode]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4,'big') + payload
    return frame, dict(mode=mode,original_bytes=len(data),transformed_sha256=sha(raw),parent_stats=stats,paq_sha256=sha(payload))


def decode(frame):
    if frame[:5] != MAGIC or len(frame) < 11 or frame[5] not in range(5): raise ValueError('invalid register log frame')
    mode = frame[5]; n, pos = vdecode(frame, 6); crc = int.from_bytes(frame[pos:pos+4],'big')
    with tempfile.TemporaryDirectory(prefix='cix-register-log-') as folder:
        folder = Path(folder); archive = folder/'stream.paq8px215'; output = folder/'restored.bin'; archive.write_bytes(frame[pos+4:])
        subprocess.run([str(binary(mode)),'-d','-simd','AVX2',str(archive),str(output)],check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=environment(mode))
        data = output.read_bytes()
    if len(data) != n or zlib.crc32(data) != crc: raise ValueError('register log source checksum mismatch')
    return data


def worker(spec):
    path, mode, options, root = spec; data = Path(path).read_bytes(); folder = Path(root)/f'{Path(path).stem}-{mode}'
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'stream.cixb').exists(): raise ValueError('preserve existing register log trial')
    provenance = ROOT/'benchmark-work/references/paq8px-cix-register-log/provenance.json'
    paths = [Path(__file__),ROOT/'benchmarks/build_paq_register_log.py',binary(mode),provenance,
             ROOT/'benchmarks/build_paq_register_prior.py',ROOT/'benchmarks/native/CixLogRegisterPrior.hpp',
             ROOT/'benchmarks/native/CixLogMath.hpp',ROOT/'benchmarks/native/CixLogTables.hpp',ROOT/'cix/multinomial.py']
    hashes = {str(p):sha(p.read_bytes()) for p in paths}; revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    t = time.perf_counter(); frame, stats = encode(data,mode,options); enc = time.perf_counter()-t; (folder/'stream.cixb').write_bytes(frame)
    t = time.perf_counter(); restored = decode((folder/'stream.cixb').read_bytes()); dec = time.perf_counter()-t
    if restored != data: raise ValueError('register log round trip failed')
    if any(sha(Path(p).read_bytes()) != value for p,value in hashes.items()): raise ValueError('register log dependency changed')
    row = dict(stats,input_path=path,input_sha256=sha(data),restored_sha256=sha(restored),frame_sha256=sha(frame),
               physical_bytes=len(frame),round_trip=True,diagnostic_only=True,complete_silesia_member=False,
               options=options,source_hashes=hashes,revision=revision,encode_seconds=enc,decode_seconds=dec,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    (folder/'complete.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:row[k] for k in ['input_path','mode','physical_bytes','round_trip']}),flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True)
    parser.add_argument('--manifest',default='results/leaderboard/ecoff-got-cohorts-v2/manifest.json')
    parser.add_argument('--modes',nargs='+',type=int,default=[4,0,1,2,3]); parser.add_argument('--jobs',type=int,default=2)
    parser.add_argument('--options',default='-4'); args = parser.parse_args(); root = Path(args.output).resolve(); root.mkdir(parents=True,exist_ok=True)
    manifest = json.loads(Path(args.manifest).read_text()); specs = []
    for row in manifest['rows']:
        if sha(Path(row['path']).read_bytes()) != row['sha256']: raise ValueError('GP cohort input changed')
        specs += [(row['path'],mode,args.options,str(root)) for mode in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs,max_tasks_per_child=1) as pool: rows = list(pool.map(worker,specs))
    controls = {}
    for row in rows:
        if row['mode'] in (0,4): controls.setdefault(row['input_path'],{})[row['mode']] = row['paq_sha256']
    for path, pair in controls.items():
        if set(pair)=={0,4} and pair[0]!=pair[4]: raise ValueError('disabled model differs from original PAQ: '+path)
    report = dict(complete=True,diagnostic_only=True,control_matches_reference=all(set(x)=={0,4} and x[0]==x[4] for x in controls.values()),rows=rows)
    (root/'complete.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':main()
