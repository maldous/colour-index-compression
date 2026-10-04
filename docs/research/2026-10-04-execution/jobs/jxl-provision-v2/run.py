import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/user/src/colour-index-compression')
dest=root/'benchmark-work/references/libjxl-v0.12.0'
if dest.exists(): raise SystemExit('Refusing existing source destination')
subprocess.run(['git','clone','--depth','1','--branch','v0.12.0','--recurse-submodules','--shallow-submodules','https://github.com/libjxl/libjxl.git',str(dest)],check=True)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=dest,text=True).strip()
if head != 'a7a9c787341cf703dede03c2009fa460cae5e5df': raise SystemExit('Pinned release identity mismatch')
submodules=subprocess.check_output(['git','submodule','status','--recursive'],cwd=dest,text=True)
files={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.rglob('*')) if p.is_file() and '.git' not in p.relative_to(dest).parts}
receipt={'source':str(dest),'head':head,'submodule_status':submodules,'sha256':files,'source_bytes':sum(p.stat().st_size for p in dest.rglob('*') if p.is_file() and '.git' not in p.relative_to(dest).parts)}
Path(__file__).with_name('source.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Pinned libjxl closure',head,len(files),'files',receipt['source_bytes'],'bytes',flush=True)
