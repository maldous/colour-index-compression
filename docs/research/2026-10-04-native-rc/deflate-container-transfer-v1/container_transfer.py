#!/usr/bin/env python3
"""Whole-ZIP DCP transfer screen: preserve all non-DEFLATE container bytes."""
import hashlib, io, json, lzma, runpy, struct, subprocess, sys, time, zipfile, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
M=runpy.run_path(str(ROOT/'docs/research/2026-10-04-native-rc/codec-decision-prediction-v2/dcp2_completion.py'),run_name='dcp2')
parse,raw_deflate,parse_raw,pack=M['parse'],M['raw_deflate'],M['parse_raw'],M['pack']
corrections_fixed,restore_fixed=M['corrections_fixed'],M['restore_fixed']

def fake_gzip(raw, plain):
 return b'\x1f\x8b\x08\0'+b'\0'*6+raw+struct.pack('<II',zlib.crc32(plain)&0xffffffff,len(plain)&0xffffffff)
def dcp_for(raw, plain):
 x=parse(fake_gzip(raw,plain));co=corrections_fixed(x,parse_raw(raw_deflate(plain)));dcp=pack(x,plain,co)
 if restore_fixed(dcp)!=fake_gzip(raw,plain):raise AssertionError('member DCP inverse')
 return dcp,co
def raw_from_dcp(dcp):
 g=restore_fixed(dcp)
 return g[10:-8]
def local_data_start(src, info):
 o=info.header_offset
 if src[o:o+4]!=b'PK\x03\x04':raise ValueError('missing local header')
 n,e=struct.unpack_from('<HH',src,o+26)
 return o+30+n+e
def stats(corr):
 s={'P':0,'L':0,'M':0,'E':0}
 for seq in corr:
  for q in seq:s[{0:'P',1:'L',2:'M',3:'E'}[q[0]]]+=1
 return s

def make_inner(src):
 with zipfile.ZipFile(io.BytesIO(src)) as z:
  infos=sorted(z.infolist(),key=lambda q:q.header_offset); chosen=[q for q in infos if q.compress_type==zipfile.ZIP_DEFLATED]
  if any(q.flag_bits&8 for q in chosen):raise ValueError('data descriptors unsupported by frozen screen')
  seg=[];cursor=0;allstats={'P':0,'L':0,'M':0,'E':0};rawsum=0;dcpsum=0
  for q in chosen:
   a=local_data_start(src,q);b=a+q.compress_size
   if a<cursor or b>len(src):raise ValueError('bad ZIP member span')
   plain=z.read(q);raw=src[a:b];dcp,co=dcp_for(raw,plain);seg.append((src[cursor:a],dcp));cursor=b
   ss=stats(co)
   for k in allstats:allstats[k]+=ss[k]
   rawsum+=len(raw);dcpsum+=len(dcp)
  tail=src[cursor:];o=bytearray(b'ZTI1')+struct.pack('<QI',len(src),len(seg))
  for pre,dcp in seg:o+=struct.pack('<I',len(pre))+pre+struct.pack('<I',len(dcp))+dcp
  o+=struct.pack('<I',len(tail))+tail
  return bytes(o),{'entries':len(infos),'deflate_entries':len(chosen),'raw_deflate_bytes':rawsum,'raw_dcp1_bytes':dcpsum,'token_stats':allstats}

def restore_inner(inner):
 p=0
 def take(n):
  nonlocal p
  if p+n>len(inner):raise ValueError('truncated ZTI1')
  q=inner[p:p+n];p+=n;return q
 if take(4)!=b'ZTI1':raise ValueError('bad ZTI1 magic')
 orig,n=struct.unpack('<QI',take(12));out=bytearray()
 for _ in range(n):
  pn=struct.unpack('<I',take(4))[0];out+=take(pn);dn=struct.unpack('<I',take(4))[0];out+=raw_from_dcp(take(dn))
 tn=struct.unpack('<I',take(4))[0];out+=take(tn)
 if p!=len(inner) or len(out)!=orig:raise ValueError('ZTI1 length/trailing mismatch')
 return bytes(out)
def transform(src):
 inner,meta=make_inner(src);ztp=b'ZTP1'+lzma.compress(inner,preset=1)
 if restore(ztp)!=src:raise AssertionError('in-process whole ZIP inverse')
 return ztp,inner,meta
def restore(ztp):
 if ztp[:4]!=b'ZTP1':raise ValueError('bad ZTP1 magic')
 return restore_inner(lzma.decompress(ztp[4:]))
def validate_zip(b):
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  if z.testzip() is not None:raise ValueError('ZIP extraction failed')
  return len(z.infolist()),sum(i.file_size for i in z.infolist())
def fixture():
 bio=io.BytesIO()
 with zipfile.ZipFile(bio,'w') as z:
  a=zipfile.ZipInfo('stored.txt');a.compress_type=zipfile.ZIP_STORED;z.writestr(a,b'nonempty stored zip member')
  b=zipfile.ZipInfo('deflated.txt');b.compress_type=zipfile.ZIP_DEFLATED;z.writestr(b,b'deflate transfer validation '*100)
 src=bio.getvalue();ztp,inner,meta=transform(src);got=restore(ztp)
 if got!=src:raise AssertionError('fixture byte inverse')
 return {'source_bytes':len(src),'ztp1_bytes':len(ztp),'entries':validate_zip(got)[0],'deflate_entries':meta['deflate_entries'],'exact':True}

INPUT=ROOT/'benchmark-work/references/cmix-v21/upstream.zip'
SHA='8fd46731ed0125707021c2db4feb24179617b3993b735c335f2e0b3c00e5a0dc'
def inverse(path,expected):
 got=restore(Path(path).read_bytes());validate_zip(got)
 if hashlib.sha256(got).hexdigest()!=expected:raise ValueError('original ZIP SHA mismatch')
def main():
 out=ROOT/'benchmark-work/deflate-container-transfer-v1';out.mkdir(exist_ok=True);fix=fixture();src=INPUT.read_bytes()
 if hashlib.sha256(src).hexdigest()!=SHA:raise ValueError('frozen input identity mismatch')
 ztp,inner,meta=transform(src);p=out/'upstream.ztp1.bin';p.write_bytes(ztp)
 z=subprocess.run([sys.executable,__file__,'--inverse',str(p),SHA],capture_output=True,text=True)
 if z.returncode:raise AssertionError('fresh inverse: '+z.stdout+z.stderr)
 ec,ei=validate_zip(src);gc,gi=validate_zip(restore(ztp))
 r={'experiment':'deflate-container-transfer-v1','input_sha256':SHA,'fixture':fix,'container_validation':{'original_entries':ec,'reconstructed_entries':gc,'original_inflated_bytes':ei,'reconstructed_inflated_bytes':gi},'transfer':meta,'bytes':{'original_zip':len(src),'same_frame_zlib9':len(b'ZBZ1'+zlib.compress(src,9)),'same_frame_xz1':len(b'ZBX1'+lzma.compress(src,preset=1)),'raw_zt_inner':len(inner),'ztp1_complete':len(ztp)},'fresh_ztp1_only_inverse':True}
 (out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='--inverse':inverse(sys.argv[2],sys.argv[3])
 else:main()
