from pathlib import Path
import hashlib,json,subprocess,time,os,zlib,math
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/record-evidence';WORK=ROOT/'benchmark-work/equality-records';BIN=WORK/'build/erc'
CIX=ROOT/'benchmark-work/release-d3a2/final/cix'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args,name,output=None):
 dest=AREA/'raw';t=time.monotonic()
 try:
  with open(output,'wb') if output else open(dest/(name+'.stdout'),'wb') as out,open(dest/(name+'.stderr'),'wb') as err:
   p=subprocess.run(['/usr/bin/time','-v','-o',str(dest/(name+'.time')),*map(str,args)],stdout=out,stderr=err,timeout=120,env={**os.environ,'LD_LIBRARY_PATH':str(CIX.parent)})
  code=p.returncode
 except subprocess.TimeoutExpired:code='timeout'
 return dict(args=list(map(str,args)),exit=code,wall_seconds=time.monotonic()-t)
versions={}
for tool,args in [('zstd',['/bin/zstd','--version']),('xz',['/bin/xz','--version']),('bzip2',['/bin/bzip2','--help']),('gzip',['/bin/gzip','--version']),('cix',[str(CIX),'--version']),('rustc',['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc','--version','--verbose']),('hardware',['/bin/lscpu'])]:
 p=subprocess.run(args,capture_output=True,text=True,env={**os.environ,'LD_LIBRARY_PATH':str(CIX.parent)});versions[tool]=dict(args=args,exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
(AREA/'versions.json').write_text(json.dumps(versions,indent=2)+'\n')
rows=[]
for fixture in json.loads((AREA/'input-freeze.json').read_text()):
 name=fixture['name'];inp=Path(fixture['path']);assert sha(inp)==fixture['sha256'];modes={};references={}
 print('encoding',name,flush=True)
 for mode in ['raw','e','c','ec','auto']:
  arc=WORK/'archives'/f'{name}-{mode}.erc';rest=WORK/'archives'/f'{name}-{mode}.restored'
  enc=call([BIN,'encode',mode,inp,arc],name+'-'+mode+'-encode')
  if enc['exit']!=0:modes[mode]=dict(status='unsupported_or_failed',encode=enc);continue
  dec=call([BIN,'decode',arc,rest],name+'-'+mode+'-decode');assert dec['exit']==0 and sha(rest)==fixture['sha256']
  data=arc.read_bytes();assert int.from_bytes(data[-4:],'little')==zlib.crc32(data[:-4])
  n=int.from_bytes(data[6:10],'little');b=data[10];mask=int.from_bytes(data[11:13],'little');h=data[13];w=int.from_bytes(data[16:20],'little')
  local_count=None;rank_oracle=None
  if data[5]!=0:
   table=[v for v in range(1<<b) if (data[5]==2 or all(not(mask>>j&1)or ((v>>(b-1-j))&1)==((v>>(b-2-j))&1)for j in range(b-1)))and(data[5]==1 or v.bit_count()==h)]
   local_count=len(table);total=local_count**(n//b);assert w==(total-1).bit_length()
   rank_oracle=0;lookup={v:i for i,v in enumerate(table)};source=inp.read_bytes()
   for pos in range(0,n,b):
    value=0
    for byte in source[pos:pos+b]:value=2*value+(byte==data[15])
    rank_oracle=rank_oracle*local_count+lookup[value]
   assert rank_oracle==int.from_bytes(data[20:-4],'big')
  modes[mode]=dict(status='verified',bytes=len(data),framing_and_model_bytes=24,rank_or_literal_bytes=len(data)-24,rank_bits=w,block_width=b,equality_mask=mask,count=h,local_cardinality=local_count,independent_rank_oracle=rank_oracle is not None,archive_sha256=sha(arc),restored_sha256=sha(rest),encode=enc,decode=dec)
 # Direct learned dictionary: established exact combinadic/mixed-radix control.
 arc=WORK/'archives'/f'{name}-rdic.archive';rest=WORK/'archives'/f'{name}-rdic.restored';rdic=WORK/'build/rdic'
 enc=call([rdic,'encode',inp,arc],name+'-rdic-encode')
 assert enc['exit']==0,enc
 dec=call([rdic,'decode',arc,rest],name+'-rdic-decode');assert dec['exit']==0 and sha(rest)==fixture['sha256']
 data=arc.read_bytes();assert int.from_bytes(data[-4:],'little')==zlib.crc32(data[:-4]);dictionary_bits=sequence_bits=0
 if data[5]==1:
  b=data[10];m=int.from_bytes(data[11:13],'little');source=inp.read_bytes();words=[]
  for pos in range(0,len(source),b):
   v=0
   for byte in source[pos:pos+b]:v=2*v+(byte==data[14])
   words.append(v)
  dictionary=sorted(set(words));assert len(dictionary)==m
  dictionary_rank=sum(math.comb(v,i+1) if v>=i+1 else 0 for i,v in enumerate(dictionary));dictionary_bits=(math.comb(1<<b,m)-1).bit_length();db=(dictionary_bits+7)//8
  assert dictionary_rank==int.from_bytes(data[15:15+db],'big')
  sequence_rank=0;lookup={v:i for i,v in enumerate(dictionary)}
  for v in words:sequence_rank=sequence_rank*m+lookup[v]
  sequence_bits=(m**len(words)-1).bit_length();assert sequence_rank==int.from_bytes(data[15+db:-4],'big')
 references['record_dictionary']=dict(status='verified',bytes=len(data),framing_and_model_header_bytes=19,dictionary_rank_bits=dictionary_bits,sequence_rank_bits=sequence_bits,block_width=data[10],independent_rank_oracle=data[5]==1,archive_sha256=sha(arc),restored_sha256=sha(rest),encode=enc,decode=dec)
 for label,enc_args,dec_args in [
  ('zstd19',['/bin/zstd','-19','-T1','-q','-c',inp],['/bin/zstd','-d','-q','-c']),
  ('xz9e',['/bin/xz','-9e','--threads=1','-c',inp],['/bin/xz','-d','-c']),
  ('bzip2_9',['/bin/bzip2','-9','-c',inp],['/bin/bzip2','-d','-c']),
  ('gzip9',['/bin/gzip','-n','-9','-c',inp],['/bin/gzip','-d','-c']),
  ('cix_best',[CIX,'--best','--threads','1','--memory','1536MiB','-c',inp],[CIX,'-d','-c']),
 ]:
  arc=WORK/'archives'/f'{name}-{label}.archive';rest=WORK/'archives'/f'{name}-{label}.restored'
  enc=call(enc_args,name+'-'+label+'-encode',arc)
  if enc['exit']!=0:references[label]=dict(status='unqualified',encode=enc);continue
  dec=call([*dec_args,arc],name+'-'+label+'-decode',rest);assert dec['exit']==0 and sha(rest)==fixture['sha256']
  references[label]=dict(status='verified',bytes=arc.stat().st_size,archive_sha256=sha(arc),restored_sha256=sha(rest),encode=enc,decode=dec)
 qualified=[(k,v['bytes'])for k,v in references.items()if v['status']=='verified'];best=min(qualified,key=lambda x:x[1]);ec=modes.get('ec',{})
 result=dict(fixture=fixture,modes=modes,references=references,L0_method=best[0],L0=best[1],conventional_L0=min(v['bytes'] for k,v in references.items() if k!='record_dictionary' and v['status']=='verified'),reference_gaps=[k for k,v in references.items()if v['status']!='verified'])
 if ec.get('status')=='verified' and all(modes[k].get('status')=='verified' for k in ['e','c']):
  le=modes['e']['bytes'];lc=modes['c']['bytes'];lec=ec['bytes'];result.update(LE=le,LC=lc,LEC=lec,Ginteraction=min(le,lc)-lec,paid_superadditivity=le+lc-lec-best[1],Delta=best[1]-lec,emergent=le>=best[1] and lc>=best[1] and lec<best[1])
 rows.append(result);(AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:result[k]for k in ['L0_method','L0','LE','LC','LEC','Delta','emergent']if k in result}),flush=True)
print('completed',len(rows),flush=True)

# Corrupt physical and CRC-valid semantic controls; no partial restoration.
sample=(WORK/'archives/dev-six-ec.erc').read_bytes();bad=[]
mutations=[('truncation',sample[:-1]),('corrupt_crc',sample[:-1]+bytes([sample[-1]^1]))]
for name,offset,value in [('invalid_width',10,b'\0'),('invalid_mask',11,b'\0\x80'),('invalid_mode',5,b'\xff'),('huge_rank_width',16,(2**31).to_bytes(4,'little'))]:
 d=bytearray(sample);d[offset:offset+len(value)]=value;d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');mutations.append((name,bytes(d)))
for name,data in mutations:
 arc=WORK/'archives'/('bad-'+name+'.erc');out=WORK/'archives'/('bad-'+name+'.out');arc.write_bytes(data);run=call([BIN,'decode',arc,out],'bad-'+name);assert run['exit'] not in (0,'timeout') and not out.exists();bad.append(dict(case=name,run=run))
(AREA/'malformed.json').write_text(json.dumps(bad,indent=2)+'\n')
