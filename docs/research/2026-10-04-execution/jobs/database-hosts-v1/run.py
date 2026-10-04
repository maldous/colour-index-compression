import os,json,subprocess
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
w=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1');work=w/'database-hosts-v1';work.mkdir(exist_ok=False)
sdk=w/'sdk-bindings-relocated-cli-bindings-v8';src=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/database-hosts-source-v1');receipt={}
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
   build=work/'wiredtiger-sdk-build';prefix=work/'wiredtiger-prefix'
   run(name,['cmake','-S',w/'wiredtiger-source-v1','-B',build,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_INSTALL_PREFIX='+str(prefix),'-DENABLE_SHARED=ON','-DENABLE_STATIC=OFF','-DENABLE_PYTHON=OFF','-DHAVE_UNITTEST=OFF','-DHAVE_UNITTEST_ASSERTS=OFF','-DENABLE_CPPSUITE=OFF','-DENABLE_MODEL=OFF','-DENABLE_STRICT=OFF','-DENABLE_LZ4=OFF','-DENABLE_SNAPPY=OFF','-DENABLE_ZLIB=OFF','-DENABLE_ZSTD=OFF','-DENABLE_SODIUM=OFF','-DENABLE_IAA=OFF','-DENABLE_S3=OFF','-DENABLE_GCP=OFF','-DENABLE_AZURE=OFF'])
   run(name,['cmake','--build',build,'--target','wiredtiger_shared','-j4'])
   run(name,['cmake','--install',build])
   run(name,['cmake','-S',src/name,'-B',work/name,'-DCIX_NATIVE_INCLUDE_DIR='+str(sdk/'include'),'-DCIX_NATIVE_LIBRARY='+str(sdk/'lib/libcix_native.so'),'-DWIREDTIGER_INCLUDE_DIR='+str(prefix/'include'),'-DWIREDTIGER_LIBRARY='+str(prefix/'lib/libwiredtiger.so'),'-DCIX_WIREDTIGER_BUILD_CONTRACT_TEST=ON'])
   run(name,['cmake','--build',work/name,'-j4'])
   (work/name/'cix-wt-contract-home').mkdir()
   run(name,['ctest','--test-dir',work/name,'--output-on-failure'])
 except Exception as err: print(name,'FAIL',str(err),flush=True)
assert all(v[-1]['returncode']==0 for v in receipt.values())
