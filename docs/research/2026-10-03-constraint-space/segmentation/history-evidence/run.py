from pathlib import Path
import json,sys,importlib.util,os,struct,zlib
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/history-evidence';OLD=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';PREV=AREA.parent/'evidence';WORK=ROOT/'benchmark-work/segmentation-history';RAW=AREA/'raw';ARC=WORK/'archives';BIN=WORK/'build';sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('paid_runner',OLD/'run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p);p.AREA=AREA;p.WORK=WORK;p.RAW=RAW;p.ARC=ARC;p.BIN=BIN

def check(q,src,tag):
 b=Path(q['archive']).read_bytes();assert b[:5]==b'NSCH\x01';h,n,k,crc=struct.unpack_from('<HIII',b,5);assert n==len(src) and crc==zlib.crc32(src);off=19;pos=0;timeline=[];trace=json.loads((RAW/(tag+'-encode.stdout')).read_text())
 for _ in range(k):
  route,length,pl=struct.unpack_from('<BII',b,off);off+=9;assert route<4 and length>0 and off+pl<=len(b);timeline.append(dict(start=pos,length=length,route_id=route,metadata_bytes=9,payload_bytes=pl,complete_bytes=9+pl));off+=pl;pos+=length
 assert len(timeline)==len(trace['selected_segments'])
 for actual,claimed in zip(timeline,trace['selected_segments']):
  assert actual['route_id']==['raw','huffman','adaptive','legacy-lz'].index(claimed['route']) and actual['start']==claimed['start'] and actual['length']==claimed['len'] and actual['complete_bytes']==claimed['total_bytes']
 assert off==len(b) and pos==n and len(b)==19+sum(x['complete_bytes']for x in timeline) and h==trace['history_bytes'];q['trace']=trace;q['accounting']=dict(header_bytes=19,history_bytes=h,timeline=timeline)
 if trace['edge_cost_matrix']is not None:
  points=trace['boundary_points'];costs=trace['edge_cost_matrix'];best={(0,0):0}
  for j in range(1,len(points)):
   for count in range(1,min(j,32)+1):
    vals=[best[(i,count-1)]+costs[i][j]for i in range(j)if(i,count-1)in best]
    if vals:best[(j,count)]=min(vals)
  assert 19+min(v for(j,_),v in best.items()if j==len(points)-1)==len(b)
 return q

if __name__=='__main__':
 assert os.environ.get('CIX_HISTORY_LEASE')=='1';RAW.mkdir(exist_ok=True);ARC.mkdir(parents=True,exist_ok=True);rows=[];bindings=json.loads((PREV/'artifact-binding.json').read_text())['artifacts']
 for previous in json.loads((PREV/'results.json').read_text()):
  f=previous['fixture'];inp=Path(f['input']);assert p.sha(inp)==f['input_sha256']
  for v in [*previous['candidates'].values(),*previous['references'].values()]:assert p.sha(v['archive'])==v['archive_sha256']and bindings[v['archive']]['sha256']==v['archive_sha256']
  c={};row=dict(fixture=f,candidates=c,previous=previous)
  arms=[(0,'adaptive',['--adaptive']),(1024,'adaptive',['--adaptive'])]
  if f['split']=='oracle':
   ref='--tiny-oracle'if f['input_bytes']<=12 else'--small-reference';arms.extend([(h,'reference',[ref])for h in[0,1024]])
  else:arms.extend([(1024,'whole',['--whole']),(1024,'fixed256',['--fixed','256']),(1024,'fixed1024',['--fixed','1024'])])
  for h,mode,args in arms:
   name='H'+str(h)+'-'+mode;tag=f['name'];q=p.qualified(name,lambda a,h=h,args=args:[BIN/'history','--history',str(h),*args,inp,a],lambda a,o:[BIN/'history','decode',a,o],inp,tag);c[name]=check(q,inp.read_bytes(),tag+'-'+name)
  assert c['H0-adaptive']['bytes']==previous['candidates']['adaptive']['bytes']+2
  rows.append(row);p.save('results.json',rows);print(f['name'],{k:v['bytes']for k,v in c.items()},flush=True)
 seed=Path(next(x['candidates']['H1024-fixed256']['archive']for x in rows if x['fixture']['name']=='development-long-dependency'));base=seed.read_bytes();variants={'truncation':base[:-1],'trailing':base+b'\0'}
 for name,offset,value,width in [('history_limit',5,4097,2),('source_length',7,4097,4),('segment_count',11,33,4),('segment_length',20,0,4)]:
  b=bytearray(base);b[offset:offset+width]=value.to_bytes(width,'little');variants[name]=b
 b=bytearray(base);b[19]=255;variants['route_id']=b;b=bytearray(base);b[15]^=1;variants['CRC']=b;bad=[]
 for name,data in variants.items():
  a=ARC/('bad-'+name+'.arc');o=ARC/('bad-'+name+'.out');a.write_bytes(data);r=p.call([BIN/'history','decode',a,o],'bad-'+name,allowed=True);assert r['exit']!=0 and not o.exists();bad.append(dict(name=name,run=r))
 probes=[]
 for x in rows:
  if 'H1024-fixed256'not in x['candidates']:continue
  original=Path(x['candidates']['H1024-fixed256']['archive']);data=bytearray(original.read_bytes());data[5:7]=b'\0\0';name=x['fixture']['name']+'-H0-probe';a=ARC/(name+'.arc');o=ARC/(name+'.out');a.write_bytes(data);r=p.call([BIN/'history','decode',a,o],name,allowed=True)
  if r['exit']==0:assert p.sha(o)==x['fixture']['input_sha256']
  else:assert not o.exists()
  probes.append(dict(fixture=x['fixture']['name'],status='compatible_H0_payload'if r['exit']==0 else'dependent_on_history',run=r))
 assert any(x['status']=='dependent_on_history'for x in probes)
 p.save('history-dependency-probes.json',probes)
 p.save('malformed.json',bad);p.save('artifact-binding.json',dict(artifacts={str(q):dict(bytes=q.stat().st_size,sha256=p.sha(q))for q in sorted(WORK.rglob('*'))if q.is_file()}))
