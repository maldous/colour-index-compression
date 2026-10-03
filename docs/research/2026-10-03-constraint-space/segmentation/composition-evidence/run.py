"""Frozen SMC1 matrix. Root runs only inside the scheduler lease."""
import hashlib,json,os,signal,struct,subprocess,time
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression'); AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/composition-evidence'; WORK=ROOT/'benchmark-work/constraint-composition-m6'; RAW=AREA/'raw'; BUILD=WORK/'build'; WRAP=BUILD/'representation_m6_wrapper'; CIX=ROOT/'benchmark-work/release-d3a2/final/cix'; SOURCE=Path('/home/user/cix-datasets/originals/fcbench/citytemp_f32')
SOURCE_SHA='3f8ba1a80684edea13185934a2ec4a612715f1942f81e94d76c60e00b568ba7f'; CIX_SHA='f9b8262086be9704d8d9425ccbf5cbf5274096ae88334ea1501aa4773034fac3'
D=[('original',1,0,[0]),*[(f'mask{i}',4,0,[0,2 if i&1 else 0,2 if i&2 else 0,2 if i&4 else 0])for i in range(8)],('E',4,0,[0,2,1,0]),('drop-prevcol',4,0,[0,0,1,0]),('row-xor',4,0,[0,2,4,0]),('last-residual',4,0,[0,2,1,2]),('phase-one',4,1,[0,2,1,0]),('width-three',3,0,[0,2,1])];assert len(D)==15
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def save(n,x):(AREA/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def oarg(o):return ','.join(map(str,o))
def call(tag,args,out=None,timeout=120):
 RAW.mkdir(parents=True,exist_ok=True);(RAW/(tag+'.command.json')).write_text(json.dumps({'argv':list(map(str,args))},indent=2)+'\n');start=time.monotonic()
 with (RAW/(tag+'.stderr')).open('wb')as err,(RAW/(tag+'.stdout')).open('wb')as stdout:
  dst=Path(out).open('wb')if out else stdout;p=subprocess.Popen(['/usr/bin/time','-v','-o',str(RAW/(tag+'.time')),*map(str,args)],stdout=dst,stderr=err,start_new_session=True)
  try:p.wait(timeout=timeout)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();raise AssertionError((tag,'timeout',timeout))
  finally:
   if out:dst.close()
 r={'argv':list(map(str,args)),'exit':p.returncode,'wall_seconds':time.monotonic()-start,'time_receipt':str(RAW/(tag+'.time'))};assert p.returncode==0,(tag,(RAW/(tag+'.stderr')).read_text(errors='replace'));return r
def tr(x,w,p,o):
 y=bytearray(x[:p])
 for j,v in enumerate(o):
  for r,i in enumerate(range(p+j,len(x),w)):y.append(x[i]if r==0 or v==0 else (x[i]-x[i-w])&255 if v==1 else (x[i]-x[i-1])&255 if v==2 else x[i]^x[i-1]if v==3 else x[i]^x[i-w])
 return bytes(y)
def inv(y,n,w,p,o):
 x=bytearray(n);x[:p]=y[:p];q=p
 for j,v in enumerate(o):
  for r,i in enumerate(range(p+j,n,w)):
   b=y[q];q+=1;x[i]=b if r==0 or v==0 else (b+x[i-w])&255 if v==1 else (b+x[i-1])&255 if v==2 else b^x[i-1]if v==3 else b^x[i-w]
 assert q==n;return bytes(x)
def account(a):
 b=Path(a).read_bytes();assert b[:5]==b'SMC1\x01';n,tn,c=struct.unpack_from('<III',b,6);w,p,k=b[18:21];at=21+w;pl=struct.unpack_from('<I',b,at)[0];assert n==tn and k==w and at+4+pl==len(b);return {'complete_bytes':len(b),'fixed_header_bytes':25,'operator_bytes':w,'payload_bytes':pl,'backend_id':b[5],'source_bytes':n,'source_crc32':c,'width':w,'phase':p,'operators':list(b[21:at])}
def run_fixture(role,offset):
 arc=WORK/'archives'/role;inp=WORK/'inputs'/role;arc.mkdir(parents=True,exist_ok=True);inp.mkdir(parents=True,exist_ok=True);result='results.json'if role=='qualification'else 'replication-results.json';freeze='input-freeze.json'if role=='qualification'else 'replication-input-freeze.json';assert not(AREA/result).exists()and not(AREA/freeze).exists()
 meta={'role':role,'source':str(SOURCE),'source_bytes':11625304,'source_sha256':SOURCE_SHA,'offset':offset,'length':4096,'input':str(inp/'slice.bin'),'exposure_statement':'algorithmically unexposed by reviewed receipts; not an absolute historical-read claim'};save(freeze,meta)
 with SOURCE.open('rb')as f:f.seek(offset);source=f.read(4096)
 assert len(source)==4096;ip=inp/'slice.bin';ip.write_bytes(source);expected=sha(ip);meta['input_sha256']=expected;save(freeze,meta)
 oracle=[]
 for name,w,p,o in D:
  for q in(source,bytes(range(13))):
   if w<=len(q)-p:t=tr(q,w,p,o);assert inv(t,len(q),w,p,o)==q;oracle.append({'descriptor':name,'bytes':len(q),'transformed_sha256':hashlib.sha256(t).hexdigest()})
 save(role+'-transform-oracle.json',oracle)
 bare={}; specs=[('bare_m6',[CIX,'--best','--format','cixm6','--threads','1','--memory','1536MiB','--block-size','16KiB','-c',ip],[CIX,'-d','--threads','1','--memory','1536MiB','-c']),('bare_zstd',['/bin/zstd','-q','-19','-T1','-c',ip],['/bin/zstd','-d','-q','-c']),('gzip9',['/bin/gzip','-n','-9','-c',ip],['/bin/gzip','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c',ip],['/bin/bzip2','-d','-c']),('xz9e',['/bin/xz','-9e','-T1','-c',ip],['/bin/xz','-d','-c'])]
 for n,en,de in specs:
  body=arc/(n+'.body');e=call(role+'-'+n+'-encode',en,body);out=arc/(n+'.restored');d0=call(role+'-'+n+'-decode',[*de,body],out);assert out.read_bytes()==source and sha(out)==expected;bare[n]={'archive':str(body),'archive_sha256':sha(body),'bytes':body.stat().st_size,'encode':e,'decode':d0}
 cache={('m6',source):{'body':Path(bare['bare_m6']['archive']),'encode':bare['bare_m6']['encode']},('zstd',source):{'body':Path(bare['bare_zstd']['archive']),'encode':bare['bare_zstd']['encode']}};rows=[]
 for n,w,p,o in D:
  tag=n.replace('-','_');tp=inp/(tag+'.transformed');tx=call(role+'-'+tag+'-transform',[WRAP,'transform','--width',str(w),'--phase',str(p),'--ops',oarg(o),ip,tp]);t=tp.read_bytes();assert t==tr(source,w,p,o);row={'descriptor':{'name':n,'width':w,'phase':p,'operators':o},'transform':tx,'transformed_sha256':hashlib.sha256(t).hexdigest(),'backends':{}}
  for backend,en in [('m6',[CIX,'--best','--format','cixm6','--threads','1','--memory','1536MiB','--block-size','16KiB','-c',tp]),('zstd',['/bin/zstd','-q','-19','-T1','-c',tp])]:
   key=(backend,t);hit=key in cache
   if not hit:
    body=arc/(backend+'-'+sha(tp)+'.body');cache[key]={'body':body,'encode':call(role+'-'+backend+'-'+sha(tp),en,body)}
   item=cache[key];assert item and t==key[1] # exact transformed bytes, never SHA alone
   out=arc/(tag+'-'+backend+'.smc');pk=call(role+'-'+tag+'-'+backend+'-pack',[WRAP,'pack','--backend',backend,'--width',str(w),'--phase',str(p),'--ops',oarg(o),ip,item['body'],out]);restore=out.with_suffix('.restored');dc=call(role+'-'+tag+'-'+backend+'-decode',[WRAP,'decode','--cix',CIX,out,restore]);assert restore.read_bytes()==source and sha(restore)==expected;row['backends'][backend]={'archive':str(out),'archive_sha256':sha(out),'bytes':out.stat().st_size,'pack':pk,'decode':dc,'backend_encode':item['encode'],'cache_hit':hit,'accounting':account(out)}
  out=arc/(tag+'-native.smc');ne=call(role+'-'+tag+'-native',[WRAP,'native','--width',str(w),'--phase',str(p),'--ops',oarg(o),ip,out]);restore=out.with_suffix('.restored');nd=call(role+'-'+tag+'-native-decode',[WRAP,'decode','--cix',CIX,out,restore]);assert restore.read_bytes()==source and sha(restore)==expected;row['backends']['native']={'archive':str(out),'archive_sha256':sha(out),'bytes':out.stat().st_size,'encode':ne,'decode':nd,'accounting':account(out)}
  rows.append(row);save(result,{'role':role,'bare_controls':bare,'rows':rows,'unique_backend_trials':len(cache)});print(role,n,{k:v['bytes']for k,v in row['backends'].items()},flush=True)
 return bare,rows
def main():
 assert os.environ.get('CIX_COMPOSITION_LEASE')=='1'and sha(CIX)==CIX_SHA and SOURCE.stat().st_size==11625304 and sha(SOURCE)==SOURCE_SHA;RAW.mkdir(parents=True,exist_ok=True);bare,rows=run_fixture('qualification',1048576);e=next(r for r in rows if r['descriptor']['name']=='E')['backends']['m6']['bytes'];m=[r['backends']['m6']['bytes']for r in rows if r['descriptor']['name'].startswith('mask')];gate=e<bare['bare_m6']['bytes']and all(e<x for x in m);save('replication-gate.json',{'E_m6_complete_bytes':e,'bare_m6_bytes':bare['bare_m6']['bytes'],'ordinary_mask_m6_complete_bytes':m,'triggered':gate})
 if gate:run_fixture('replication',2097152)
 save('artifact-binding.json',{'artifacts':{str(p):{'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(WORK.rglob('*'))if p.is_file()}})
if __name__=='__main__':main()
