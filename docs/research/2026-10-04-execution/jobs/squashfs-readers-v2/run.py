import hashlib,json,os,shutil,subprocess
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
r=Path(__file__).resolve().parents[5];w=r/'benchmark-work/native-rc-check-v1';o=w/'squashfs-readers-v2';o.mkdir();f=w/'squashfs-host-v3/fixture';a=o/'adapters';p=o/'profile';rows=[]
def run(x,cwd,e):
 q=subprocess.run(list(map(str,x)),cwd=cwd,env=e,capture_output=True,text=True,timeout=600);rows.append({'argv':list(map(str,x)),'rc':q.returncode,'out':q.stdout,'err':q.stderr});(o/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n');
 if q.returncode:raise RuntimeError(q.stderr[-4000:])
def subst(path,old,new):
 s=path.read_text();assert old in s;path.write_text(s.replace(old,new))
def hashes(root):return {x.relative_to(root).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(root.rglob('*')) if x.is_file()}
shutil.copytree(r/'rust/cix-native/adapters/squashfs/userspace',a);shutil.copytree(r/'rust/cix-native/adapters/squashfs/profile',p)
ng=o/'sqfsng-vendor';fu=o/'squashfuse-vendor';shutil.copytree(w/'sqfsng-source-v1',ng);shutil.copytree(w/'squashfuse-source-v1',fu)
e={**os.environ,'CFLAGS':'-O2 -Wall -Wextra -I'+str(a/'include')+' -I'+str(p/'include'),'CPPFLAGS':'-DCIX_SQFSNG_COMPRESSOR_SOURCE=\\"'+str(ng/'lib/sqfs/comp/compressor.c')+'\\" -DCIX_SQFSNG_READ_SUPER_SOURCE=\\"'+str(ng/'lib/sqfs/read_super.c')+'\\" -DCIX_SQUASHFUSE_DECOMPRESS_SOURCE=\\"'+str(fu/'decompress.c')+'\\"'}
nb=o/'ng-build';nb.mkdir();run([ng/'autogen.sh'],ng,e);run([ng/'configure','--disable-shared'],nb,e);subst(nb/'Makefile','lib/sqfs/read_super.c',str(a/'libsquashfs/cix_sqfsng_read_super.c'));subst(nb/'Makefile','lib/sqfs/comp/compressor.c',str(a/'libsquashfs/cix_sqfsng_compressor.c'));run(['make','-j4','bin/rdsquashfs/rdsquashfs'],nb,e)
fb=o/'fu-build';fb.mkdir();run([fu/'autogen.sh'],fu,e);run([fu/'configure','--disable-fuse','--enable-demo'],fb,e);subst(fb/'Makefile','decompress.c',str(a/'squashfuse/cix_squashfuse_decode.c'));run(['make','-j4','squashfuse_extract'],fb,e)
expect={k:v['sha256'] for k,v in json.loads((f/'receipt.json').read_text())['entries'].items()}
for name,cmd in [('ng',[nb/'bin/rdsquashfs/rdsquashfs','-X','-u','/','-p']),('fu',[fb/'squashfuse_extract',f/'image.sqfs'])]:
 dest=o/(name+'-out');run([*cmd,dest,f/'image.sqfs'] if name=='ng' else [*cmd,dest],o,e);assert hashes(dest)==expect
 for bad in ('unknown-method.sqfs','malformed-inode-profile-version.sqfs'):
  negative=o/(name+'-'+bad);args=[str(cmd[0]),'-X','-u','/','-p',str(negative),str(f/bad)] if name=='ng' else [str(cmd[0]),str(f/bad),str(negative)]
  q=subprocess.run(args,cwd=o,env=e,capture_output=True);assert q.returncode!=0
shutil.rmtree(nb);shutil.rmtree(fb)
