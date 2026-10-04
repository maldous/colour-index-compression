import os,json,subprocess
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
w=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1');work=w/'database-hosts-v2';work.mkdir(exist_ok=False)
sdk=w/'sdk-bindings-relocated-cli-bindings-v8';src=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/database-hosts-source-v2');receipt={}
reclaimed=[]
original=sdk/'lib/libcix_native.so'
import hashlib
for n in [3,4,5,6]:
 p=w/f'codec-hosts-v{n}/squash-plugins/cix/libcix_native.so'
 if p.exists() and not p.is_symlink():
  sha=hashlib.sha256(p.read_bytes()).hexdigest()
  assert sha==hashlib.sha256(original.read_bytes()).hexdigest()
  size=p.stat().st_size;p.unlink();p.symlink_to(original)
  reclaimed.append(dict(path=str(p),sha256=sha,bytes=size,symlink=str(original)))
Path('/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/database-hosts-v2/space-receipt.json').write_text(json.dumps(reclaimed,indent=2)+'\n')
def run(name,args):
 p=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True)
 receipt.setdefault(name,[]).append(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
 (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(name,args,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr[-3000:] or p.stdout[-3000:])
for name in ['sevenzip','wiredtiger']:
 try:
  if name=='sevenzip':
   run(name,['cmake','-S',src/name,'-B',work/name,'-DCIX_NATIVE_INCLUDE_DIR='+str(sdk/'include'),'-DCIX_NATIVE_LIBRARY='+str(sdk/'lib/libcix_native.so'),'-DCIX_7ZIP_SDK_ROOT='+str(w/'sevenzip-source-v1'),'-DCIX_7ZIP_SDK_ARCHIVE_SHA256=9cbde5099c6deb73691b0579063da5827522ccbbcba3f0020fd04e8c8c16c0d4','-DCIX_7ZIP_BUILD_CONTRACT=ON'])
   run(name,['cmake','--build',work/name,'-j4'])
   run(name,[work/name/'cix_7zip_contract'])
  else:
   build=w/'database-hosts-v1/wiredtiger-sdk-build';prefix=w/'database-hosts-v1/wiredtiger-prefix'
   run(name,['cmake','--build',build,'--target','wt','-j4'])
   run(name,['cmake','--install',build])
   run(name,['cmake','-S',src/name,'-B',work/name,'-DCIX_NATIVE_INCLUDE_DIR='+str(sdk/'include'),'-DCIX_NATIVE_LIBRARY='+str(sdk/'lib/libcix_native.so'),'-DWIREDTIGER_INCLUDE_DIR='+str(prefix/'include'),'-DWIREDTIGER_LIBRARY='+str(prefix/'lib/libwiredtiger.so'),'-DCIX_WIREDTIGER_BUILD_CONTRACT_TEST=ON'])
   run(name,['cmake','--build',work/name,'-j4'])
   (work/name/'cix-wt-contract-home').mkdir()
   run(name,['ctest','--test-dir',work/name,'--output-on-failure'])
 except Exception as err: print(name,'FAIL',str(err),flush=True)
assert all(v[-1]['returncode']==0 for v in receipt.values())
