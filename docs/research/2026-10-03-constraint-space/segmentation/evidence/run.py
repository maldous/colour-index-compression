"""Frozen local independent-segment screen; native codecs only."""
from pathlib import Path
import importlib.util,sys,json,hashlib,os,struct,subprocess,time,zlib
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/evidence';WORK=ROOT/'benchmark-work/segmentation-reference';RAW=AREA/'raw';ARC=WORK/'archives';BIN=WORK/'build'
OLD=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';sys.path.insert(0,str(OLD))
spec=importlib.util.spec_from_file_location('paid_runner',OLD/'run.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p.AREA=AREA;p.WORK=WORK;p.RAW=RAW;p.ARC=ARC;p.BIN=BIN
sha=p.sha;save=p.save;call=p.call;qualified=p.qualified

def parse(archive,source,trace):
 b=Path(archive).read_bytes();assert b[:5]==b'NCSC\x01';n,k,crc=struct.unpack_from('<III',b,5);assert n==len(source) and crc==zlib.crc32(source);off=17;pos=0;timeline=[]
 for _ in range(k):
  route,length,pl=struct.unpack_from('<BII',b,off);assert route<4 and length>0;off+=9;assert off+pl<=len(b);timeline.append(dict(start=pos,length=length,route_id=route,metadata_bytes=9,payload_bytes=pl,complete_bytes=9+pl));pos+=length;off+=pl
 assert pos==n and off==len(b);assert len(b)==17+sum(t['complete_bytes']for t in timeline)
 assert trace['archive_bytes']==len(b) and len(trace['selected_segments'])==k
 for actual,claimed in zip(timeline,trace['selected_segments']):
  for field in ['start','length','metadata_bytes','payload_bytes','complete_bytes']:assert actual[field]==claimed[{'length':'len','complete_bytes':'total_bytes'}.get(field,field)],(field,actual,claimed)
 return dict(header_bytes=17,timeline=timeline,complete_bytes=len(b),CRC_verified=True)

def native(inp,tag,mode,args):
 q=qualified(mode,lambda a:[BIN/'segments',*args,inp,a],lambda a,o:[BIN/'segments','decode',a,o],inp,tag)
 trace=json.loads((RAW/(tag+'-'+mode+'-encode.stdout')).read_text());q['trace']=trace;q['accounting']=parse(q['archive'],Path(inp).read_bytes(),trace)
 if mode=='tiny':assert trace['exhaustive_partition_gap_bytes']==0
 if mode in ['tiny','reference']:
  points=trace['boundary_points'];costs=trace['edge_cost_matrix'];best={(0,0):0}
  for j in range(1,len(points)):
   for count in range(1,min(j,32)+1):
    vals=[best[(i,count-1)]+costs[i][j] for i in range(j)if(i,count-1)in best]
    if vals:best[(j,count)]=min(vals)
  value=17+min((v for (j,_),v in best.items()if j==len(points)-1),default=0)
  assert value==q['bytes'];q['independent_DP_bytes']=value
 return q

if __name__=='__main__':
 assert os.environ.get('CIX_SEGMENT_LEASE')=='1';RAW.mkdir(exist_ok=True);ARC.mkdir(parents=True,exist_ok=True);rows=[]
 for f in json.loads((AREA/'input-freeze.json').read_text()):
  inp=Path(f['input']);assert sha(inp)==f['input_sha256'];tag=f['name'];row=dict(fixture=f,candidates={},references={});c=row['candidates']
  c['whole']=native(inp,tag,'whole',['--whole']);c['adaptive']=native(inp,tag,'adaptive',['--adaptive'])
  if f['split']=='oracle':
   mode='tiny'if f['input_bytes']<=12 else'reference';c[mode]=native(inp,tag,mode,['--tiny-oracle'if mode=='tiny'else'--small-reference']);row['adaptive_candidate_gap_bytes']=c['adaptive']['bytes']-c[mode]['bytes'];assert row['adaptive_candidate_gap_bytes']>=0
  else:
   for size in [64,256,1024]:c['fixed'+str(size)]=native(inp,tag,'fixed'+str(size),['--fixed',str(size)])
   refs=row['references'];specs=[('zstd19',['/bin/zstd','-q','-19','-T1','-c'],['/bin/zstd','-d','-q','-c']),('xz9e',['/bin/xz','-9e','-T1','-c'],['/bin/xz','-d','-c']),('bzip2_9',['/bin/bzip2','-9','-c'],['/bin/bzip2','-d','-c']),('gzip9',['/bin/gzip','-n','-9','-c'],['/bin/gzip','-d','-c'])]
   for name,en,de in specs:refs[name]=qualified(name,lambda a,en=en:[*en,inp],lambda a,o,de=de:[*de,a],inp,tag,stdout=True)
   cix=ROOT/'benchmark-work/release-d3a2/final/cix'
   for effort,flags in [('default',[]),('best',['--best'])]:refs['cix_'+effort]=qualified('cix_best',lambda a,flags=flags:[cix,*flags,'--threads','1','--memory','1536MiB','-c',inp],lambda a,o:[cix,'-d','-c',a],inp,tag+'-'+effort,stdout=True)
  rows.append(row);save('results.json',rows);print(tag,{k:v['bytes']for k,v in c.items()},{k:v['bytes']for k,v in row['references'].items()},flush=True)
  if len(rows)==9:save('stage2-checkpoint.json',dict(status='verified',rows=9,exact_reference_gaps=[x['adaptive_candidate_gap_bytes']for x in rows]));print('stage2 verified; continuing frozen stage3',flush=True)
 # Actual production fixed-block trace: preserve stderr and freshly decode.
 inp=Path(next(x['fixture']['input']for x in rows if x['fixture']['name']=='development-abrupt'));cix=ROOT/'benchmark-work/release-d3a2/final/cix'
 trace=qualified('cix_best',lambda a:[cix,'--format','cixg2','--stream','--best','--threads','1','--parallelism','candidates','--block-size','1KiB','--memory','512MiB','--explain','-c',inp],lambda a,o:[cix,'-d','-c',a],inp,'production-route-trace',stdout=True);save('production-route-trace.json',trace)
 seed=Path(next(x['candidates']['whole']['archive']for x in rows if x['fixture']['name']=='development-high-entropy'));base=seed.read_bytes();variants={}
 variants['truncated']=base[:-1];variants['trailing']=base+b'\0'
 for name,offset,value in [('source_length',5,4097),('segment_count',9,33),('segment_length',18,0),('payload_length',22,32768)]:
  b=bytearray(base);b[offset:offset+4]=value.to_bytes(4,'little');variants[name]=b
 b=bytearray(base);b[17]=255;variants['route_id']=b;b=bytearray(base);b[13]^=1;variants['source_CRC']=b
 # Reject inner Huffman decoded length before it can request allocation.
 payload=bytearray(19);payload[0]=1;payload[3:11]=(1<<40).to_bytes(8,'little');variants['Huffman_length']=b'NCSC\x01'+struct.pack('<III',1,1,0)+struct.pack('<BII',1,1,len(payload))+payload
 bad=[]
 for name,data in variants.items():
  a=ARC/('bad-'+name+'.arc');o=ARC/('bad-'+name+'.out');a.write_bytes(data);result=call([BIN/'segments','decode',a,o],'bad-'+name,allowed=True);assert result['exit']!=0 and not o.exists();bad.append(dict(name=name,run=result))
 save('malformed.json',bad);save('artifact-binding.json',dict(artifacts={str(q):dict(bytes=q.stat().st_size,sha256=sha(q))for q in sorted(WORK.rglob('*'))if q.is_file()}))
