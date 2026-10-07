from pathlib import Path
import json,hashlib,importlib.util
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/lane-evidence';WORK=ROOT/'benchmark-work/segmentation-lanes';OLD=AREA.parent/'evidence';spec=importlib.util.spec_from_file_location('oldfixtures',OLD/'fixtures.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[]
 for old in json.loads((OLD/'results.json').read_text()):
  if old['fixture']['split']=='oracle'and old['fixture']['name']not in['empty','tiny-one','tiny-changing']:continue
  rows.append(dict(old['fixture'],previous=old))
 for width,count,seed in [(4,367,1201),(5,293,1203)]:
  values=p.draw(seed,count);noise=p.draw(seed+1,width*count);data=bytes(noise[i*width+k]if i%19==0 else((values[i]+3*k)&255)if k<width-1 else 0 for i in range(count)for k in range(width));data+=p.draw(seed+2,width-2);name='new-held-out-stride'+str(width);q=WORK/'inputs'/(name+'.bin');q.write_bytes(data);rows.append(dict(name=name,split='new-held-out',input=str(q),input_bytes=len(data),input_sha256=hashlib.sha256(data).hexdigest(),generator=dict(width=width,count=count,seed=seed,violations='every19throw',partial_row_bytes=width-2),diagnostic='not supplied to encoder'))
 data=p.draw(1205,1491);q=WORK/'inputs'/'new-held-out-absent.bin';q.write_bytes(data);rows.append(dict(name='new-held-out-absent',split='new-held-out',input=str(q),input_bytes=len(data),input_sha256=hashlib.sha256(data).hexdigest(),generator=dict(seed=1205,length=1491)))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'inputs',flush=True)
