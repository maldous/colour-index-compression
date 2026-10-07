import json,hashlib,math,struct,zlib,sys,importlib.util,subprocess,os,time
from pathlib import Path
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/position-evidence';WORK=ROOT/'benchmark-work/record-positions';OLD=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';sys.path.insert(0,str(OLD));import oracle
spec=importlib.util.spec_from_file_location('oldrun',OLD/'run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.AREA=AREA;p.WORK=WORK;p.RAW=AREA/'raw';p.ARC=WORK/'archives';p.BIN=WORK/'build';p.ARC.mkdir(parents=True,exist_ok=True);p.RAW.mkdir(parents=True,exist_ok=True);BIN=p.BIN
assert os.environ.get('CIX_POSITION_LEASE')=='1'

def bounded_call(args,tag,out=None,allowed=False):
 start=time.monotonic()
 with (p.RAW/(tag+'.stderr')).open('wb')as err,(p.RAW/(tag+'.stdout')).open('wb')as txt:
  dest=Path(out).open('wb')if out else txt
  try:cp=subprocess.run(['/usr/bin/time','-v','-o',str(p.RAW/(tag+'.time')),*map(str,args)],stdout=dest,stderr=err,timeout=120 if 'cix_best'in tag else 30)
  finally:
   if out:dest.close()
 if not allowed:assert cp.returncode==0,(tag,(p.RAW/(tag+'.stderr')).read_text(errors='replace'))
 return dict(args=list(map(str,args)),exit=cp.returncode,wall_seconds=time.monotonic()-start)
p.call=bounded_call

def rxp(arc,src):
 d=arc.read_bytes();assert d[:4]==b'RXP1'and zlib.crc32(d[:-4])==int.from_bytes(d[-4:],'little');v,k,n,b,a0,a1,r,e,mask,cm,cp,codec,ml,pl,el=struct.unpack_from('<BBIBBBIIHBBBHHH',d,4);assert n==len(src) and len(d)==36+ml+pl+el
 if k==0:assert d[32:-4]==src;return dict(kind='raw',bytes=len(d))
 table=[v for v in range(1<<b)if all(not(mask>>j&1)or ((v>>(b-1-j))&1)==((v>>(b-2-j))&1)for j in range(b-1))and(cm==0 or cm==1 and v.bit_count()==cp or cm==2 and v.bit_count()<=cp)];words=[oracle.word(src[i:i+b],[a0,a1])for i in range(0,n,b)];bad=[i for i,x in enumerate(words)if x not in table];assert len(bad)==e;mapbytes=d[32:32+ml]
 if codec==0:assert ml==(oracle.width(math.comb(r,e))+7)//8 and int.from_bytes(mapbytes,'big')==sum(math.comb(pos,i+1)for i,pos in enumerate(bad))
 elif codec==1:
  start,step=struct.unpack('<HH',mapbytes);assert e>=2 and step>0 and bad==[start+i*step for i in range(e)]
 elif codec==2:
  cp=subprocess.run(['/bin/zstd','-d','-q','-c'],input=mapbytes,capture_output=True,timeout=5);assert cp.returncode==0;gaps=[bad[0]]+[bad[i]-bad[i-1]for i in range(1,e)]if e else[];assert cp.stdout==b''.join(x.to_bytes(2,'little')for x in gaps)
 else:raise AssertionError('map codec')
 rank=0
 for w in words:
  if w in table:rank=rank*len(table)+table.index(w)
 assert pl==(oracle.width(len(table)**(r-e))+7)//8 and int.from_bytes(d[32+ml:32+ml+pl],'big')==rank
 bits=''.join(f'{words[i]:0{b}b}'for i in bad);assert d[32+ml+pl:-4]==int((bits+'0'*((-len(bits))%8))or'0',2).to_bytes(el,'big')
 return dict(kind='exceptions',b=b,r=r,e=e,M=len(table),position_codec=['colex','progression','zstd-gaps'][codec],map_bytes=ml,payload_bytes=pl,exception_bytes=el,header_crc_bytes=36,bytes=len(d),independent_map=True,independent_payload=True)
rows=[]
for f in json.loads((AREA/'input-freeze.json').read_text()):
 inp=Path(f['input']);assert p.sha(inp)==f['input_sha256'];tag=f['name'];row=dict(fixture=f,candidates={},references={})
 for policy in ['auto','colex','zstd-gaps']:
  row['candidates'][policy]=p.qualified(policy,lambda a,policy=policy:[BIN/'rxp','encode','--positions',policy,inp,a],lambda a,o:[BIN/'rxp','decode',a,o],inp,tag,oracle=rxp)
 if'previous'in f:
  prev=f['previous']
  allbindings={}
  for packet in [OLD/'artifact-binding.json',ROOT/'docs/research/2026-10-03-constraint-space/record-evidence/artifact-binding.json']:allbindings.update(json.loads(packet.read_text())['artifacts'])
  for ref in [*prev['references'].values(),*prev['candidates'].values()]:
   if ref.get('status')!='verified':continue
   matches=[Path(path)for path,binding in allbindings.items()if binding['sha256']==ref['archive_sha256']]
   assert matches
   for path in matches:assert p.sha(path)==ref['archive_sha256']and path.stat().st_size==ref['bytes']
  row['references'].update(prev['references']);row['references']['rex']=prev['candidates']['exceptions'];row['references']['histogram']=prev['candidates'].get('histogram',prev['candidates']['exact_only']);row['references']['exact_only']=prev['candidates']['exact_only']
 else:
  rexbin=ROOT/'benchmark-work/record-exceptions/build/rex';rhcbin=ROOT/'benchmark-work/record-exceptions/build/rhc';rdic=ROOT/'benchmark-work/equality-records/build/rdic'
  for name,bin,oa in [('rex',rexbin,oracle.rex),('histogram',rhcbin,oracle.rhc),('record_dictionary',rdic,None)]:row['references'][name]=p.qualified(name,lambda a,bin=bin:[bin,'encode',inp,a],lambda a,o,bin=bin:[bin,'decode',a,o],inp,tag,oracle=oa)
  for name,en,de in [('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c'])]:row['references'][name]=p.qualified(name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],inp,tag,stdout=True)
  cix=ROOT/'benchmark-work/release-d3a2/final/cix';row['references']['cix_best']=p.qualified('cix_best',lambda a:[cix,'--best','--threads','1','--memory','1536MiB','-c',inp],lambda a,o:[cix,'-d','-c',a],inp,tag,stdout=True)
 rows.append(row);p.save('results.json',rows);print(tag,{k:v['bytes']for k,v in row['candidates'].items()},flush=True)
# Progression corruption and backend trailing bytes are semantic malformed tests.
a=next(Path(x['candidates']['auto']['archive'])for x in rows if x['candidates']['auto']['oracle'].get('position_codec')=='progression');base=a.read_bytes();variants={'truncated':base[:-1],'CRC':bytearray(base),'step0':bytearray(base),'start_range':bytearray(base),'codec':bytearray(base),'maplength':bytearray(base),'count':bytearray(base),'rank':bytearray(base)};variants['CRC'][32]^=1;variants['step0'][34:36]=b'\0\0';variants['start_range'][32:34]=b'\xff\xff';variants['codec'][25]=3;variants['maplength'][26]^=1;variants['count'][17:21]=(int.from_bytes(base[13:17],'little')+1).to_bytes(4,'little');ml=int.from_bytes(base[26:28],'little');pl=int.from_bytes(base[28:30],'little');variants['rank'][32+ml:32+ml+pl]=b'\xff'*pl;bad=[]
for name,d in variants.items():
 d=bytearray(d)
 if name not in['truncated','CRC']:d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little')
 arc=p.ARC/('bad-'+name+'.arc');out=arc.with_suffix('.out');arc.write_bytes(d);run=p.call([BIN/'rxp','decode',arc,out],'bad-'+name,allowed=True);assert run['exit']and not out.exists();bad.append(dict(name=name,run=run))
a=next(Path(x['candidates']['zstd-gaps']['archive'])for x in rows if x['candidates']['zstd-gaps']['oracle'].get('position_codec')=='zstd-gaps');d=bytearray(a.read_bytes());ml=int.from_bytes(d[26:28],'little');d[26:28]=(ml+1).to_bytes(2,'little');d[32+ml:32+ml]=b'\0';d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');arc=p.ARC/'bad-zstd-trailing.arc';out=arc.with_suffix('.out');arc.write_bytes(d);run=p.call([BIN/'rxp','decode',arc,out],'bad-zstd-trailing',allowed=True);assert run['exit']and not out.exists();bad.append(dict(name='zstd_trailing',run=run));p.save('malformed.json',bad)
p.save('artifact-binding.json',dict(artifacts={str(x):dict(bytes=x.stat().st_size,sha256=p.sha(x))for x in sorted(WORK.rglob('*'))if x.is_file()}))
