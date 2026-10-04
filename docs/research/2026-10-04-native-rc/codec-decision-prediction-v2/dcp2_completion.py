#!/usr/bin/env python3
"""One fixed xz wrapper around DCP1, with corrected stored-block offset inverse."""
import gzip, hashlib, json, lzma, runpy, struct, subprocess, sys, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
M=runpy.run_path(str(ROOT/'docs/research/2026-10-04-native-rc/codec-decision-prediction-v1/decision_prediction.py'),run_name='dcp1')
D=M['D']; parse,rebuild=M['parse'],M['rebuild']; raw_deflate,parse_raw=M['raw_deflate'],M['parse_raw']; token_map,token_len=M['token_map'],M['token_len']
unpack,pack=M['unpack'],M['pack']; VERSION=M['VERSION']

def restore_fixed(dcp1):
 x,plain,cor=unpack(dcp1);ref=parse_raw(raw_deflate(plain));rm=token_map(ref);off=0;ci=0
 for b in x['blocks']:
  if b['type']==0:
   off+=len(b['raw'])
   continue
  seq=cor[ci];ci+=1;tokens=[]
  for q in seq:
   tag=q[0]
   if tag==3:tokens.append((2,));continue
   if tag==0:
    if off not in rm:raise ValueError('missing predictor token')
    t=rm[off]
   elif tag==1:t=(0,plain[off])
   elif tag==2:t=(1,*q[1:])
   else:raise ValueError('bad correction tag')
   tokens.append(t);off+=token_len(t)
  if not tokens or tokens[-1]!=(2,):raise ValueError('missing EOB')
  b['tokens']=tokens
 g=rebuild(x)
 if len(g)!=x['origlen'] or gzip.decompress(g)!=plain:raise ValueError('DCP1 inverse mismatch')
 return g

def corrections_fixed(orig, ref):
 rm=token_map(ref);off=0;out=[]
 for b in orig['blocks']:
  if b['type']==0:
   off+=len(b['raw']);continue
  seq=[]
  for t in b['tokens']:
   if t[0]==2:seq.append((3,));continue
   if rm.get(off)==t:seq.append((0,))
   elif t[0]==0:seq.append((1,))
   else:seq.append((2,*t[1:]))
   off+=token_len(t)
  out.append(seq)
 return out

def mixed_validation():
 # Non-final stored block followed by final fixed-Huffman literals exercises the offset fix.
 bw=D['BitWriter']();put=D['putsym']; enc,_=D['huff'](D['FIX_LL']);a=b'stored-prefix:';z=b'compressed-suffix'
 bw.put(0,1);bw.put(0,2);bw.put(0,(-bw.p)%8);bw.raw(struct.pack('<HH',len(a),(~len(a))&0xffff));bw.raw(a)
 bw.put(1,1);bw.put(1,2)
 for q in z:put(bw,enc,q)
 put(bw,enc,256);bw.put(0,(-bw.p)%8)
 plain=a+z
 g=b'\x1f\x8b\x08\0'+b'\0'*6+bw.out()+struct.pack('<II',zlib.crc32(plain)&0xffffffff,len(plain)&0xffffffff);x=parse(g)
 if [b['type'] for b in x['blocks']] != [0,1]:raise AssertionError('mixed block construction')
 co=corrections_fixed(x,parse_raw(raw_deflate(plain)));dcp=pack(x,plain,co)
 if restore_fixed(dcp)!=g:raise AssertionError('mixed stored offset inverse')
 return {'block_types':[0,1],'gzip_bytes':len(g),'dcp1_bytes':len(dcp),'exact':True}

ITEMS=[
 ('artificial','cc1818a084d61fe693fe2a9db7312da25fdb4b54313502a6920abf692b7a47ab','b3f3bfd6dc006c97fd695b1a59f0c2b4606b2f32c529579b60ecbb65cd4c0c23'),
 ('canterbury','f140e8a5b73d3f53198555a63bfb827889394a42f20825df33c810c3d5e3f8fb','02522da7db7487fce7e9d7682da895dbd7580b2fcbd74690df31c3ea8395f5de'),
 ('calgary','e109eebdc19c5cee533c58bd6a49a4be3a77cc52f84ba234a089148a4f2093b7','42e3f33e345e1cebe0735e178b159a0b6fbea50be1dc561cd4ccc61eadf5d9c1')]

def inverse(path, expected):
 b=Path(path).read_bytes()
 if b[:4]!=b'DCP2':raise ValueError('bad DCP2 magic')
 g=restore_fixed(lzma.decompress(b[4:]))
 if hashlib.sha256(g).hexdigest()!=expected:raise ValueError('source SHA mismatch')

def main():
 out=ROOT/'benchmark-work/codec-decision-prediction-v2';out.mkdir(exist_ok=True);mixed=mixed_validation();rows=[]
 for n,origsha,dcp1sha in ITEMS:
  src=(ROOT/'benchmark-work'/(n+'.tar.gz')).read_bytes();p=ROOT/'benchmark-work/codec-decision-prediction-v1'/(n+'.decision_predictor_dcp1.bin');dcp1=p.read_bytes()
  if hashlib.sha256(src).hexdigest()!=origsha or hashlib.sha256(dcp1).hexdigest()!=dcp1sha:raise ValueError('frozen identity mismatch '+n)
  # Existing DCP1 parser confirms whether its already-executed correction offset bug was reachable.
  x,plain,cor=unpack(dcp1);types=[b['type'] for b in x['blocks']]
  if 0 in types:raise ValueError('v1 real input contains stored block; cannot rely on prior DCP1 encoding')
  if restore_fixed(dcp1)!=src:raise AssertionError('corrected DCP1 inverse '+n)
  dcp2=b'DCP2'+lzma.compress(dcp1,preset=1);q=out/(n+'.dcp2.bin');q.write_bytes(dcp2)
  z=subprocess.run([sys.executable,__file__,'--inverse',str(q),origsha],capture_output=True,text=True)
  if z.returncode:raise AssertionError('fresh DCP2 '+n+': '+z.stderr+z.stdout)
  controls={'original_gzip':len(src),'gzip_bytes_zlib9':len(b'GZB1'+zlib.compress(src,9)),'gzip_bytes_xz1':len(b'GXB1'+lzma.compress(src,preset=1)),'raw_dcp1':len(dcp1),'dcp2_xz1_complete':len(dcp2)}
  rows.append({'asset':n,'source_sha256':origsha,'dcp1_sha256':dcp1sha,'source_block_types':types,'source_bytes':len(src),'plaintext_bytes':len(plain),'zlib_runtime_version':VERSION,'bytes':controls,'fresh_dcp2_only_inverse':True})
 r={'experiment':'codec-decision-prediction-v2','mixed_stored_compressed_validation':mixed,'rows':rows,'all_exact':True};(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--inverse':inverse(sys.argv[2],sys.argv[3])
 else:main()
