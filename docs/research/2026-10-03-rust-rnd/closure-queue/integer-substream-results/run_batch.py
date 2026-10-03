import json,hashlib,subprocess,zlib
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');base=root/'benchmark-work/closure-integer';work=base/'runs';area=root/'docs/research/2026-10-03-rust-rnd/closure-queue/integer-substream-results';exe=base/'build/isc';plan=json.loads((root/'docs/research/2026-10-03-rust-rnd/closure-queue/integer-substream-plan/freeze.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={}
for case in ['strong','weak','absent']:
 p=work/(case+'.input');subprocess.run([str(exe),'generate',case,str(p)],check=True);inputs[case]={'sha256':sha(p),'bytes':p.stat().st_size};assert inputs[case]=={k:plan['input_schema']['fixtures'][case][k]for k in ['sha256','bytes']}
(area/'execution-binding.json').write_text(json.dumps({'before_codec':True,'binary_sha256':sha(exe),'inputs':inputs},indent=2)+'\n')
rows=[]
for case in inputs:
 for coder in ['varint','gamma','delta','rice:0','rice:2','rice:4','rice:8']:
  stem=work/(case+'-'+coder.replace(':','-'));arc=stem.with_suffix('.isc');out=stem.with_suffix('.restored');tf=stem.with_suffix('.time')
  v=subprocess.run(['/usr/bin/time','-v','-o',str(tf),str(exe),'encode',coder,str(work/(case+'.input')),str(arc),str(out)],capture_output=True,text=True,timeout=30);(area/'raw'/tf.name).write_bytes(tf.read_bytes());(area/'raw'/(stem.name+'.stdout')).write_text(v.stdout);(area/'raw'/(stem.name+'.stderr')).write_text(v.stderr);assert v.returncode==0,v.stderr
  row=json.loads(v.stdout);assert row['fresh_archive_only_decode'] and sha(out)==inputs[case]['sha256']
  fresh=stem.with_suffix('.fresh-restored');dt=stem.with_suffix('.decode.time');d=subprocess.run(['/usr/bin/time','-v','-o',str(dt),str(exe),'decode',str(arc),str(fresh)],capture_output=True,text=True,timeout=30);(area/'raw'/dt.name).write_bytes(dt.read_bytes());assert d.returncode==0 and sha(fresh)==inputs[case]['sha256']
  row.update(case=case,archive_sha256=sha(arc),restored_sha256=sha(out),fresh_measured_restored_sha256=sha(fresh),encode_time_log=tf.name,decode_time_log=dt.name);rows.append(row)
  (area/'results.json').write_text(json.dumps({'status':'VERIFIED'if len(rows)==21 else'PARTIAL','rows':rows},indent=2)+'\n')
valid=(work/'strong-gamma.isc').read_bytes();bad=[]
for name,data in [('crc',valid[:-1]+bytes([valid[-1]^1])),('truncated',valid[:-1]),('coder',valid[:5]+b'\xff'+valid[6:])]:
 p=work/(name+'.bad');p.write_bytes(data);out=work/(name+'.out');v=subprocess.run([str(exe),'decode',str(p),str(out)],capture_output=True,text=True,timeout=30);assert v.returncode!=0 and'panicked'not in v.stderr and not out.exists();bad.append({'case':name,'exit':v.returncode,'stderr':v.stderr})
(area/'malformed.json').write_text(json.dumps(bad,indent=2)+'\n')
