from pathlib import Path
import json,sys,importlib.util,os,struct,zlib,time,subprocess
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/lane-evidence';OLD=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';PREV=AREA.parent/'evidence';WORK=ROOT/'benchmark-work/segmentation-lanes';RAW=AREA/'raw';ARC=WORK/'archives';BIN=WORK/'build';sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('paid_runner',OLD/'run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.AREA=AREA;p.WORK=WORK;p.RAW=RAW;p.ARC=ARC;p.BIN=BIN

def bounded_call(args,tag,out=None,allowed=False):
 start=time.monotonic()
 with(RAW/(tag+'.stderr')).open('wb')as err,(RAW/(tag+'.stdout')).open('wb')as txt:
  dest=Path(out).open('wb')if out else txt
  try:cp=subprocess.run(['/usr/bin/time','-v','-o',str(RAW/(tag+'.time')),*map(str,args)],stdout=dest,stderr=err,timeout=120 if'cix_best'in tag else 30)
  finally:
   if out:dest.close()
 if not allowed:assert cp.returncode==0,(tag,(RAW/(tag+'.stderr')).read_text(errors='replace'))
 return dict(args=list(map(str,args)),exit=cp.returncode,wall_seconds=time.monotonic()-start)
p.call=bounded_call

def check(q,src,tag):
 b=Path(q['archive']).read_bytes();assert b[:5]==b'NCSL\x01';n,crc,s,t,k=struct.unpack_from('<IIBBH',b,5);assert n==len(src)and zlib.crc32(src)==crc;off=17;lanes=[]
 for index in range(k):
  route,length,pl=struct.unpack_from('<BII',b,off);off+=9;assert route<4 and length==(max(0,n-index)+s-1)//s and off+pl<=len(b);lanes.append(dict(offset=index,archive_offset=off-9,stride=s,length=length,route_id=route,metadata_bytes=9,payload_bytes=pl,total_bytes=9+pl));off+=pl
 assert off==len(b)and len(b)==17+sum(x['total_bytes']for x in lanes);trace=json.loads((RAW/(tag+'-encode.stdout')).read_text());assert trace['archive_bytes']==len(b)and trace['selected_stride']==s and trace['selected_transform']==t
 assert len(trace['lanes'])==len(lanes)
 for actual,claimed in zip(lanes,trace['lanes']):
  assert claimed['input_offset']==actual['offset']and claimed['archive_offset']==actual['archive_offset']and claimed['count']==actual['length']and claimed['stride']==s and claimed['route']==['raw','huffman','adaptive','legacy-lz'][actual['route_id']]
  for field in['metadata_bytes','payload_bytes','total_bytes']:assert claimed[field]==actual[field]
 chosen=[x for x in trace['candidates']if x['stride']==s and x['transform']==t];assert len(chosen)==1 and chosen[0]['complete_bytes']==len(b)and min(x['complete_bytes']for x in trace['candidates'])==len(b)
 q['trace']=trace;q['accounting']=dict(header_bytes=17,lanes=lanes,complete_bytes=len(b));return q

if __name__=='__main__':
 assert os.environ.get('CIX_LANE_LEASE')=='1';RAW.mkdir(exist_ok=True);ARC.mkdir(parents=True,exist_ok=True);rows=[];bindings=json.loads((PREV/'artifact-binding.json').read_text())['artifacts']
 for f in json.loads((AREA/'input-freeze.json').read_text()):
  inp=Path(f['input']);assert p.sha(inp)==f['input_sha256'];tag=f['name'];c={};row=dict(fixture=f,candidates=c,references={})
  for policy in['whole','shuffle','auto']:
   q=p.qualified(policy,lambda a,policy=policy:[BIN/'lanes','encode','--policy',policy,inp,a],lambda a,o:[BIN/'lanes','decode',a,o],inp,tag);c[policy]=check(q,inp.read_bytes(),tag+'-'+policy)
  assert c['auto']['bytes']<=c['shuffle']['bytes']<=c['whole']['bytes']
  stride=c['auto']['trace']['selected_stride'];transform=c['auto']['trace']['selected_transform'];q=p.qualified('matched_zstd',lambda a:[BIN/'zsc','encode','--stride',str(stride),'--transform',str(transform),inp,a],lambda a,o:[BIN/'zsc','decode',a,o],inp,tag);b=Path(q['archive']).read_bytes();assert b[:5]==b'ZSC1\x01';n,crc,ss,tt,kk,pl=struct.unpack_from('<IIBBHI',b,5);assert len(b)==21+pl and n==f['input_bytes']and crc==zlib.crc32(inp.read_bytes())and ss==stride and tt==transform and kk==(stride if n else 0);q['accounting']=dict(header_bytes=21,payload_bytes=pl,stride=ss,transform=tt);q['trace']=json.loads((RAW/(tag+'-matched_zstd-encode.stdout')).read_text());assert q['trace']['archivebytes']==len(b)and q['trace']['sourcebytes']==n and q['trace']['modelbytes']==21 and q['trace']['payloadbytes']==pl and q['trace']['stride']==ss and q['trace']['transform']==tt;row['references']['matched_zstd']=q
  if'previous'in f:
   prev=f['previous'];assert c['whole']['bytes']==prev['candidates']['whole']['bytes'];row['references'].update(prev['references']);row['previous_candidates']=prev['candidates']
   for v in[*prev['candidates'].values(),*prev['references'].values()]:assert p.sha(v['archive'])==v['archive_sha256']and bindings[v['archive']]['sha256']==v['archive_sha256']
  else:
   specs=[('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c'])]
   for name,en,de in specs:row['references'][name]=p.qualified(name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],inp,tag,stdout=True)
   cix=ROOT/'benchmark-work/release-d3a2/final/cix';row['references']['cix_best']=p.qualified('cix_best',lambda a:[cix,'--best','--threads','1','--memory','1536MiB','-c',inp],lambda a,o:[cix,'-d','-c',a],inp,tag,stdout=True)
  rows.append(row);p.save('results.json',rows);print(tag,{k:v['bytes']for k,v in c.items()},{k:v['bytes']for k,v in row['references'].items()},flush=True)
 seed=Path(next(x['candidates']['auto']['archive']for x in rows if x['candidates']['auto']['trace']['selected_transform']==1));base=seed.read_bytes();variants={'truncated':base[:-1],'trailing':base+b'\0'}
 for name,offset,value,width in[('stride_zero',13,0,1),('stride_large',13,9,1),('transform',14,2,1),('lane_count',15,9,2),('source_length',5,4097,4),('lane_length',18,1<<30,4),('payload_length',22,32768,4),('route_id',17,255,1)]:
  b=bytearray(base);b[offset:offset+width]=value.to_bytes(width,'little');variants[name]=b
 b=bytearray(base);b[9]^=1;variants['CRC']=b
 payload=bytearray(19);payload[0]=1;payload[3:11]=(1<<40).to_bytes(8,'little');variants['Huffman_length']=b'NCSL\x01'+struct.pack('<IIBBH',1,0,1,0,1)+struct.pack('<BII',1,1,len(payload))+payload
 bad=[]
 for name,data in variants.items():
  a=ARC/('bad-'+name+'.arc');o=ARC/('bad-'+name+'.out');a.write_bytes(data);r=p.call([BIN/'lanes','decode',a,o],'bad-'+name,allowed=True);assert r['exit']!=0 and not o.exists();bad.append(dict(name=name,run=r))
 zs=Path(rows[-1]['references']['matched_zstd']['archive']).read_bytes();zd=bytearray(zs+b'\0');zd[17:21]=(len(zs)-21+1).to_bytes(4,'little');za=ARC/'bad-zstd-trailing.arc';zo=ARC/'bad-zstd-trailing.out';za.write_bytes(zd);zr=p.call([BIN/'zsc','decode',za,zo],'bad-zstd-trailing',allowed=True);assert zr['exit']!=0 and not zo.exists();bad.append(dict(name='zstd_trailing_frame',run=zr))
 r=p.call([BIN/'lanes'],'bad-no-arguments',allowed=True);assert r['exit']!=0;bad.append(dict(name='no_arguments',run=r));p.save('malformed.json',bad);p.save('artifact-binding.json',dict(artifacts={str(q):dict(bytes=q.stat().st_size,sha256=p.sha(q))for q in sorted(WORK.rglob('*'))if q.is_file()}))
