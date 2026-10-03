#!/usr/bin/env python3
"""Root-owned frozen lease-only batch; native coding, independent readback."""
import json,hashlib,math,os,subprocess,time,zlib,struct
from pathlib import Path
from oracle import rex,rhc
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';WORK=ROOT/'benchmark-work/record-exceptions';RAW=AREA/'raw';ARC=WORK/'archives';BIN=WORK/'build';OLD=ROOT/'docs/research/2026-10-03-constraint-space/record-evidence'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
 p=AREA/name;q=p.with_suffix('.tmp');q.write_text(json.dumps(value,indent=2)+'\n');q.replace(p)
def call(args,tag,out=None,allowed=False):
 start=time.monotonic()
 with (RAW/(tag+'.stderr')).open('wb') as err,(RAW/(tag+'.stdout')).open('wb') as txt:
  dest=Path(out).open('wb') if out else txt
  try:cp=subprocess.run(['/usr/bin/time','-v','-o',str(RAW/(tag+'.time')),*map(str,args)],stdout=dest,stderr=err,timeout=120)
  finally:
   if out:dest.close()
 stats=dict(args=list(map(str,args)),exit=cp.returncode,wall_seconds=time.monotonic()-start)
 if not allowed:assert cp.returncode==0,(tag,(RAW/(tag+'.stderr')).read_text(errors='replace'))
 return stats
def qualified(name,enc,dec,inp,tag,stdout=False,oracle=None):
 arc=ARC/(tag+'-'+name+'.arc');rest=ARC/(tag+'-'+name+'.restored');e=call(enc(arc),tag+'-'+name+'-encode',out=arc if stdout else None);assert arc.exists();d=call(dec(arc,rest),tag+'-'+name+'-decode',out=rest if name in ['zstd19','xz9e','bzip2_9','gzip9','cix_best'] else None);assert sha(rest)==sha(inp)
 row=dict(status='verified',bytes=arc.stat().st_size,archive=str(arc),archive_sha256=sha(arc),restored_sha256=sha(rest),encode=e,decode=d)
 if oracle:row['oracle']=oracle(arc,Path(inp).read_bytes())
 return row
if __name__=='__main__':
 assert os.environ.get('CIX_EXCEPTION_LEASE')=='1','must use root scheduler'
 RAW.mkdir(exist_ok=True);ARC.mkdir(parents=True,exist_ok=True);rows=[]
 oldbindings=json.loads((OLD/'artifact-binding.json').read_text())['artifacts']
 for f in json.loads((AREA/'input-freeze.json').read_text()):
  inp=Path(f['input']);assert sha(inp)==f['input_sha256'];tag=f['name'];row=dict(fixture=f,candidates={},references={});c=row['candidates'];refs=row['references']
  c['exceptions']=qualified('exceptions',lambda a:[BIN/'rex','encode',inp,a],lambda a,o:[BIN/'rex','decode',a,o],inp,tag,oracle=rex)
  # Match histogram controls on exactly the same learned support and width.
  b=c['exceptions']['oracle'].get('b',0)
  row['generator_model_retained']=None if 'generator_parameters'not in f else (b==f['generator_parameters']['b'] and c['exceptions']['oracle'].get('e')==f['generator_parameters']['e'])
  if 2<=b<=12 and len(set(inp.read_bytes()))==2 and len(inp.read_bytes())%b==0:
   for mode in ['histogram','uniform']:
    c[mode]=qualified(mode,lambda a,m=mode:[BIN/'rhc','encode',*(['--uniform']if m=='uniform'else[]),'--width',str(b),inp,a],lambda a,o:[BIN/'rhc','decode',a,o],inp,tag,oracle=rhc)
   assert c['histogram']['oracle']['b']==c['uniform']['oracle']['b'] and c['histogram']['oracle']['K']==c['uniform']['oracle']['K']
  if 'existing'in f:
   old=f['existing']
   for v in [*old['references'].values(),old['modes']['auto']]:
    if v['status']!='verified':continue
    matches=[Path(p)for p,binding in oldbindings.items()if binding['sha256']==v['archive_sha256']]
    assert matches
    for arcpath in matches:assert sha(arcpath)==v['archive_sha256'] and arcpath.stat().st_size==v['bytes']
   refs.update(old['references']);c['exact_only']=old['modes']['auto'];row['reused_reference_receipts']=True
  else:
   c['exact_only']=qualified('exact_only',lambda a:[ROOT/'benchmark-work/equality-records/build/erc','encode','auto',inp,a],lambda a,o:[ROOT/'benchmark-work/equality-records/build/erc','decode',a,o],inp,tag)
   refs['record_dictionary']=qualified('record_dictionary',lambda a:[ROOT/'benchmark-work/equality-records/build/rdic','encode',inp,a],lambda a,o:[ROOT/'benchmark-work/equality-records/build/rdic','decode',a,o],inp,tag)
   specs=[('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c'])]
   for name,en,de in specs:refs[name]=qualified(name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],inp,tag,stdout=True)
   cix=ROOT/'benchmark-work/release-d3a2/final/cix';refs['cix_best']=qualified('cix_best',lambda a:[cix,'--best','--threads','1','--memory','1536MiB','-c',inp],lambda a,o:[cix,'-d','-c',a],inp,tag,stdout=True)
   # CIX stdout decode is explicitly routed below by qualified for this case.
  rows.append(row);save('results.json',rows);print(tag,{k:v['bytes']for k,v in c.items()},{k:v['bytes']for k,v in refs.items()},flush=True)
 # Malformed semantic fields, maps/ranks and histogram metadata; reseal CRC.
 bad=[]
 seed=next(Path(x['candidates']['exceptions']['archive'])for x in rows if x['candidates']['exceptions']['oracle'].get('e',0)>0);base=seed.read_bytes();m=rex(seed,next(Path(x['fixture']['input']).read_bytes()for x in rows if x['candidates']['exceptions'].get('archive')==str(seed)))
 variants={'truncation':base[:-1],'CRC':bytearray(base),'e_exceeds_r':bytearray(base),'map_rank':bytearray(base),'payload_rank':bytearray(base),'exception_length':bytearray(base),'mask':bytearray(base)}
 variants['CRC'][31]^=1;variants['e_exceeds_r'][17:21]=(m['r']+1).to_bytes(4,'little');variants['map_rank'][31:31+m['map_bytes']]=b'\xff'*m['map_bytes'];off=31+m['map_bytes'];variants['payload_rank'][off:off+m['payload_bytes']]=(m['M']**(m['r']-m['e'])).to_bytes(m['payload_bytes'],'big');variants['exception_length'][29]^=1;variants['mask'][21:23]=b'\xff\xff'
 for name,data in variants.items():
  data=bytearray(data)
  if name not in ['truncation','CRC']:data[-4:]=zlib.crc32(data[:-4]).to_bytes(4,'little')
  p=ARC/('bad-'+name+'.arc');o=ARC/('bad-'+name+'.out');p.write_bytes(data);v=call([BIN/'rex','decode',p,o],'bad-'+name,allowed=True);assert v['exit']!=0 and not o.exists();bad.append(dict(name=name,run=v))
 hist=next(Path(x['candidates']['histogram']['archive'])for x in rows if'histogram'in x['candidates']);data=bytearray(hist.read_bytes());k=int.from_bytes(data[13:15],'little');data[15+2*k:17+2*k]=b'\x00\x00';data[-4:]=zlib.crc32(data[:-4]).to_bytes(4,'little');p=ARC/'bad-histogram.arc';o=ARC/'bad-histogram.out';p.write_bytes(data);v=call([BIN/'rhc','decode',p,o],'bad-histogram',allowed=True);assert v['exit']!=0 and not o.exists();bad.append(dict(name='histogram_zero_count',run=v));save('malformed.json',bad)
 save('artifact-binding.json',dict(artifacts={str(p):dict(bytes=p.stat().st_size,sha256=sha(p))for p in sorted(WORK.rglob('*'))if p.is_file()}))
