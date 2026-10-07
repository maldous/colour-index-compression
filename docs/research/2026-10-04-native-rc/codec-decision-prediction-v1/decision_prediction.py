#!/usr/bin/env python3
"""Fixed zlib-reference DEFLATE token predictor with exact correction stream."""
import gzip, hashlib, json, lzma, runpy, struct, subprocess, sys, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
V1=ROOT/'docs/research/2026-10-04-native-rc/codec-decisions-v1/codec_decisions.py'
D=runpy.run_path(str(V1),run_name='deflate_syntax')
parse,rebuild=D['parse'],D['rebuild']; LEN_BASE,LEN_EXTRA=D['LEN_BASE'],D['LEN_EXTRA']
VERSION=zlib.ZLIB_RUNTIME_VERSION

def raw_deflate(plain, level=6, strategy=zlib.Z_DEFAULT_STRATEGY):
 c=zlib.compressobj(level,zlib.DEFLATED,-15,8,strategy)
 return c.compress(plain)+c.flush()
def parse_raw(raw): return parse(b'\x1f\x8b\x08\x00'+b'\0'*6+raw+b'\0'*8)
def token_len(t): return 1 if t[0]==0 else LEN_BASE[t[1]]+t[2]
def token_map(x):
 m={};off=0
 for b in x['blocks']:
  if b['type']==0:off+=len(b['raw']);continue
  for t in b['tokens']:
   if t[0]!=2:m[off]=t;off+=token_len(t)
 return m

def corrections(orig, ref):
 rm=token_map(ref); off=0; out=[]; stats={'predicted_same':0,'literal_derived':0,'match_explicit':0,'end':0,'total_coded_tokens':0}
 for b in orig['blocks']:
  if b['type']==0:continue
  seq=[]
  for t in b['tokens']:
   stats['total_coded_tokens']+=1
   if t[0]==2:seq.append((3,));stats['end']+=1;continue
   if rm.get(off)==t:seq.append((0,));stats['predicted_same']+=1
   elif t[0]==0:seq.append((1,));stats['literal_derived']+=1
   else:seq.append((2,*t[1:]));stats['match_explicit']+=1
   off+=token_len(t)
  out.append(seq)
 return out,stats

def pack(x, plain, corr):
 o=bytearray(b'DCP1'); vb=VERSION.encode();o+=bytes((len(vb),))+vb
 xp=lzma.compress(plain,preset=1);o+=struct.pack('<QII',x['origlen'],len(x['head']),len(xp));o+=xp;o+=x['head'];o+=struct.pack('<I',len(x['blocks']))
 ci=0
 for b in x['blocks']:
  o.append(b['final']|(b['type']<<1))
  if b['type']==0:
   o+=bytes(b['pad']);o+=b['lens'];o+=struct.pack('<I',len(b['raw']));o+=b['raw'];continue
  if b['type']==2:
   o+=struct.pack('<HHH',b['hlit'],b['hdist'],b['hclen']);o+=bytes(b['ov']);o+=struct.pack('<H',len(b['runs']))
   for s,e in b['runs']:o+=bytes((s,e))
  seq=corr[ci];ci+=1;o+=struct.pack('<I',len(seq))
  for t in seq:
   o.append(t[0])
   if t[0]==2:o+=bytes((t[1],))+struct.pack('<H',t[2])+bytes((t[3],))+struct.pack('<H',t[4])
 o+=bytes(x['endpad']);o+=x['tail'];return bytes(o)

def unpack(blob):
 p=0
 def take(n):
  nonlocal p
  if p+n>len(blob):raise ValueError('truncated container')
  r=blob[p:p+n];p+=n;return r
 if take(4)!=b'DCP1':raise ValueError('bad DCP1 magic')
 vn=take(1)[0];v=take(vn).decode()
 if v!=VERSION:raise ValueError('zlib runtime version mismatch: archive '+v+' decoder '+VERSION)
 orig,hn,xn=struct.unpack('<QII',take(16));plain=lzma.decompress(take(xn));x={'origlen':orig,'head':take(hn),'blocks':[]};cor=[]
 nb=struct.unpack('<I',take(4))[0]
 for _ in range(nb):
  q=take(1)[0];bt=q>>1;b={'final':q&1,'type':bt}
  if bt==0:
   b['pad']=(take(1)[0],take(1)[0]);b['lens']=take(4);n=struct.unpack('<I',take(4))[0];b['raw']=take(n)
  elif bt in (1,2):
   if bt==2:
    b['hlit'],b['hdist'],b['hclen']=struct.unpack('<HHH',take(6));b['ov']=list(take(b['hclen']));rn=struct.unpack('<H',take(2))[0];b['runs']=[tuple(take(2)) for _ in range(rn)]
   n=struct.unpack('<I',take(4))[0];seq=[]
   for _ in range(n):
    tag=take(1)[0]
    if tag in (0,1,3):seq.append((tag,))
    elif tag==2:
     lc=take(1)[0];ex=struct.unpack('<H',take(2))[0];ds=take(1)[0];dx=struct.unpack('<H',take(2))[0];seq.append((2,lc,ex,ds,dx))
    else:raise ValueError('bad correction tag')
   cor.append(seq)
  else:raise ValueError('reserved block')
  x['blocks'].append(b)
 x['endpad']=(take(1)[0],take(1)[0]);x['tail']=take(8)
 if p!=len(blob):raise ValueError('trailing DCP1 bytes')
 return x,plain,cor

def restore(blob):
 x,plain,cor=unpack(blob); ref=parse_raw(raw_deflate(plain));rm=token_map(ref);off=0;ci=0
 for b in x['blocks']:
  if b['type']==0:off+=len(b['raw']);continue
  seq=cor[ci];ci+=1;tokens=[]
  for q in seq:
   tag=q[0]
   if tag==3:tokens.append((2,));continue
   if tag==0:
    if off not in rm:raise ValueError('missing predictor token')
    t=rm[off]
   elif tag==1:t=(0,plain[off])
   else:t=(1,*q[1:])
   tokens.append(t);off+=token_len(t)
  if not tokens or tokens[-1]!=(2,):raise ValueError('missing EOB')
  b['tokens']=tokens
 g=rebuild(x)
 if len(g)!=x['origlen']:raise ValueError('original length mismatch')
 if gzip.decompress(g)!=plain:raise ValueError('plaintext mismatch')
 return g

def tiny():
 common=b'fixed predictor test '*20;dynamic=b''.join(bytes([i])*((i%17)+1) for i in range(256))*20;out=[]
 for name,level,strategy,data,want in [('stored',0,zlib.Z_DEFAULT_STRATEGY,common,0),('fixed',9,zlib.Z_FIXED,common,1),('dynamic',6,zlib.Z_DEFAULT_STRATEGY,dynamic,2)]:
  c=zlib.compressobj(level,zlib.DEFLATED,31,8,strategy);g=c.compress(data)+c.flush();x=parse(g)
  if want not in [b['type'] for b in x['blocks']]:raise AssertionError(name+' block type')
  ref=parse_raw(raw_deflate(data));co,st=corrections(x,ref);a=pack(x,data,co)
  if restore(a)!=g:raise AssertionError(name+' inverse')
  out.append({'case':name,'gzip_bytes':len(g),'dcp1_bytes':len(a),'block_types':[b['type'] for b in x['blocks']],'stats':st})
 return out

def inverse(path, expected):
 g=restore(Path(path).read_bytes());
 if hashlib.sha256(g).hexdigest()!=expected:raise ValueError('source hash mismatch')

def main():
 out=ROOT/'benchmark-work/codec-decision-prediction-v1';out.mkdir(exist_ok=True);tv=tiny();rows=[]
 for n in ['artificial','canterbury','calgary']:
  g=(ROOT/'benchmark-work'/(n+'.tar.gz')).read_bytes();plain=gzip.decompress(g);x=parse(g);ref=parse_raw(raw_deflate(plain));co,st=corrections(x,ref);dcp=pack(x,plain,co)
  if restore(dcp)!=g:raise AssertionError(n+' exact restore')
  cases={'original_gzip':g,'gzip_bytes_zlib9':b'GZB1'+zlib.compress(g,9),'gzip_bytes_xz1':b'GXB1'+lzma.compress(g,preset=1),'decision_predictor_dcp1':dcp}
  fresh=[]
  for k,v in cases.items():
   if k=='decision_predictor_dcp1':
    p=out/(n+'.'+k+'.bin');p.write_bytes(v)
    z=subprocess.run([sys.executable,__file__,'--inverse',str(p),hashlib.sha256(g).hexdigest()],capture_output=True,text=True)
    if z.returncode:raise AssertionError('fresh '+n+': '+z.stderr+z.stdout)
    fresh.append(k)
   elif k!='original_gzip' and len(v)<len(g):
    p=out/(n+'.'+k+'.bin');p.write_bytes(v)
  rows.append({'asset':n,'source_sha256':hashlib.sha256(g).hexdigest(),'source_bytes':len(g),'plaintext_bytes':len(plain),'zlib_runtime_version':VERSION,'original_blocks':len(x['blocks']),'reference_blocks':len(ref['blocks']),'bytes':{k:len(v) for k,v in cases.items()},'token_stats':st,'predictor_same_percent':100*st['predicted_same']/max(1,st['total_coded_tokens']-st['end']),'fresh_archive_only_inverse':fresh})
 r={'experiment':'codec-decision-prediction-v1','tiny_validation':tv,'rows':rows,'all_dcp1_exact':True};(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--inverse':inverse(sys.argv[2],sys.argv[3])
 else:main()
