import json,hashlib,os,subprocess,time,struct,zlib
from pathlib import Path
assert os.environ.get('CIX_ATTR_LEASE')=='1'
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/attribution-evidence';RAW=AREA/'raw';WORK=ROOT/'benchmark-work/segmentation-attribution';ARC=WORK/'archives';BIN=ROOT/'benchmark-work/segmentation-masks/build/zsc'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):(AREA/p).write_text(json.dumps(x,indent=2)+'\n')
def call(args,tag):
 (RAW/(tag+'.command.json')).write_text(json.dumps(list(map(str,args)))+'\n')
 with (RAW/(tag+'.stdout')).open('wb') as out,(RAW/(tag+'.stderr')).open('wb') as err:
  start=time.monotonic();cp=subprocess.run(['/usr/bin/time','-v','-o',str(RAW/(tag+'.time')),*map(str,args)],stdout=out,stderr=err,timeout=30)
 assert cp.returncode==0,(tag,(RAW/(tag+'.stderr')).read_text());return dict(wall_seconds=time.monotonic()-start,exit=cp.returncode)
ARC.mkdir(parents=True,exist_ok=True);rows=[]
for old in json.loads((AREA/'input-freeze.json').read_text()):
 f=old['fixture'];inp=Path(f['input']);assert sha(inp)==f['input_sha256'];name=f['name'];c={};cache={};native=old['candidates']['auto'];ref=old['references']['matched_zstd'];s=native['trace']['selected_stride'];m=native['trace']['selected_mask']
 assert sha(ref['archive'])==ref['archive_sha256'] and sha(native['archive'])==native['archive_sha256'];cache[s,m]=dict(ref,reused=True)
 def trial(w,mask):
  if (w,mask) in cache:return cache[w,mask]
  tag=f'{name}-w{w}-m{mask}';a=ARC/(tag+'.arc');o=ARC/(tag+'.restored');assert not a.exists()
  en=call([BIN,'encode','--stride',w,'--mask',mask,inp,a],tag+'-encode');de=call([BIN,'decode',a,o],tag+'-decode');assert sha(o)==f['input_sha256'];b=a.read_bytes();n,crc,ww,mm,k,pl=struct.unpack_from('<IIBBHI',b,5);assert b[:5]==b'ZSC1\2' and n==f['input_bytes']and crc==zlib.crc32(inp.read_bytes()) and(w,mask)==(ww,mm)and len(b)==21+pl
  q=dict(bytes=len(b),archive=str(a),archive_sha256=sha(a),restored_sha256=sha(o),encode=en,decode=de,accounting=dict(metadata_bytes=21,payload_bytes=pl),reused=False);cache[w,mask]=q;return q
 c['A_original_zstd']=trial(1,0)
 c['B_fixed_BSS']={str(w):trial(w,0)for w in range(2,min(8,f['input_bytes'])+1)}
 c['C_native_inferred_literal']=trial(s,0)
 c['D_native_width_all_residual']=trial(s,(1<<s)-2)
 c['E_native_selected_mask_zstd']=cache[s,m]
 c['F_native_selected']=dict(native,reused=True)
 bestlit=min([c['A_original_zstd'],*c['B_fixed_BSS'].values()],key=lambda q:q['bytes'])
 delta=dict(lane_separation_at_native_width=c['A_original_zstd']['bytes']-c['C_native_inferred_literal']['bytes'],best_fixed_BSS_gain=c['A_original_zstd']['bytes']-bestlit['bytes'],all_residual_gain=c['C_native_inferred_literal']['bytes']-c['D_native_width_all_residual']['bytes'],selective_over_all=c['D_native_width_all_residual']['bytes']-c['E_native_selected_mask_zstd']['bytes'],selective_over_literal=c['C_native_inferred_literal']['bytes']-c['E_native_selected_mask_zstd']['bytes'],native_to_same_layout_zstd=c['F_native_selected']['bytes']-c['E_native_selected_mask_zstd']['bytes'],wrapper_metadata_bytes=21)
 rows.append(dict(fixture=f,native_geometry=dict(width=s,mask=m),arms=c,deltas=delta,unique_new_cells=sum(not q['reused'] for q in cache.values())));save('results.json',rows);print(name,{k:(v['bytes']if'bytes'in v else{k2:q['bytes']for k2,q in v.items()})for k,v in c.items()},flush=True)
save('artifact-binding.json',dict(artifacts={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in WORK.rglob('*')if p.is_file()}))
