#!/usr/bin/env python3
"""Byte-exact DEFLATE syntax container screen; standard library only."""
import gzip, hashlib, json, lzma, struct, subprocess, sys, time, zlib
from pathlib import Path

LEN_BASE=[3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LEN_EXTRA=[0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
DIS_BASE=[1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
DIS_EXTRA=[0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
CL_ORDER=[16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]

class BitReader:
 def __init__(self,b): self.b=b; self.p=0
 def get(self,n):
  if self.p+n>len(self.b)*8: raise ValueError('truncated deflate')
  v=0
  for i in range(n): v|=((self.b[(self.p+i)//8]>>((self.p+i)%8))&1)<<i
  self.p+=n; return v
 def raw(self,n):
  if self.p%8: raise ValueError('raw unaligned')
  q=self.p//8; self.p+=n*8; return self.b[q:q+n]

class BitWriter:
 def __init__(self): self.a=bytearray(); self.p=0
 def put(self,v,n):
  for i in range(n):
   if self.p%8==0:self.a.append(0)
   self.a[-1]|=((v>>i)&1)<<(self.p%8); self.p+=1
 def raw(self,b):
  if self.p%8: raise ValueError('raw unaligned')
  self.a.extend(b);self.p+=8*len(b)
 def out(self): return bytes(self.a)

def rev(v,n):
 r=0
 for _ in range(n): r=(r<<1)|(v&1);v>>=1
 return r
def huff(lengths):
 count=[0]*16
 for x in lengths:
  if x: count[x]+=1
 code=0;nxt=[0]*16
 for bits in range(1,16): code=(code+count[bits-1])<<1;nxt[bits]=code
 enc={}; dec={}
 for sym,n in enumerate(lengths):
  if n:
   c=rev(nxt[n],n);nxt[n]+=1;enc[sym]=(c,n);dec[(n,c)]=sym
 return enc,dec
FIX_LL=[8]*144+[9]*112+[7]*24+[8]*8
FIX_D=[5]*32
def getsym(r,dec):
 v=0
 for n in range(1,16):
  v|=r.get(1)<<(n-1)
  if (n,v) in dec:return dec[(n,v)]
 raise ValueError('invalid huffman symbol')
def putsym(w,enc,s):
 c,n=enc[s];w.put(c,n)

def gzip_parts(g):
 if g[:3]!=b'\x1f\x8b\x08': raise ValueError('not gzip/deflate')
 flg=g[3]; p=10
 if flg&4: n=struct.unpack_from('<H',g,p)[0];p+=2+n
 for bit in (8,16):
  if flg&bit:
   while g[p]:p+=1
   p+=1
 if flg&2:p+=2
 if p+8>len(g):raise ValueError('truncated gzip')
 return g[:p],g[p:-8],g[-8:]

def dynamic(r):
 hlit=r.get(5)+257; hdist=r.get(5)+1; hclen=r.get(4)+4
 ordervals=[r.get(3) for _ in range(hclen)]
 cl=[0]*19
 for i,v in enumerate(ordervals):cl[CL_ORDER[i]]=v
 _,d=huff(cl); vals=[];prev=0
 while len(vals)<hlit+hdist:
  s=getsym(r,d); e=0
  if s<16: vals.append(s);prev=s
  elif s==16:
   e=r.get(2); vals.extend([prev]*(3+e))
  elif s==17:
   e=r.get(3); vals.extend([0]*(3+e));prev=0
  elif s==18:
   e=r.get(7); vals.extend([0]*(11+e));prev=0
  else:raise ValueError('bad codelen sym')
  if len(vals)>hlit+hdist:raise ValueError('codelen overflow')
  # Need record every syntactic header decision, not only expanded values.
  # Attach to stream separately using a local list retained below.
 # rerun impossible; retain by reparse callers need actual list, so encode from vals canonically would alter bitstream.
 return hlit,hdist,hclen,ordervals,vals

def parse(g):
 head,body,tail=gzip_parts(g);r=BitReader(body);blocks=[]
 while True:
  final=r.get(1);typ=r.get(2); b={'final':final,'type':typ}
  if typ==0:
   k=(-r.p)%8;b['pad']=(k,r.get(k));b['lens']=r.raw(4);n=struct.unpack_from('<H',b['lens'])[0]
   b['raw']=r.raw(n);blocks.append(b)
  elif typ in (1,2):
   if typ==1: ll=FIX_LL; dd=FIX_D
   else:
    # Parse dynamic header manually so its exact run decisions are retained.
    hlit=r.get(5)+257;hdist=r.get(5)+1;hclen=r.get(4)+4
    ov=[r.get(3) for _ in range(hclen)];cl=[0]*19
    for i,v in enumerate(ov):cl[CL_ORDER[i]]=v
    ce,cd=huff(cl);vals=[];runs=[];prev=0
    while len(vals)<hlit+hdist:
     s=getsym(r,cd);e=0
     if s<16:vals.append(s);prev=s
     elif s==16:e=r.get(2);vals.extend([prev]*(3+e))
     elif s==17:e=r.get(3);vals.extend([0]*(3+e));prev=0
     elif s==18:e=r.get(7);vals.extend([0]*(11+e));prev=0
     else:raise ValueError('bad codelen symbol')
     runs.append((s,e))
     if len(vals)>hlit+hdist:raise ValueError('codelen overflow')
    ll=vals[:hlit]+[0]*(286-hlit);dd=vals[hlit:]+[0]*(32-hdist)
    b.update({'hlit':hlit,'hdist':hdist,'hclen':hclen,'ov':ov,'runs':runs})
   le,ld=huff(ll);de,ddc=huff(dd);tokens=[]
   while True:
    s=getsym(r,ld)
    if s<256:tokens.append((0,s));continue
    if s==256:tokens.append((2,));break
    if not 257<=s<=285:raise ValueError('bad length symbol')
    lc=s-257; ex=r.get(LEN_EXTRA[lc]);ds=getsym(r,ddc)
    if ds>29:raise ValueError('bad distance symbol')
    dx=r.get(DIS_EXTRA[ds]);tokens.append((1,lc,ex,ds,dx))
   b['tokens']=tokens;blocks.append(b)
  else:raise ValueError('reserved deflate block')
  if final:break
 k=(-r.p)%8; pad=r.get(k)
 if r.p!=len(body)*8:raise ValueError('unconsumed deflate body')
 return {'head':head,'tail':tail,'blocks':blocks,'endpad':(k,pad),'origlen':len(g)}

def rebuild(x):
 w=BitWriter()
 for b in x['blocks']:
  w.put(b['final'],1);w.put(b['type'],2)
  if b['type']==0:
   k,v=b['pad'];w.put(v,k);w.raw(b['lens']);w.raw(b['raw']);continue
  if b['type']==1:ll=FIX_LL;dd=FIX_D
  else:
   w.put(b['hlit']-257,5);w.put(b['hdist']-1,5);w.put(b['hclen']-4,4)
   for v in b['ov']:w.put(v,3)
   cl=[0]*19
   for i,v in enumerate(b['ov']):cl[CL_ORDER[i]]=v
   ce,cd=huff(cl)
   for s,e in b['runs']:
    putsym(w,ce,s)
    if s==16:w.put(e,2)
    elif s==17:w.put(e,3)
    elif s==18:w.put(e,7)
   # expanded values needed only to build literal/distance codes
   vals=[];prev=0
   for s,e in b['runs']:
    if s<16:vals.append(s);prev=s
    elif s==16:vals.extend([prev]*(3+e))
    elif s==17:vals.extend([0]*(3+e));prev=0
    else:vals.extend([0]*(11+e));prev=0
   ll=vals[:b['hlit']]+[0]*(286-b['hlit']);dd=vals[b['hlit']:]+[0]*(32-b['hdist'])
  le,_=huff(ll);de,_=huff(dd)
  for t in b['tokens']:
   if t[0]==0:putsym(w,le,t[1])
   elif t[0]==2:putsym(w,le,256)
   else:
    _,lc,ex,ds,dx=t;putsym(w,le,257+lc);w.put(ex,LEN_EXTRA[lc]);putsym(w,de,ds);w.put(dx,DIS_EXTRA[ds])
 k,v=x['endpad'];w.put(v,k)
 return x['head']+w.out()+x['tail']

def pack(x):
 o=bytearray(b'CDV1');o+=struct.pack('<QII',x['origlen'],len(x['head']),len(x['blocks']));o+=x['head']
 for b in x['blocks']:
  o.append(b['final']|(b['type']<<1))
  if b['type']==0:
   o.append(b['pad'][0]);o.append(b['pad'][1]);o+=b['lens'];o+=struct.pack('<I',len(b['raw']));o+=b['raw'];continue
  if b['type']==2:
   o+=struct.pack('<HHH',b['hlit'],b['hdist'],b['hclen']);o+=bytes(b['ov']);o+=struct.pack('<H',len(b['runs']))
   for s,e in b['runs']:o+=bytes((s,e))
  o+=struct.pack('<I',len(b['tokens']))
  for t in b['tokens']:
   o.append(t[0]);
   if t[0]==0:o.append(t[1])
   elif t[0]==1:o+=bytes((t[1],))+struct.pack('<H',t[2])+bytes((t[3],))+struct.pack('<H',t[4])
 o+=bytes(x['endpad']);o+=x['tail'];return bytes(o)

def unpack(blob):
 p=0
 def take(n):
  nonlocal p
  if p+n>len(blob):raise ValueError('container truncated')
  z=blob[p:p+n];p+=n;return z
 if take(4)!=b'CDV1':raise ValueError('bad magic')
 orig,hn,nb=struct.unpack('<QII',take(16));x={'origlen':orig,'head':take(hn),'blocks':[]}
 for _ in range(nb):
  q=take(1)[0];bt=q>>1;b={'final':q&1,'type':bt}
  if bt==0:
   b['pad']=(take(1)[0],take(1)[0]);b['lens']=take(4);n=struct.unpack('<I',take(4))[0];b['raw']=take(n)
  else:
   if bt==2:
    b['hlit'],b['hdist'],b['hclen']=struct.unpack('<HHH',take(6));b['ov']=list(take(b['hclen']));rn=struct.unpack('<H',take(2))[0];b['runs']=[tuple(take(2)) for _ in range(rn)]
   tn=struct.unpack('<I',take(4))[0];b['tokens']=[]
   for _ in range(tn):
    tag=take(1)[0]
    if tag==0:b['tokens'].append((0,take(1)[0]))
    elif tag==1:
     lc=take(1)[0]; ex=struct.unpack('<H',take(2))[0]; ds=take(1)[0]; dx=struct.unpack('<H',take(2))[0]
     b['tokens'].append((1,lc,ex,ds,dx))
    elif tag==2:b['tokens'].append((2,))
    else:raise ValueError('bad token tag')
  x['blocks'].append(b)
 x['endpad']=(take(1)[0],take(1)[0]);x['tail']=take(8)
 if p!=len(blob):raise ValueError('trailing container data')
 if len(rebuild(x))!=orig:raise ValueError('length mismatch')
 return x

def validate_tiny():
 data=(b'fixed dynamic stored validation '*20)
 dynamic_data=b''.join(bytes([i])*((i%17)+1) for i in range(256))*20
 out=[]
 for name,level,strat in [('stored',0,zlib.Z_DEFAULT_STRATEGY),('fixed',9,zlib.Z_FIXED),('dynamic',6,zlib.Z_DEFAULT_STRATEGY)]:
  source=dynamic_data if name=='dynamic' else data
  co=zlib.compressobj(level,zlib.DEFLATED,31,8,strat);g=co.compress(source)+co.flush(); x=parse(g);c=pack(x);back=rebuild(unpack(c))
  if back!=g or gzip.decompress(back)!=source:raise AssertionError(name)
  types=[b['type'] for b in x['blocks']]
  wanted={'stored':0,'fixed':1,'dynamic':2}[name]
  if wanted not in types:raise AssertionError(name+' did not select required block type')
  out.append({'case':name,'gzip_bytes':len(g),'decision_bytes':len(c),'blocks':len(x['blocks']),'block_types':types})
 return out

def main():
 root=Path(__file__).resolve().parents[4];out=root/'benchmark-work/codec-decisions-v1';out.mkdir(exist_ok=True)
 tiny=validate_tiny(); names=['artificial','canterbury','calgary']; rows=[]
 for n in names:
  src=root/'benchmark-work'/(n+'.tar.gz');g=src.read_bytes();x=parse(g);c=pack(x);back=rebuild(unpack(c))
  if back!=g or gzip.decompress(back)!=gzip.decompress(g):raise AssertionError(n+' base inverse')
  cases={'original_gzip':g,'gzip_bytes_zlib9':b'GZB1'+zlib.compress(g,9),'gzip_bytes_xz1':b'GXB1'+lzma.compress(g,preset=1),'decision_unsplit':c,'decision_zlib9':b'CDZ1'+zlib.compress(c,9),'decision_xz1':b'CDX1'+lzma.compress(c,preset=1)}
  check={}
  for k,v in cases.items():
   if k.startswith('decision_'):
    q=v if k=='decision_unsplit' else (zlib.decompress(v[4:]) if k=='decision_zlib9' else lzma.decompress(v[4:]))
    got=rebuild(unpack(q));check[k]=(got==g and gzip.decompress(got)==gzip.decompress(g))
   else:
    q=zlib.decompress(v[4:]) if k=='gzip_bytes_zlib9' else (lzma.decompress(v[4:]) if k=='gzip_bytes_xz1' else g)
    check[k]=(q==g and gzip.decompress(q)==gzip.decompress(g))
  if not all(check.values()):raise AssertionError(n+' candidate inverse')
  retained=[]
  for k,v in cases.items():
   if k!='original_gzip' and len(v)<len(g):
    p=out/(n+'.'+k+'.bin');p.write_bytes(v)
    z=subprocess.run([sys.executable,__file__,'--inverse',str(p),hashlib.sha256(g).hexdigest()],capture_output=True,text=True)
    if z.returncode:raise AssertionError('fresh inverse '+n+' '+k+': '+z.stderr+z.stdout)
    retained.append(k)
  rows.append({'asset':n,'source_sha256':hashlib.sha256(g).hexdigest(),'source_bytes':len(g),'inflated_bytes':len(gzip.decompress(g)),'blocks':len(x['blocks']),'block_types':{str(t):sum(1 for b in x['blocks'] if b['type']==t) for t in range(3)},'bytes':{k:len(v) for k,v in cases.items()},'inverse_verified':check,'fresh_archive_only_inverse':retained})
 result={'experiment':'codec-decisions-v1','tiny_validation':tiny,'rows':rows,'all_exact':True,'note':'zlib/xz ordinary second-pass payloads are not original gzip streams; only decision candidates are self-contained byte-exact reconstructions.'}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
def inverse_main(path, expected):
 b=Path(path).read_bytes(); magic=b[:4]
 if magic==b'GZB1':g=zlib.decompress(b[4:])
 elif magic==b'GXB1':g=lzma.decompress(b[4:])
 elif magic==b'CDV1':g=rebuild(unpack(b))
 elif magic==b'CDZ1':g=rebuild(unpack(zlib.decompress(b[4:])))
 elif magic==b'CDX1':g=rebuild(unpack(lzma.decompress(b[4:])))
 else:raise ValueError('unknown archive magic')
 gzip.decompress(g)
 if hashlib.sha256(g).hexdigest()!=expected:raise ValueError('source hash mismatch')

if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--inverse':inverse_main(sys.argv[2],sys.argv[3])
 else:main()
