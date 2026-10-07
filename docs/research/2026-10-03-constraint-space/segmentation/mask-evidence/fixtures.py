from pathlib import Path
import json,hashlib,importlib.util
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/segmentation/mask-evidence';WORK=ROOT/'benchmark-work/segmentation-masks';OLD=AREA.parent/'lane-evidence';spec=importlib.util.spec_from_file_location('oldfixtures',AREA.parent/'evidence/fixtures.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
if __name__=='__main__':
 (WORK/'inputs').mkdir(parents=True,exist_ok=True);rows=[];names=['empty','tiny-one','tiny-changing','development-interleaved-noise','held-out-interleaved-noise','new-held-out-stride4','new-held-out-stride5','new-held-out-absent','development-A-B-A']
 for old in json.loads((OLD/'results.json').read_text()):
  if old['fixture']['name']in names:rows.append(dict(old['fixture'],previous=old))
 for width,count,seed in[(3,487,1401),(4,367,1403),(5,293,1405)]:
  values=p.draw(seed,count);noise=p.draw(seed+1,width*count);data=bytes(noise[i*width+k]if i%23==0 else((values[i]+5*k)&255)if k<width-1 else 0 for i in range(count)for k in range(width))+p.draw(seed+2,width-2);name='fresh-held-mask-width'+str(width);q=WORK/'inputs'/(name+'.bin');q.write_bytes(data);rows.append(dict(name=name,split='new-held-out',input=str(q),input_bytes=len(data),input_sha256=hashlib.sha256(data).hexdigest(),generator=dict(width=width,count=count,seed=seed,noise_period=23,partial_row_bytes=width-2),diagnostic='not passed to encoder'))
 (AREA/'input-freeze.json').write_text(json.dumps(rows,indent=2)+'\n');print('froze',len(rows),'inputs',flush=True)
