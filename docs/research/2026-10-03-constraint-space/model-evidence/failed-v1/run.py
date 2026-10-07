from pathlib import Path
import hashlib,json,subprocess,time,os,zlib,math
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/model-evidence';WORK=ROOT/'benchmark-work/model-descriptions';BIN=WORK/'build/models';CTRL=WORK/'build/mdc';CIX=ROOT/'benchmark-work/release-d3a2/final/cix'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args,label,output=None,limit=10):
 t=time.monotonic()
 with (Path(output)if output else AREA/'raw'/f'{label}.stdout').open('wb')as out,(AREA/'raw'/f'{label}.stderr').open('wb')as err:
  try:p=subprocess.run(['/usr/bin/time','-v','-o',str(AREA/'raw'/f'{label}.time'),*map(str,args)],stdout=out,stderr=err,timeout=limit,env={**os.environ,'LD_LIBRARY_PATH':str(CIX.parent)});code=p.returncode
  except subprocess.TimeoutExpired:code='timeout'
 return dict(args=list(map(str,args)),exit=code,wall_seconds=time.monotonic()-t)
def model_table(arc):
 b=arc[10];kind=arc[5];ml=int.from_bytes(arc[13:15],'little');data=arc[15:15+ml];u=1<<b
 if kind==1:
  m=int.from_bytes(data[:2],'little');rank=int.from_bytes(data[2:],'big');out=[];upper=u
  for i in range(m,0,-1):
   v=upper-1
   while math.comb(v,i)>rank:v-=1
   rank-=math.comb(v,i);out.append(v);upper=v
  assert rank==0;return sorted(out)
 if kind==2:return[v for v in range(u)if data[v//8]>>(v%8)&1]
 if kind==3:
  n=int.from_bytes(data[:2],'little');out=[]
  for i in range(n):start=int.from_bytes(data[2+i*4:4+i*4],'little');length=int.from_bytes(data[4+i*4:6+i*4],'little');out.extend(range(start,start+length))
  return out
 if kind==7:
  n=int.from_bytes(data[:2],'little');root=int.from_bytes(data[2:4],'little');nodes=[tuple([data[4+5*i],int.from_bytes(data[5+5*i:7+5*i],'little'),int.from_bytes(data[7+5*i:9+5*i],'little')])for i in range(n)];out=[]
  for v in range(u):
   node=root
   while node>=2:j,lo,hi=nodes[node-2];node=hi if v>>(b-1-j)&1 else lo
   if node==1:out.append(v)
  return out
 if kind==4:atoms=[(data[1+4*i],int.from_bytes(data[2+4*i:4+4*i],'little'),data[4+4*i])for i in range(data[0])]
 elif kind==5:atoms=[(data[1+3*i]>>4,int.from_bytes(data[2+3*i:4+3*i],'little'),data[1+3*i]&15)for i in range(data[0])]
 elif kind==6:
  s=data[0];masks=[int.from_bytes(data[1+2*i:3+2*i],'little')for i in range(s)];at=1+2*s;atoms=[(data[at+1+2*i]>>6,masks[data[at+1+2*i]&63],data[at+2+2*i])for i in range(data[at])]
 else:raise AssertionError(kind)
 from fixtures import holds
 return[v for v in range(u)if all(holds(v,a)for a in atoms)]
rows=[]
for fixture in json.loads((AREA/'input-freeze.json').read_text()):
 name=fixture['name'];inp=Path(fixture['input']);model=Path(fixture['model']);assert sha(inp)==fixture['input_sha256']and sha(model)==fixture['model_sha256'];candidates={};controls={};print('model comparison',name,flush=True)
 for kind in ['raw','subset','bitset','rle','bdd','flat','packed-flat','shared','auto']:
  arc=WORK/'archives'/f'{name}-{kind}.msl';rest=WORK/'archives'/f'{name}-{kind}.restored';enc=call([BIN,'encode',kind,model,inp,arc],name+'-'+kind+'-encode')
  if enc['exit']!=0:
   # Structural applicability, not unexpected failure: fallback controls have fewer/morethan2symbols.
   assert name in ['empty','mono','absent']and kind not in ['raw','auto'] and enc['exit']not in ['timeout',-11,-6] and 'input does not have two observed symbols' in (AREA/'raw'/f'{name}-{kind}-encode.stderr').read_text();candidates[kind]=dict(status='explicitly_inapplicable',encode=enc);continue
  dec=call([BIN,'decode',arc,rest],name+'-'+kind+'-decode');assert dec['exit']==0 and sha(rest)==fixture['input_sha256']
  data=arc.read_bytes();assert data[:4]==b'MSL1'and data[4]==1 and zlib.crc32(data[:-4])==int.from_bytes(data[-4:],'little');m=int.from_bytes(data[13:15],'little');stats=json.loads((AREA/'raw'/f'{name}-{kind}-encode.stdout').read_text())
  if data[5]!=0:
   table=model_table(data);assert table==fixture['exact_members'];count=len(table)**(fixture['input_bytes']//fixture['b']);bits=(count-1).bit_length();assert stats['rank_bits']==bits
   rank=0;lookup={v:i for i,v in enumerate(table)};src=inp.read_bytes()
   for pos in range(0,len(src),fixture['b']):
    v=0
    for byte in src[pos:pos+fixture['b']]:v=2*v+(byte==data[12])
    rank=rank*len(table)+lookup[v]
   assert rank==int.from_bytes(data[15+m:-4],'big')
  else:assert data[15:-4]==inp.read_bytes()
  assert len(data)==19+m+(fixture['input_bytes']if data[5]==0 else stats['rank_bytes']);candidates[kind]=dict(status='verified',bytes=len(data),model_bytes=m,stats=stats,encode=enc,decode=dec,decode_kernels=json.loads((AREA/'raw'/f'{name}-{kind}-decode.stderr').read_text()),archive_sha256=sha(arc),restored_sha256=sha(rest))
 # Separate generic input-derived discovery; no prescribed model is passed.
 arc=WORK/'archives'/f'{name}-discover.msl';rest=WORK/'archives'/f'{name}-discover.restored';enc=call([BIN,'discover',inp,arc],name+'-discover-encode',limit=30);assert enc['exit']==0
 dec=call([BIN,'decode',arc,rest],name+'-discover-decode');assert dec['exit']==0 and sha(rest)==fixture['input_sha256'];data=arc.read_bytes();stats=json.loads((AREA/'raw'/f'{name}-discover-encode.stdout').read_text());discovery_same_space=None
 assert data[:4]==b'MSL1'and data[4]==1 and zlib.crc32(data[:-4])==int.from_bytes(data[-4:],'little');assert stats['selectedb']==data[10]
 assert stats['candidatecount']==(1+7*sum(fixture['input_bytes']%b==0 for b in range(2,13))if len(set(inp.read_bytes()))==2 else 1)
 assert len(data)==19+int.from_bytes(data[13:15],'little')+(fixture['input_bytes']if data[5]==0 else stats['rank_bytes'])
 if data[5]!=0:
  observed_table=model_table(data)
  from fixtures import holds
  assert observed_table==[v for v in range(1<<data[10])if all(holds(v,a)for a in stats['selectedatoms'])]
  discovery_same_space=data[10]==fixture['b']and observed_table==fixture['exact_members']
  source=inp.read_bytes();b=data[10];rank=0;lookup={v:i for i,v in enumerate(observed_table)}
  for pos in range(0,len(source),b):
   v=0
   for byte in source[pos:pos+b]:v=2*v+(byte==data[12])
   rank=rank*len(observed_table)+lookup[v]
  ml=int.from_bytes(data[13:15],'little');assert rank==int.from_bytes(data[15+ml:-4],'big')
 discovery=dict(status='verified',bytes=len(data),stats=stats,same_prescribed_space=discovery_same_space,encode=enc,decode=dec,archive_sha256=sha(arc),restored_sha256=sha(rest))
 # Metadata-only established controls: actual wrapper, native extract/unpack, standardnativebackend, freshnativeMSLdecode.
 for basekind in ['flat','shared','bdd']:
  if candidates.get(basekind,{}).get('status')!='verified':continue
  base=WORK/'archives'/f'{name}-{basekind}.msl';rawmodel=WORK/'archives'/f'{name}-{basekind}.model';assert call([CTRL,'model',base,rawmodel],name+'-'+basekind+'-extractmodel')['exit']==0
  for codec,compress,decompress in [('zstd',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('bzip2',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c'])]:
   label=name+'-'+basekind+'-'+codec;comp=WORK/'archives'/(label+'.comp');wrapped=WORK/'archives'/(label+'.mdc');extracted=WORK/'archives'/(label+'.extracted');restmodel=WORK/'archives'/(label+'.restmodel');inner=WORK/'archives'/(label+'.inner');out=WORK/'archives'/(label+'.restored')
   enc=call([*compress,rawmodel],label+'-compress',comp);assert enc['exit']==0
   assert call([CTRL,'pack',codec,base,comp,wrapped],label+'-pack')['exit']==0
   assert call([CTRL,'extract',wrapped,extracted],label+'-extract')['exit']==0 and sha(extracted)==sha(comp)
   dec=call([*decompress,extracted],label+'-decompress',restmodel);assert dec['exit']==0 and sha(restmodel)==sha(rawmodel)
   assert call([CTRL,'unpack',wrapped,restmodel,inner],label+'-unpack')['exit']==0 and sha(inner)==sha(base)
   verify=call([BIN,'decode',inner,out],label+'-decode');assert verify['exit']==0 and sha(out)==fixture['input_sha256']
   assert wrapped.stat().st_size==31+comp.stat().st_size+candidates[basekind]['stats']['rank_bytes']
   controls[basekind+'-'+codec]=dict(status='verified',bytes=wrapped.stat().st_size,compressed_model_bytes=comp.stat().st_size,compression=enc,decompression=dec,archive_sha256=sha(wrapped),restored_sha256=sha(out))
 refs={}
 if 'existing_references'in fixture:refs=fixture['existing_references']
 elif fixture['split']!='control':
  for label,encargs,decargs in [('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','--threads=1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c']),('cix_best',[CIX,'--best','--threads','1','--memory','1536MiB','-c'],[CIX,'-d','-c'])]:
   arc=WORK/'archives'/f'{name}-{label}.control';out=WORK/'archives'/f'{name}-{label}.control-restored';enc=call([*encargs,inp],name+'-'+label+'-encode',arc,120)
   if enc['exit']!=0:refs[label]=dict(status='unqualified',encode=enc);continue
   dec=call([*decargs,arc],name+'-'+label+'-decode',out,120);assert dec['exit']==0 and sha(out)==fixture['input_sha256'];refs[label]=dict(status='verified',bytes=arc.stat().st_size,encode=enc,decode=dec,archive_sha256=sha(arc),restored_sha256=sha(out))
 verified=[(k,v['bytes'])for k,v in candidates.items()if v['status']=='verified'];best=min(verified,key=lambda x:x[1]);assert candidates['auto']['bytes']==best[1]
 row=dict(fixture=fixture,candidates=candidates,discovery=discovery,metadata_controls=controls,strong_references=refs,best=best)
 if candidates.get('shared',{}).get('status')=='verified':row.update(shared_vs_flat_model_bytes=candidates['flat']['model_bytes']-candidates['shared']['model_bytes'],shared_vs_packed_model_bytes=candidates['packed-flat']['model_bytes']-candidates['shared']['model_bytes'])
 rows.append(row);(AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(name,'selected',candidates['auto']['stats']['format'],best[1],'sharedvsflat',row.get('shared_vs_flat_model_bytes'),'sharedvspacked',row.get('shared_vs_packed_model_bytes'),flush=True)
# Parser corruption: basic framing and correctly resealed semantic metadata.
base=(WORK/'archives/upper-parity-dev-flat.msl').read_bytes();tests=[('truncated',base[:-1]),('crc',base[:-1]+bytes([base[-1]^1]))]
for label,offset,value in [('kind',5,b'\xfe'),('model_length',13,b'\xff\xff'),('count',15,b'\xff'),('mask',17,b'\0\0')]:
 d=bytearray(base);d[offset:offset+len(value)]=value;d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');tests.append((label,bytes(d)))
# Resealed cyclic BDD child in the first node (node2 cannot point to itself).
d=bytearray((WORK/'archives/upper-parity-dev-bdd.msl').read_bytes());d[20:22]=(2).to_bytes(2,'little');d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');tests.append(('bdd_cycle',bytes(d)))
# Explicit canonical b2 bitset padding regression from independent small fixture.
smallmodel=WORK/'inputs/bitset-two.model';smallinput=WORK/'inputs/bitset-two.input';smallarc=WORK/'archives/bitset-two.msl';smallmodel.write_text('2\n');smallinput.write_bytes(bytes([17,230,17,230]))
assert call([BIN,'encode','bitset',smallmodel,smallinput,smallarc],'bitset-two-encode')['exit']==0
d=bytearray(smallarc.read_bytes());d[15]|=0x10;d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');tests.append(('bitset_high_padding',bytes(d)))
d=bytearray((WORK/'archives/upper-parity-dev-shared.msl').read_bytes());first=15+1+2*d[15]+1;d[first]=(d[first]&192)|63;d[-4:]=zlib.crc32(d[:-4]).to_bytes(4,'little');tests.append(('shared_invalid_reference',bytes(d)))
checks=[]
for label,data in tests:
 arc=WORK/'archives'/f'bad-{label}.msl';out=WORK/'archives'/f'bad-{label}.out';assert not out.exists();arc.write_bytes(data);run=call([BIN,'decode',arc,out],'bad-'+label);assert run['exit']not in [0,'timeout']and not out.exists();checks.append(dict(case=label,run=run))
(AREA/'malformed.json').write_text(json.dumps(checks,indent=2)+'\n')
(AREA/'artifact-binding.json').write_text(json.dumps({'artifacts':{str(p.resolve()):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted((WORK/'archives').iterdir())},'binaries':{str(p.resolve()):sha(p)for p in sorted((WORK/'build').iterdir())}},indent=2)+'\n')
print('qualified',len(rows),'frozen model rows',flush=True)
