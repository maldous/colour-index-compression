from pathlib import Path
import hashlib,json,subprocess,zlib,math,time
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/normalised-evidence';OLD=ROOT/'docs/research/2026-10-03-constraint-space/record-evidence';WORK=ROOT/'benchmark-work/constraint-normalised';RNC=WORK/'build/rnc';PREVIOUS=ROOT/'benchmark-work/equality-records'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def call(args,label):
 t=time.monotonic()
 with (AREA/'raw'/f'{label}.stdout').open('wb')as out,(AREA/'raw'/f'{label}.stderr').open('wb')as err:
  p=subprocess.run(['/usr/bin/time','-v','-o',str(AREA/'raw'/f'{label}.time'),*map(str,args)],stdout=out,stderr=err,timeout=10)
 return dict(args=list(map(str,args)),exit=p.returncode,wall_seconds=time.monotonic()-t)
freeze=json.loads((AREA/'freeze.json').read_text())
for path,digest in freeze['hashes'].items():assert sha(ROOT/path)==digest
binding=json.loads((OLD/'artifact-binding.json').read_text());rows=[]
for old in json.loads((OLD/'results.json').read_text()):
 name=old['fixture']['name'];models={}
 for key,original in [(k,PREVIOUS/'archives'/f'{name}-{k}.erc')for k,v in old['modes'].items()if v['status']=='verified']+ [('dictionary',PREVIOUS/'archives'/f'{name}-rdic.archive')]:
  assert sha(original)==binding['artifacts'][str(original)]['sha256']
  codec='rdic'if key=='dictionary'else'erc';frame=WORK/'archives'/f'{name}-{key}.rnc';inner=WORK/'archives'/f'{name}-{key}.inner';rest=WORK/'archives'/f'{name}-{key}.restored'
  pack=call([RNC,'pack',codec,original,frame],name+'-'+key+'-pack');assert pack['exit']==0
  unpack=call([RNC,'unpack',frame,inner],name+'-'+key+'-unpack');assert unpack['exit']==0 and sha(inner)==sha(original)
  decode=call([PREVIOUS/'build'/codec,'decode',inner,rest],name+'-'+key+'-decode');assert decode['exit']==0 and sha(rest)==old['fixture']['sha256']
  data=frame.read_bytes();assert data[:4]==b'RNC1'and data[4]==1 and zlib.crc32(data[:-4])==int.from_bytes(data[-4:],'little')
  payload=int.from_bytes(data[6:10],'little');assert len(data)==270+payload
  src=original.read_bytes();dictionary_rank_bits=0
  if codec=='erc':model_len=20;rank_bits=int.from_bytes(src[16:20],'little')
  elif src[5]==0:model_len=15;rank_bits=8*old['fixture']['bytes']
  else:
   b=src[10];m=int.from_bytes(src[11:13],'little');dictionary_rank_bits=(math.comb(1<<b,m)-1).bit_length();model_len=15+(dictionary_rank_bits+7)//8;rank_bits=(m**(old['fixture']['bytes']//b)-1).bit_length()
  assert data[10:10+model_len]==src[:model_len] and not any(data[10+model_len:266])
  assert data[266:-4]==src[model_len:-4] and payload==(rank_bits+7)//8
  models[key]=dict(bytes=len(data),model_area_bytes=256,outer_framing_bytes=14,used_model_bytes=model_len,payload_bytes=payload,exact_rank_or_literal_bits=rank_bits,dictionary_rank_bits_in_model=dictionary_rank_bits,frame_sha256=sha(frame),inner_sha256=sha(inner),restored_sha256=sha(rest),pack=pack,unpack=unpack,decode=decode)
 # Paid two-symbol unconstrained universe, generated natively without constraints.
 if old['fixture']['bytes'] and len(set(Path(old['fixture']['path']).read_bytes()))==2:
  frame=WORK/'archives'/f'{name}-uniform.rnc';inner=WORK/'archives'/f'{name}-uniform.inner';rest=WORK/'archives'/f'{name}-uniform.restored'
  pack=call([RNC,'uniform',old['fixture']['path'],frame],name+'-uniform-pack');assert pack['exit']==0
  unpack=call([RNC,'unpack',frame,inner],name+'-uniform-unpack');assert unpack['exit']==0
  decode=call([PREVIOUS/'build/erc','decode',inner,rest],name+'-uniform-decode');assert decode['exit']==0 and sha(rest)==old['fixture']['sha256']
  data=frame.read_bytes();payload=(old['fixture']['bytes']+7)//8;assert len(data)==270+payload
  source=Path(old['fixture']['path']).read_bytes();alphabet=sorted(set(source));rank=0
  for byte in source:rank=2*rank+(byte==alphabet[1])
  assert rank==int.from_bytes(data[266:-4],'big')
  models['uniform']=dict(bytes=len(data),model_area_bytes=256,outer_framing_bytes=14,used_model_bytes=20,payload_bytes=payload,exact_rank_or_literal_bits=len(source),independent_rank_oracle=True,frame_sha256=sha(frame),inner_sha256=sha(inner),restored_sha256=sha(rest),pack=pack,unpack=unpack,decode=decode)
 row=dict(fixture=old['fixture'],models=models,original_control_bytes=old['L0'],normalised_control='dictionary',normalised_L0=models['dictionary']['bytes'])
 if all(k in models for k in ['e','c','ec']):
  e=models['e'];c=models['c'];ec=models['ec'];d=models['dictionary']
  erc=(WORK/'archives'/f'{name}-ec.inner').read_bytes();rdic=(WORK/'archives'/f'{name}-dictionary.inner').read_bytes()
  assert erc[6:10]==rdic[6:10] and erc[10]==rdic[10] and erc[14:16]==rdic[13:15]
  b=erc[10];mask=int.from_bytes(erc[11:13],'little');h=erc[13]
  admissible=[v for v in range(1<<b) if v.bit_count()==h and all(not(mask>>j&1) or ((v>>(b-1-j))&1)==((v>>(b-2-j))&1)for j in range(b-1))]
  source=Path(old['fixture']['path']).read_bytes();observed=[]
  for pos in range(0,len(source),b):
   word=0
   for byte in source[pos:pos+b]:word=word*2+(byte==erc[15])
   observed.append(word)
  eheader=(WORK/'archives'/f'{name}-e.inner').read_bytes();cheader=(WORK/'archives'/f'{name}-c.inner').read_bytes()
  assert eheader[6:10]==erc[6:10] and cheader[6:10]==erc[6:10] and eheader[14:16]==erc[14:16] and cheader[14:16]==erc[14:16]
  be=eheader[10];bc=cheader[10];em=int.from_bytes(eheader[11:13],'little');ch=cheader[13]
  assert b%be==0 and b%bc==0 # exact aligned local factorisation, not an assumed cross-width pairing
  def eok(v):
   bits=[(v>>(b-1-j))&1 for j in range(b)]
   return all(not(em>>j&1) or bits[start+j]==bits[start+j+1] for start in range(0,b,be) for j in range(be-1))
  def cok(v):
   bits=[(v>>(b-1-j))&1 for j in range(b)]
   return all(sum(bits[start:start+bc])==ch for start in range(0,b,bc))
  etable=[v for v in range(1<<b) if eok(v)];ctable=[v for v in range(1<<b) if cok(v)]
  intersection=sorted(set(etable)&set(ctable));assert intersection==admissible
  r=old['fixture']['bytes']//b
  assert (len(etable)**r-1).bit_length()==e['exact_rank_or_literal_bits'] and (len(ctable)**r-1).bit_length()==c['exact_rank_or_literal_bits']
  row['exact_intersection_verified']=True
  row['local_cardinalities_in_common_block']=dict(uniform=1<<b,equality=len(etable),counts=len(ctable),intersection=len(intersection),block_width=b)
  assert admissible==sorted(set(observed))
  assert (WORK/'archives'/f'{name}-ec.rnc').read_bytes()[266:-4]==(WORK/'archives'/f'{name}-dictionary.rnc').read_bytes()[266:-4]
  row.update(rank_gain_bits=min(e['exact_rank_or_literal_bits'],c['exact_rank_or_literal_bits'])-ec['exact_rank_or_literal_bits'],interaction_bytes=min(e['bytes'],c['bytes'])-ec['bytes'],versus_normalised_direct_control=d['bytes']-ec['bytes'],same_rank_payload_as_dictionary=ec['payload_bytes']==d['payload_bytes'],rounded_state_space_surplus_bits=e['exact_rank_or_literal_bits']+c['exact_rank_or_literal_bits']-models['uniform']['exact_rank_or_literal_bits']-ec['exact_rank_or_literal_bits'],rounded_state_space_surplus_bytes=e['payload_bytes']+c['payload_bytes']-models['uniform']['payload_bytes']-ec['payload_bytes'])
 rows.append(row);(AREA/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({k:v for k,v in row.items()if k not in ['models','fixture']},sort_keys=True),flush=True)
# Physically invalid and resealed semantic outer frames.
sample=(WORK/'archives/dev-eight-ec.rnc').read_bytes();bad=[('truncation',sample[:-1]),('CRC',sample[:-1]+bytes([sample[-1]^1]))]
for label,offset,value in [('model_padding',30,b'\1'),('codec',5,b'\xff'),('payload_length',6,(2**31).to_bytes(4,'little'))]:
 data=bytearray(sample);data[offset:offset+len(value)]=value;data[-4:]=zlib.crc32(data[:-4]).to_bytes(4,'little');bad.append((label,bytes(data)))
checks=[]
for label,data in bad:
 frame=WORK/'archives'/f'bad-{label}.rnc';output=WORK/'archives'/f'bad-{label}.inner';assert not output.exists();frame.write_bytes(data)
 result=call([RNC,'unpack',frame,output],'bad-'+label);assert result['exit']!=0 and not output.exists();checks.append(dict(case=label,run=result))
(AREA/'malformed.json').write_text(json.dumps(checks,indent=2)+'\n')
artifacts={str(p.resolve()):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted((WORK/'archives').iterdir())}
(AREA/'artifact-binding.json').write_text(json.dumps({'binary':{'path':str(RNC),'sha256':sha(RNC)},'artifacts':artifacts,'successful_frames':sum(len(r['models'])for r in rows)},indent=2)+'\n')
print('qualified',sum(len(r['models'])for r in rows),'complete frames',flush=True)
