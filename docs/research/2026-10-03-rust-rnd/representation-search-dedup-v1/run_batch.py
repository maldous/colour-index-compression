import hashlib,json,subprocess,time,zlib,os
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');area=root/'docs/research/2026-10-03-rust-rnd/representation-search-dedup-v1';work=root/'benchmark-work/representation-search-dedup-v1/runs';exe=root/'benchmark-work/representation-search-dedup-v1/build/rsl1';f=json.loads((area/'freeze.json').read_text());binding=json.loads((area/'execution-binding.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().strip().split(':')[-1])
def receipt():return {k:(cg/k).read_text().strip() for k in ['cpu.max','cpuset.cpus.effective','memory.max','memory.current','memory.peak','memory.swap.max','memory.events']}
os.environ['PATH']='/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
before=receipt();assert before['cpu.max']=='100000 100000' and before['memory.max']=='1073741824' and before['cpuset.cpus.effective']=='20' and before['memory.swap.max']=='0'
assert sha(exe)==binding['binary_sha256'];inp=root/f['input']['path'];assert sha(inp)==f['input']['sha256']
out=work/'selected.rsl1';report=work/'screen.jsonl';started=time.monotonic()
subprocess.run([str(exe),'screen',str(inp),str(out),str(report),str(root/f['backend_control']['cix']),str(root/f['backend_control']['uncix']),'fast'],cwd=root,check=True)
rows=[json.loads(line) for line in report.read_text().splitlines()]; candidates=[r for r in rows if 'candidate' in r]; assert len(candidates)==12 and all(r['verified'] for r in candidates)
selected=rows[-1];assert selected['complete_bytes']==min(r['complete_bytes'] for r in candidates) and selected['fresh_archive_only_decode']
for r in candidates:
    r['transformed_sha256']=sha(work/'rsl1-scratch'/f"{r['candidate']:03}.raw")
    if r['backend']!='raw':r['nested_archive_sha256']=sha(Path(r['nested_archive']))
baseline=json.loads((root/f['baseline']['results']).read_text()); baseline_rows=[r for r in baseline['rows'] if 'candidate' in r]; assert [r['complete_bytes'] for r in candidates]==[r['complete_bytes'] for r in baseline_rows]; assert sum(r['native_trial_performed'] for r in candidates)==9; assert sha(out)==f['baseline']['selected_archive_sha256']; assert out.read_bytes()==(root/f['baseline']['selected_archive']).read_bytes()
for current, prior in zip(candidates,baseline_rows):
    assert all(current[k]==prior[k] for k in ['candidate','program','backend','backend_payload_bytes','instruction_bytes','complete_bytes'])
    if current['backend']!='raw':assert current['nested_archive_sha256']==prior['nested_archive_sha256']
assert [(r['candidate'],r['reused_from']) for r in candidates if r['reused_from'] is not None]==[(7,3),(8,4)]
assert all(r['cache_bytes']<=4194304 for r in candidates)
restored=work/'rsl1-scratch/selected.archive-only.restored';assert sha(restored)==sha(inp)
valid=out.read_bytes();body=valid[:-4]
def seal(b):return bytes(b)+zlib.crc32(b).to_bytes(4,'little')
op=bytearray(body);op[23]=255
bad=[]
for name,data in [('bad-crc',valid[:-1]+bytes([valid[-1]^1])),('invalid-opcode',seal(op)),('truncated-body',seal(body[:-1])),('trailing-body',seal(body+b'!'))]:
    p=work/(name+'.bad');p.write_bytes(data);dest=work/(name+'.restored');r=subprocess.run([str(exe),'decode',str(p),str(dest),str(root/f['backend_control']['uncix'])],cwd=root,capture_output=True,text=True)
    assert r.returncode!=0 and 'panicked' not in r.stderr and not dest.exists();bad.append({'case':name,'exit_code':r.returncode,'stderr':r.stderr})
(area/'results.json').write_text(json.dumps({'status':'VERIFIED_SINGLE_SCREEN','rows':rows,'selected_archive_sha256':sha(out),'restored_sha256':sha(restored),'input_sha256':sha(inp),'malformed':bad,'elapsed_seconds':time.monotonic()-started,'cgroup_before':before,'cgroup_after':receipt(),'retained_run_bytes':sum(p.stat().st_size for p in work.rglob('*') if p.is_file())},indent=2)+'\n')
