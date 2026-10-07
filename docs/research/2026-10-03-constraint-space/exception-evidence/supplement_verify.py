from pathlib import Path
import json,subprocess,time,hashlib
from oracle import rex
ROOT=Path('/home/user/src/colour-index-compression');AREA=ROOT/'docs/research/2026-10-03-constraint-space/exception-evidence';WORK=ROOT/'benchmark-work/record-exceptions';rows=[]
for arc in sorted((WORK/'benchmark-work/record-exceptions/supplement').glob('*.rex')):
 inp=arc.with_suffix('.input');out=arc.with_suffix('.restored');start=time.monotonic();cp=subprocess.run(['/usr/bin/time','-v','-o',str(AREA/'raw'/(arc.stem+'-supplement-decode.time')),str(WORK/'build/rex'),'decode',str(arc),str(out)],capture_output=True,timeout=10);assert cp.returncode==0 and out.read_bytes()==inp.read_bytes()
 rows.append(dict(name=arc.stem,source_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),archive_sha256=hashlib.sha256(arc.read_bytes()).hexdigest(),restored_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),decode_wall_seconds=time.monotonic()-start,oracle=rex(arc,inp.read_bytes())))
assert len(rows)==7
(AREA/'supplement-results.json').write_text(json.dumps(rows,indent=2)+'\n')
(AREA/'supplement-artifact-binding.json').write_text(json.dumps(dict(artifacts={str(p):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sorted(WORK.rglob('*'))if p.is_file()}),indent=2)+'\n')
print('qualified',len(rows),'fresh-process supplement restores and independent ranks',flush=True)
