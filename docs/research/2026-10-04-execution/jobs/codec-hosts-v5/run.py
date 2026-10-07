import os,subprocess,json
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
w=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-v5');w.mkdir(exist_ok=False)
r={'components':{}}
def run(name,args,env={}):
 p=subprocess.run(list(map(str,args)),env={**os.environ,**env},capture_output=True,text=True,cwd=w)
 r['components'].setdefault(name,[]).append(dict(argv=list(map(str,args)),env_extra=env,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
 (w/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
 print(name,args,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr[-4000:] or p.stdout[-4000:])
env={'PKG_CONFIG_PATH':'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix/lib/pkgconfig','LD_LIBRARY_PATH':'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix/lib','SQUASH_SOURCE_REVISION':'713eeca85cccadde39bf57f8b59ea663a085a347','CIX_NATIVE_LIBRARY':'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8/lib/libcix_native.so','CIX_INCLUDE_DIR':'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8/include','SQUASH_PLUGIN_ROOT':str(w/'squash-plugins')}
run('squash',['sh','/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-source-v5/packaging/squash/build-plugin.sh'],env)
run('squash',['cc','-std=c11','-Wall','-Wextra','-Werror','-I/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix/include/squash-0.8','/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-source-v5/packaging/squash/contract.c','-L/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix/lib','-lsquash0.8','-o',w/'squash-contract'],env)
run('squash',[w/'squash-contract',w/'squash-plugins'],env)
