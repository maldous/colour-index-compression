import hashlib,json,subprocess,time,zlib
from pathlib import Path
root=Path('/home/user/src/colour-index-compression'); area=root/'docs/research/2026-10-03-rust-rnd/histogram-reuse-v1'; work=root/'benchmark-work/histogram-reuse-v1/runs-v2'; exe=root/'benchmark-work/histogram-reuse-v1/build-v2/hrv'; decoder=root/'benchmark-work/conditional-cost-v1/build/conditional-cost-v1'
binding=json.loads((area/'execution-binding.json').read_text()); freeze=json.loads((area/'freeze.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args):return subprocess.run([str(x) for x in args],cwd=root,capture_output=True,text=True,check=True).stdout
def timed(args,log):return call(['/usr/bin/time','-v','-o',log,*args])
cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().strip().split(':')[-1])
def receipt():return {k:(cg/k).read_text().strip() for k in ['cpu.max','cpuset.cpus.effective','memory.max','memory.current','memory.peak','memory.swap.max','memory.events']}
before=receipt();assert before['cpu.max']=='100000 100000' and before['memory.max']=='805306368' and before['cpuset.cpus.effective']=='20' and before['memory.swap.max']=='0'
assert sha(exe)==binding['driver_binary_sha256'] and sha(decoder)==binding['decoder_sha256']
assert sha(root/binding['source_path'])==freeze['build']['driver_sha256']
items=[]
for case in ['identical','weak','absent']:
    native=work/(case+'.cixcc');call([exe,'fixture',case,native]); original=work/(case+'.original.source'); call([exe,'decode-source',native,original]); assert sha(original)==freeze['decoded_source_sha256'][case]; items.append((case,native,freeze['decoded_source_sha256'][case]))
for p in binding['frozen_archives']:
    path=root/p['path'];assert sha(path)==p['sha256'];items.append((path.stem,path,p['source_sha256']))
rows=[];started=time.monotonic()
for label,native,expected in items:
    packed=work/(label+'.hrv'); restored=work/(label+'.restored.cixcc'); source=work/(label+'.restored')
    row=json.loads(timed([exe,'pack',native,packed],work/(label+'.pack.time')))
    timed([exe,'unpack',packed,restored],work/(label+'.unpack.time'))
    assert sha(native)==sha(restored)
    call([exe,'decode-source',restored,source]);assert sha(source)==expected
    row.update(label=label,native_sha256=sha(native),packed_sha256=sha(packed),restored_native_sha256=sha(restored),restored_source_sha256=sha(source),source_bytes=source.stat().st_size,fresh_exact_restoration=True)
    rows.append(row);print(label,row['native_bytes'],row['histogram_reuse_bytes'],row['delta_bytes'],flush=True)
    assert sum(p.stat().st_size for p in work.rglob('*') if p.is_file())<=1048576
valid=(work/'identical.hrv').read_bytes(); malformed=[]
body=valid[:-4]
def sealed(data):return bytes(data)+zlib.crc32(data).to_bytes(4,'little')
invalid_tag=bytearray(body);invalid_tag[48]=2
invalid_ref=bytearray(body);invalid_ref[48]=1;invalid_ref[51]=127
native_crc=bytearray(body);native_crc[17]^=1
for label,data in [('bad-envelope',valid[:-1]+bytes([valid[-1]^1])),('invalid-tag',sealed(invalid_tag)),('invalid-reference',sealed(invalid_ref)),('truncated-body',sealed(body[:-1])),('trailing-body',sealed(body+b'!')),('native-crc-mismatch',sealed(native_crc))]:
    path=work/(label+'.bad');path.write_bytes(data);r=subprocess.run([str(exe),'unpack',str(path),str(work/(label+'.out'))],capture_output=True,text=True)
    assert r.returncode!=0 and 'panicked' not in r.stderr and not (work/(label+'.out')).exists()
    malformed.append({'case':label,'exit_code':r.returncode,'stderr':r.stderr})
(area/'results.json').write_text(json.dumps({'status':'VERIFIED_SINGLE_SCREEN','rows':rows,'malformed':malformed,'elapsed_seconds':time.monotonic()-started,'cgroup_before':before,'cgroup_after':receipt(),'retained_run_bytes':sum(p.stat().st_size for p in work.rglob('*') if p.is_file())},indent=2)+'\n')
