from pathlib import Path
import importlib.util,json,os
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/mask-evidence/contiguous-controls';WORK=ROOT/'benchmark-work/mask-contiguous-controls';PREV=AREA.parent;SRC=PREV.parent/'evidence'
spec=importlib.util.spec_from_file_location('seg_control',SRC/'run.py');n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n);n.p.AREA=AREA;n.p.WORK=WORK;n.p.RAW=AREA/'raw';n.p.ARC=WORK/'archives';n.RAW=n.p.RAW;n.BIN=ROOT/'benchmark-work/segmentation-reference/build'
if __name__=='__main__':
 assert os.environ.get('CIX_MASK_BASELINE_LEASE')=='1';n.RAW.mkdir(exist_ok=True);n.p.ARC.mkdir(parents=True,exist_ok=True);rows=[]
 for old in json.loads((PREV/'results.json').read_text()):
  f=old['fixture']
  if not f['name'].startswith('fresh-held-mask-'):continue
  inp=Path(f['input']);assert n.sha(inp)==f['input_sha256'];c={};row=dict(fixture=f,candidates=c)
  for name,args in [('adaptive',['--adaptive']),('fixed64',['--fixed','64']),('fixed256',['--fixed','256']),('fixed1024',['--fixed','1024'])]:c[name]=n.native(inp,f['name'],name,args)
  rows.append(row);n.save('results.json',rows);print(f['name'],{k:v['bytes']for k,v in c.items()},flush=True)
 n.save('artifact-binding.json',dict(artifacts={str(q):dict(bytes=q.stat().st_size,sha256=n.sha(q))for q in sorted(WORK.rglob('*'))if q.is_file()}))
