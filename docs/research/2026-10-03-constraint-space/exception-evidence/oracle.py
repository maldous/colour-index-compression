"""Independent mathematical readback, never a runtime codec."""
import math,struct,zlib
from collections import Counter
def width(n):return (n-1).bit_length()
def word(c,alpha):
 v=0
 for x in c:
  assert x in alpha;v=(v<<1)+(x==alpha[1])
 return v
def rex(arc,src):
 d=arc.read_bytes();assert d[:4]==b'REX1';assert zlib.crc32(d[:-4])==int.from_bytes(d[-4:],'little')
 ver,k,n,b,a0,a1,r,e,mask,cm,cp,ml,pl,el=struct.unpack_from('<BBIBBBIIHBBHHH',d,4);assert ver==1 and n==len(src) and len(d)==35+ml+pl+el
 if k==0:assert d[31:-4]==src;return dict(kind='raw',bytes=len(d))
 alpha=[a0,a1];table=[]
 for v in range(1<<b):
  eq=all(not(mask>>j&1) or ((v>>(b-1-j))&1)==((v>>(b-2-j))&1) for j in range(b-1));h=v.bit_count()
  if eq and (cm==0 or cm==1 and h==cp or cm==2 and h<=cp):table.append(v)
 words=[word(src[j:j+b],alpha)for j in range(0,n,b)];bad=[j for j,v in enumerate(words)if v not in table];assert len(bad)==e and len(words)==r
 mr=sum(math.comb(p,i+1)for i,p in enumerate(bad));good=[v for v in words if v in table];pr=0
 for v in good:pr=pr*len(table)+table.index(v)
 mb=math.comb(r,e);pb=len(table)**(r-e);assert ml==(width(mb)+7)//8 and pl==(width(pb)+7)//8 and el==(b*e+7)//8
 assert int.from_bytes(d[31:31+ml],'big')==mr and int.from_bytes(d[31+ml:31+ml+pl],'big')==pr
 bits=''.join(f'{words[p]:0{b}b}'for p in bad);xb=d[31+ml+pl:-4];expected=int((bits+'0'*((-len(bits))%8))or'0',2).to_bytes(el,'big');assert xb==expected
 return dict(kind='exceptions',b=b,r=r,e=e,M=len(table),mask=mask,count_mode=cm,count_param=cp,model_bytes=5,framing_bytes=30,map_bits=width(mb),map_bytes=ml,payload_bits=width(pb),payload_bytes=pl,exception_bits=b*e,exception_bytes=el,bytes=len(d),exception_positions=bad,independent_map_rank=True,independent_payload_rank=True)
def rhc(arc,src):
 d=arc.read_bytes();assert d[:4]==b'RHC1' and zlib.crc32(d[:-4])==int.from_bytes(d[-4:],'little');mode=d[5];n=int.from_bytes(d[6:10],'little');b=d[10];alpha=list(d[11:13]);k=int.from_bytes(d[13:15],'little');assert n==len(src)
 if mode==0:assert d[15:-4]==src;return dict(mode='raw',bytes=len(d))
 words=[int.from_bytes(d[15+2*i:17+2*i],'little')for i in range(k)];sequence=[word(src[j:j+b],alpha)for j in range(0,n,b)];assert words==sorted(set(sequence));digits=[words.index(v)for v in sequence];r=len(digits);off=15+2*k
 if mode==2:
  card=k**r;rank=0
  for v in digits:rank=rank*k+v
  hist=0
 else:
  counts=[int.from_bytes(d[off+2*i:off+2*i+2],'little')for i in range(k)];assert counts==[sequence.count(v)for v in words];hist=2*k;off+=hist;card=math.factorial(r)
  for c in counts:card//=math.factorial(c)
  remaining=r;ways=card;left=counts[:];rank=0
  for v in digits:
   rank+=sum(ways*left[j]//remaining for j in range(v));ways=ways*left[v]//remaining;left[v]-=1;remaining-=1
 assert len(d)-off-4==(width(card)+7)//8 and int.from_bytes(d[off:-4],'big')==rank
 return dict(mode='uniform'if mode==2 else'histogram',b=b,K=k,model_bytes=2*k,histogram_bytes=hist,payload_bits=width(card),payload_bytes=len(d)-off-4,bytes=len(d),independent_rank=True)
