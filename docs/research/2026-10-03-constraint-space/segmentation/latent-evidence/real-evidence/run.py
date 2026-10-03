import json,hashlib,importlib.util,os
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/latent-evidence/real-evidence';WORK=ROOT/'benchmark-work/latent-layout-real';RAW=AREA/'raw'
assert os.environ.get('CIX_REAL_LATENT_LEASE')=='1'
spec=importlib.util.spec_from_file_location('frozen_latent',AREA.parent/'run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.AREA=AREA;p.WORK=WORK;p.ARC=WORK/'archives';p.RAW=RAW;p.ARC.mkdir(parents=True,exist_ok=True);(WORK/'inputs').mkdir(exist_ok=True);rows=[];frozen=[]
for f in json.loads((AREA/'sources.json').read_text()):
 source=Path(f['source']);assert source.stat().st_size==f['source_bytes'];assert p.sha(source)==f['source_sha256'];inp=WORK/'inputs'/(f['name']+'.bin');assert not inp.exists()
 with source.open('rb')as s:inp.write_bytes(s.read(4096))
 item=dict(f,input=str(inp),input_bytes=inp.stat().st_size,input_sha256=p.sha(inp),offset=0);frozen.append(item);p.save('input-freeze.json',frozen);c={};refs={}
 for policy in ['whole','bss','uniform','mask-control','auto']:c[policy]=p.qualified(inp,policy,lambda a,policy=policy:[p.BIN,'encode','--policy',policy,inp,a],lambda a,o:[p.BIN,'decode',a,o])
 assert c['auto']['bytes']<=c['whole']['bytes']and c['auto']['bytes']<=c['bss']['bytes']
 for name,en,de in [('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c']),('cix_best',[p.CIX,'--best','--threads','1','--memory','1536MiB','-c'],[p.CIX,'-d','-c'])]:refs[name]=p.qualified(inp,name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],True)
 rows.append(dict(fixture=item,candidates=c,references=refs));p.save('results.json',rows);print(f['name'],{k:q['bytes']for k,q in c.items()},{k:q['bytes']for k,q in refs.items()},flush=True)
p.save('artifact-binding.json',dict(artifacts={str(q):dict(bytes=q.stat().st_size,sha256=p.sha(q))for q in WORK.rglob('*')if q.is_file()}))
