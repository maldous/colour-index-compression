"""One bounded public-artifact derivation. No application, tracker or credentials."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess
base=Path('/home/user/src/cix-approved-migration')
old=base/'runtime-cix243-v1';new=base/'runtime-cix243-v2'
tool=base/'successor-preparation/tools/extracted/usr/bin/patchelf'
old_loader=Path('/tmp/libc-musl-71c35316aff45bbfd243d8eb9bfc4a58b6eb97cee09514cd2030e145b68107fb.so')
loader_sha='71c35316aff45bbfd243d8eb9bfc4a58b6eb97cee09514cd2030e145b68107fb'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cg=next(x.split(':',2)[2] for x in Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::'))
assert cg=='/cix.slice/cix-bau139.slice/cix244-runtime-relocate-v1.service'
control=Path('/sys/fs/cgroup')/cg.lstrip('/')
assert int((control/'memory.max').read_text())<=2000000000
assert (control/'memory.swap.max').read_text().strip()=='0'
assert os.sched_getaffinity(0)=={0}
assert sha(old_loader)==loader_sha
receipt=json.loads((old/'artifact-derivation.json').read_text())
for rel,digest in receipt['public_closure_sha256'].items():assert sha(old/rel)==digest,rel
manifest=json.loads((old/'overlay/beam-manifest.json').read_text())
for unit in manifest['units']:
 for artifact in unit['modules']:assert sha(old/artifact['path'])==artifact['sha256']
new.mkdir(mode=0o700,exist_ok=False)
inputs={}
for subtree in ['bin','lib','erts-16.4','releases','overlay']:
 for source in sorted((old/subtree).rglob('*')):
  if not source.is_file():continue
  assert not source.is_symlink() and source.resolve().is_relative_to(old)
  rel=source.relative_to(old);dest=new/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);inputs[str(rel)]=sha(source);assert sha(dest)==inputs[str(rel)]
for name in ['bootstrap.exs','launch.sh','launch.vm.args']:
 shutil.copy2(old/name,new/name);inputs[name]=sha(old/name)
# Materialize the unchanged official launcher template for the successor root.
(new/'erts-16.4/bin/erl').write_bytes((new/'erts-16.4/bin/erl.src').read_bytes().replace(b'%FINAL_ROOTDIR%',str(new).encode()))
(new/'erts-16.4/bin/erl').chmod(0o700)
loader=new/'libexec/ld-musl.so';loader.parent.mkdir();shutil.copy2(old_loader,loader);loader.chmod(0o700);assert sha(loader)==loader_sha

def interpreter(p):
 b=p.read_bytes()
 if b[:4]!=b'\x7fELF':return None
 endian='<' if b[5]==1 else '>' if b[5]==2 else None
 assert endian
 if b[4]==2:offset=struct.unpack_from(endian+'Q',b,32)[0];size,count=struct.unpack_from(endian+'HH',b,54);poff,pfilesz=8,32;number='Q'
 elif b[4]==1:offset=struct.unpack_from(endian+'I',b,28)[0];size,count=struct.unpack_from(endian+'HH',b,42);poff,pfilesz=4,16;number='I'
 else:raise RuntimeError('Unsupported ELF class')
 assert count!=65535
 for i in range(count):
  ph=offset+i*size
  if struct.unpack_from(endian+'I',b,ph)[0]==3:
   start=struct.unpack_from(endian+number,b,ph+poff)[0];length=struct.unpack_from(endian+number,b,ph+pfilesz)[0]
   return b[start:start+length].rstrip(b'\0').decode()
 return ''
changed=[];elf_inventory=[]
version=subprocess.check_output([str(tool),'--version'],text=True).strip()
for p in sorted(new.rglob('*')):
 if not p.is_file():continue
 value=interpreter(p)
 if value is None:continue
 rel=str(p.relative_to(new));before=sha(p)
 if value==str(old_loader):
  before_needed=subprocess.check_output([str(tool),'--print-needed',str(p)])
  before_rpath=subprocess.check_output([str(tool),'--print-rpath',str(p)])
  subprocess.run([str(tool),'--set-interpreter',str(loader),str(p)],check=True)
  assert interpreter(p)==str(loader)
  assert subprocess.check_output([str(tool),'--print-needed',str(p)])==before_needed
  assert subprocess.check_output([str(tool),'--print-rpath',str(p)])==before_rpath
  changed.append({'path':rel,'before_sha256':before,'after_sha256':sha(p),'old_interpreter':value,'new_interpreter':str(loader),'needed_rpath_unchanged':True})
 else:assert not value.startswith('/tmp/'),'Unresolved temporary interpreter'
 elf_inventory.append({'path':rel,'interpreter':interpreter(p),'sha256':sha(p)})
assert changed
for unit in manifest['units']:
 for artifact in unit['modules']:assert sha(new/artifact['path'])==artifact['sha256']
result={'status':'DERIVED_NOT_ACTIVATED','source_runtime':str(old),'target_runtime':str(new),'source_public_inputs':inputs,'loader_sha256':loader_sha,'loader_path':str(loader),'editor_version':version,'editor_sha256':sha(tool),'official_package_sha256':'962a43e33cd56061522554898557a038ccbb8aa4e1e0f421b2d6f6adf1f80c60','changed_elfs':changed,'all_elf_inventory':elf_inventory,'beam_pins_unchanged':True,'services_started':False,'tracker_contacted':False,'credentials_read':False,'control_group':cg,'memory_max_actual':int((control/'memory.max').read_text()),'memory_peak':int((control/'memory.peak').read_text()),'copied_public_bytes':sum(p.stat().st_size for p in new.rglob('*') if p.is_file())}
(new/'relocation-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'changed_elf_count':len(changed),'elf_count':len(elf_inventory),'public_bytes':result['copied_public_bytes'],'memory_peak':result['memory_peak']}))
