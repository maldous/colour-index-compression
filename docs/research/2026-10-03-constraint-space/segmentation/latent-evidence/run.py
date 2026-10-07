"""Root-only finite frozen search cells; fresh native archive-only decodes."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,time,zlib,itertools,ctypes
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/latent-evidence';WORK=ROOT/'benchmark-work/latent-layout';RAW=AREA/'raw';ARC=WORK/'archives';BIN=WORK/'build/layout';CIX=ROOT/'benchmark-work/release-d3a2/final/cix'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(AREA/n).write_text(json.dumps(v,indent=2)+'\n')
def call(args,tag,out=None,allowed=False):
 (RAW/(tag+'.command.json')).write_text(json.dumps(list(map(str,args)))+'\n')
 with (RAW/(tag+'.stderr')).open('wb')as err,(RAW/(tag+'.stdout')).open('wb')as txt:
  dest=Path(out).open('wb')if out else txt
  try:
   start=time.monotonic();cp=subprocess.run(['/usr/bin/time','-v','-o',str(RAW/(tag+'.time')),*map(str,args)],stdout=dest,stderr=err,timeout=120)
  finally:
   if out:dest.close()
 if not allowed:assert cp.returncode==0,(tag,(RAW/(tag+'.stderr')).read_text())
 return dict(exit=cp.returncode,wall_seconds=time.monotonic()-start)
def qualified(inp,name,enc,dec,stdout=False):
 tag=inp.stem+'-'+name;a=ARC/(tag+'.arc');o=ARC/(tag+'.restored');assert not a.exists()
 en=call(enc(a),tag+'-encode',a if stdout else None);de=call(dec(a,o),tag+'-decode',o if stdout else None);assert sha(o)==sha(inp)
 q=dict(bytes=a.stat().st_size,archive=str(a),archive_sha256=sha(a),restored_sha256=sha(o),encode=en,decode=de)
 if not stdout:
  q['trace']=json.loads((RAW/(tag+'-encode.stdout')).read_text());assert q['trace']['archive_bytes']==q['bytes'];q['accounting']=accounting(a,inp.read_bytes())
 return q

def accounting(a,x):
 b=Path(a).read_bytes();assert b[:5]==b'LLT1\x01';kind=b[5];n,crc=struct.unpack_from('<II',b,6);w,p,k,pl=b[14:18];assert n==len(x)and crc==zlib.crc32(x)and pl==p;off=18+p;payload=0;met=18+p;lanes=[]
 if n==0:assert kind==0 and(w,p,k,pl)==(1,0,0,0)and len(b)==18;return dict(header_bytes=18,metadata_bytes=18,payload_bytes=0,complete_bytes=18)
 if kind==1:
  ops=list(b[off:off+w]);off+=w;ln=struct.unpack_from('<I',b,off)[0];off+=4;assert off+ln==len(b);payload=ln;met=off;lanes=[dict(operators=ops,route='global-zstd',payload_bytes=ln)]
 else:
  assert kind==0
  for j in range(k):
   op,r,d,ln=struct.unpack_from('<BBII',b,off);off+=10;assert d==(n-p-j+w-1)//w and off+ln<=len(b);lanes.append(dict(offset=p+j,stride=w,op=op,route=r,decoded_bytes=d,metadata_bytes=10,payload_bytes=ln));off+=ln;payload+=ln;met+=10
  assert off==len(b)
 assert met+payload==len(b);return dict(header_bytes=18,raw_prefix_bytes=p,metadata_bytes=met,payload_bytes=payload,complete_bytes=len(b),lanes=lanes)

# Independent finite global-Zstd oracle: enumerates geometry/operator vectors,
# calls the same native entropy library directly, and computes physical LLT cost.
z=ctypes.CDLL('/lib/x86_64-linux-gnu/libzstd.so.1');z.ZSTD_compressBound.argtypes=[ctypes.c_size_t];z.ZSTD_compressBound.restype=ctypes.c_size_t;z.ZSTD_compress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];z.ZSTD_compress.restype=ctypes.c_size_t;z.ZSTD_isError.argtypes=[ctypes.c_size_t];z.ZSTD_isError.restype=ctypes.c_uint

def global_oracle(x):
 if not x:return dict(best_complete=18,evaluated=0)
 best=10**9;count=0
 for w in range(1,min(3,len(x))+1):
  for p in range(w):
   if w>len(x)-p:continue
   for ops in itertools.product([0,1,4],*([range(5)]*(w-1))):
    out=bytearray()
    for j,op in enumerate(ops):
     for row,i in enumerate(range(p+j,len(x),w)):
      if row==0 or op==0:v=x[i]
      elif op==1:v=(x[i]-x[i-w])%256
      elif op==2:v=(x[i]-x[i-1])%256
      elif op==3:v=x[i]^x[i-1]
      else:v=x[i]^x[i-w]
      out.append(v)
    cap=z.ZSTD_compressBound(len(out));dst=ctypes.create_string_buffer(cap);src=ctypes.create_string_buffer(bytes(out));ln=z.ZSTD_compress(dst,cap,src,len(out),19);assert not z.ZSTD_isError(ln);cost=18+p+w+4+ln;best=min(best,cost);count+=1
 return dict(best_complete=best,evaluated=count)

if __name__=='__main__':
 assert os.environ.get('CIX_LATENT_LEASE')=='1';ARC.mkdir(parents=True,exist_ok=True);rows=[]
 for f in json.loads((AREA/'input-freeze.json').read_text()):
  inp=Path(f['input']);assert sha(inp)==f['input_sha256'];c={};refs={}
  for pol in ['whole','bss','uniform','mask-control','auto']:
   c[pol]=qualified(inp,pol,lambda a,pol=pol:[BIN,'encode','--policy',pol,inp,a],lambda a,o:[BIN,'decode',a,o])
  assert c['auto']['bytes']<=c['whole']['bytes']and c['auto']['bytes']<=c['bss']['bytes']
  oracle=None
  if f['split']=='tiny':
   c['oracle']=qualified(inp,'oracle',lambda a:[BIN,'encode','--policy','oracle',inp,a],lambda a,o:[BIN,'decode',a,o]);g=global_oracle(inp.read_bytes());native_min=min([q['complete_bytes']for q in c['oracle'].get('trace',{}).get('candidates',[])if q['tag']in ('native-auto','raw-whole')]+[18]if len(inp.read_bytes())==0 else[q['complete_bytes']for q in c['oracle']['trace']['candidates']if q['tag']in ('native-auto','raw-whole')]);exact=min(g['best_complete'],native_min);assert c['oracle']['bytes']==exact;assert c['auto']['bytes']>=exact;oracle=dict(independent_global=g,exact_family_bytes=exact,selector_regret=c['auto']['bytes']-exact)
  if f['split']=='held-out':
   for name,en,de in [('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c']),('cix_best',[CIX,'--best','--threads','1','--memory','1536MiB','-c'],[CIX,'-d','-c'])]:
    refs[name]=qualified(inp,name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],True)
  elif f['split']=='exposed-attribution':
   for k,q in f['diagnostic']['existing_controls'].items():
    if k=='matched_zstd_v1':continue
    assert sha(q['archive'])==q['archive_sha256'];refs[k]=dict(q,reused=True)
  rows.append(dict(fixture=f,candidates=c,references=refs,oracle=oracle));save('results.json',rows);print(f['name'],{k:q['bytes']for k,q in c.items()}, {k:q['bytes']for k,q in refs.items()}, 'regret',None if oracle is None else oracle['selector_regret'],flush=True)
 # Bounds/semantic corruption tests are archive-only fresh native invocations.
 seed=next(Path(r['candidates']['auto']['archive'])for r in rows if r['fixture']['input_bytes']>12);b=seed.read_bytes();bad={'truncated':b[:-1],'trailing':b+b'\0'}
 for name,off,width,val in [('magic',0,1,0),('version',4,1,2),('kind',5,1,255),('source_bound',6,4,4097),('width_zero',14,1,0),('width_high',14,1,9),('phase_high',15,1,255),('count_high',16,1,255),('prefix_mismatch',17,1,8),('CRC',10,4,0)]:
  q=bytearray(b);q[off:off+width]=val.to_bytes(width,'little');bad[name]=bytes(q)
 q=bytearray(b);q[6:10]=(1).to_bytes(4,'little');q[14:18]=bytes([8,7,8,7]);bad['phase_exceeds_source']=bytes(q)
 q=bytearray(b);pos=18+q[15];q[pos]=255;bad['operator_id']=bytes(q)
 zb=next(Path(r['candidates']['bss']['archive']).read_bytes() for r in rows if r['fixture']['input_bytes']>12 and Path(r['candidates']['bss']['archive']).read_bytes()[5]==1)
 if zb[5]==1:
  q=bytearray(zb);pos=18+q[15]+q[14];q[pos:pos+4]=(32768).to_bytes(4,'little');bad['frame_length']=bytes(q)
  q=bytearray(zb);pos=18+q[15]+q[14];ln=struct.unpack_from('<I',q,pos)[0];q[pos:pos+4]=(ln+1).to_bytes(4,'little');q.append(0);bad['zstd_trailing_frame']=bytes(q)
 header=b'LLT1\1\0'+struct.pack('<II',1,0)+bytes([1,0,1,0]);payload=bytearray(19);payload[0]=1;payload[3:11]=(1<<40).to_bytes(8,'little');bad['Huffman_length']=header+struct.pack('<BBII',0,1,1,19)+payload
 frame=bytes.fromhex('28b52ffd8088')+struct.pack('<I',1)+bytes.fromhex('09000000')
 bad['zstd_declared_window']=b'LLT1\1\1'+struct.pack('<II',1,zlib.crc32(b'\0'))+bytes([1,0,1,0,0])+struct.pack('<I',len(frame))+frame
 bad['unknown_route']=header+struct.pack('<BBII',0,255,1,1)+b'\0'
 bad['noncanonical_empty']=b'LLT1\1\0'+struct.pack('<II',0,0)+bytes([2,0,0,0])
 checks=[]
 for name,data in bad.items():
  a=ARC/('bad-'+name+'.arc');o=ARC/('bad-'+name+'.out');a.write_bytes(data);r=call([BIN,'decode',a,o],'bad-'+name,allowed=True);assert r['exit']==1 and not o.exists(),(name,r);
  if name=='zstd_declared_window':assert 'zstd frame bounds' in(RAW/('bad-'+name+'.stderr')).read_text()
  checks.append(dict(name=name,run=r))
 # All supported small geometries/operator combinations restore via raw lanes.
 mechanisms=[]
 for n in range(1,9):
  x=bytes((i*61+i*i*7+13)&255 for i in range(n))
  for w in range(1,min(3,n)+1):
   for phase in range(w):
    if w>n-phase:continue
    for ops in itertools.product([0,1,4],*([range(5)]*(w-1))):
     a=bytearray(b'LLT1\1\0'+struct.pack('<II',n,zlib.crc32(x))+bytes([w,phase,w,phase])+x[:phase])
     for j,op in enumerate(ops):
      v=bytearray()
      for row,i in enumerate(range(phase+j,n,w)):
       if row==0 or op==0:t=x[i]
       elif op==1:t=(x[i]-x[i-w])%256
       elif op==2:t=(x[i]-x[i-1])%256
       elif op==3:t=x[i]^x[i-1]
       else:t=x[i]^x[i-w]
       v.append(t)
      a.extend(struct.pack('<BBII',op,0,len(v),len(v)));a.extend(v)
     tag=f'mechanism-{n}-{w}-{phase}-'+''.join(map(str,ops));ap=ARC/(tag+'.arc');opth=ARC/(tag+'.restored');ap.write_bytes(a)
     cp=subprocess.run([str(BIN),'decode',str(ap),str(opth)],capture_output=True,timeout=5);assert cp.returncode==0 and opth.read_bytes()==x,(tag,cp.stderr)
     mechanisms.append(dict(name=tag,bytes=len(a),archive_sha256=sha(ap),restored_sha256=sha(opth),exit=cp.returncode))
 save('mechanism-inverses.json',mechanisms)
 print('Mechanism exact fresh raw inverses',len(mechanisms),flush=True)
 save('malformed.json',checks);save('artifact-binding.json' ,dict(artifacts={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in WORK.rglob('*')if p.is_file()}))
