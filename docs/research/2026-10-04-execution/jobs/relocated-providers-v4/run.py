import subprocess
subprocess.run(['python3', '/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/relocated-providers-v4/check.py', '--runtime', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/runtime-closure-v2/relocated/usr', '--workspace', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/relocated-providers-v4', '--jxl-header', '/home/user/src/colour-index-compression/rust/cix-native/codecs/jxl/cix_jxl_bridge.h', '--paq-level=-1', '--paq-memory', '1073741824'],check=True)
from pathlib import Path
import json
runtime=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/runtime-closure-v2/relocated/usr')
source=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/relocated-providers-v1/v215.encoded')
records=[]
for variant in ['v215','v216','joint-discount','store-state']:
 dst=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/relocated-providers-v4')/(variant+'-must-not-exist')
 cmd=[str(runtime/'bin/cix'),'--internal-paq-worker-v1',variant,'decode',str(runtime/'lib/cix'),str(source),str(dst),'1073741824','1048576','-1','1','none']
 p=subprocess.run(cmd,capture_output=True,text=True)
 record={'variant':variant,'argv':cmd,'returncode':p.returncode,'stderr':p.stderr,'output_exists':dst.exists()}
 records.append(record)
 Path('/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/relocated-providers-v4/guard-receipt.json').write_text(json.dumps(records,indent=2)+'\n')
 assert p.returncode==1 and 'level-0' in p.stderr and not dst.exists(),record
