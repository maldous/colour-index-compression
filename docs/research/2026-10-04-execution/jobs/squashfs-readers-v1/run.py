import hashlib,json,os,shutil,subprocess
from pathlib import Path

assert os.environ.get('CIX_RELEASE_LEASE')=='1'
repo=Path(__file__).resolve().parents[5]; work=repo/'benchmark-work/native-rc-check-v1'; out=work/'squashfs-readers-v1'; out.mkdir()
fixture=work/'squashfs-host-v3/fixture'; adapters=repo/'rust/cix-native/adapters/squashfs/userspace'; rows=[]
def run(argv,cwd,env=None):
 p=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,capture_output=True,text=True,timeout=600)
 rows.append({'argv':[str(x) for x in argv],'cwd':str(cwd),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
 if p.returncode: raise RuntimeError(p.stderr[-5000:] or p.stdout[-5000:])
def replace(makefile,old,new):
 s=makefile.read_text(); assert old in s,old; makefile.write_text(s.replace(old,new))
def tree_receipt(root):
 result={}
 for p in sorted(root.rglob('*')):
  if p.is_file(): result[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 return result
expected=json.loads((fixture/'receipt.json').read_text())['entries']
for key,value in expected.items(): assert hashlib.sha256((fixture/'root'/key).read_bytes()).hexdigest()==value['sha256']
# Build copies are disposable. Vendor source paths and bytes are never changed.
ngsrc=work/'sqfsng-source-v1'; fusrc=work/'squashfuse-source-v1'
ngcopy=out/'sqfsng-vendor'; fucopy=out/'squashfuse-vendor'
shutil.copytree(ngsrc,ngcopy); shutil.copytree(fusrc,fucopy)
env={**os.environ,'CFLAGS':'-O2 -Wall -Wextra -I'+str(adapters/'include')+' -I'+str(repo/'rust/cix-native/adapters/squashfs/profile/include'),
 'CPPFLAGS':'-DCIX_SQFSNG_COMPRESSOR_SOURCE=\\"'+str(ngcopy/'lib/sqfs/comp/compressor.c')+'\\" -DCIX_SQFSNG_READ_SUPER_SOURCE=\\"'+str(ngcopy/'lib/sqfs/read_super.c')+'\\" -DCIX_SQUASHFUSE_DECOMPRESS_SOURCE=\\"'+str(fucopy/'decompress.c')+'\\"'}
ngbuild=out/'sqfsng-build'; ngbuild.mkdir(); run([ngcopy/'configure','--disable-shared'],ngbuild,env)
replace(ngbuild/'Makefile','lib/sqfs/read_super.c',str(adapters/'libsquashfs/cix_sqfsng_read_super.c'))
replace(ngbuild/'Makefile','lib/sqfs/comp/compressor.c',str(adapters/'libsquashfs/cix_sqfsng_compressor.c'))
run(['make','-j4','bin/rdsquashfs/rdsquashfs'],ngbuild,env)
fubuild=out/'squashfuse-build'; fubuild.mkdir(); run([fucopy/'configure','--disable-fuse','--enable-demo'],fubuild,env)
replace(fubuild/'Makefile','decompress.c',str(adapters/'squashfuse/cix_squashfuse_decode.c'))
run(['make','-j4','squashfuse_extract'],fubuild,env)
for label,tool,args in [('sqfsng',ngbuild/'bin/rdsquashfs/rdsquashfs',['-d']),('squashfuse',fubuild/'squashfuse_extract',[])]:
 dest=out/(label+'-out'); run([tool,*args,fixture/'image.sqfs',dest],out,env); assert tree_receipt(dest)=={k:v['sha256'] for k,v in expected.items()}
 for bad in ['unknown-method.sqfs','malformed-inode-profile-version.sqfs']:
  p=subprocess.run([str(tool),*args,str(fixture/bad),str(out/(label+'-'+bad))],cwd=out,env=env,capture_output=True,text=True,timeout=120); rows.append({'negative':[label,bad],'returncode':p.returncode}); assert p.returncode!=0
shutil.rmtree(ngbuild); shutil.rmtree(fubuild)
