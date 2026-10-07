#!/usr/bin/env python3
"""Stage the integrated runtime closure; execute only from the root scheduler."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, shutil, subprocess, sys, sysconfig
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=Path('/home/user/src/cix-0.1-artifacts/final/bin')
NATIVE_LIBRARY = 'libcix_native.so'
PAQ={
 'v215':ROOT/'benchmark-work/references/paq8px-v215/build-local/paq8px',
 'v216':ROOT/'benchmark-work/references/paq8px-v216/build-local/paq8px',
 'joint-discount':ROOT/'benchmark-work/references/paq8px-cix-joint-discount/build-local/paq8px',
 'store-state':ROOT/'benchmark-work/references/paq8px-cix-store-state/build-local/paq8px',
}
def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def copy_file(source:Path,dest:Path):
 if not source.is_file():raise SystemExit(f'missing staging dependency: {source}')
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
def ignore_generated(directory,names):
 return {name for name in names if name == '__pycache__' or name.endswith('.pyc')}
def elf_dependencies(path: Path) -> dict:
 output=subprocess.run(['ldd',str(path)],text=True,capture_output=True,check=False).stdout
 libraries=[]
 for line in output.splitlines():
  candidate=line.split('=>',1)[-1].strip().split(' ',1)[0]
  library=Path(candidate)
  if library.is_absolute() and library.is_file(): libraries.append({'path':str(library),'sha256':digest(library)})
 return {'ldd_output':output,'resolved_libraries':libraries}
def package_version(name: str) -> str | None:
 try:return importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:return None
def elf_files(root: Path) -> list[Path]:
 result=[]
 for path in sorted(root.rglob('*')):
  if path.is_file():
   with path.open('rb') as handle:
    if handle.read(4) == b'\x7fELF':result.append(path)
 return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path,required=True);p.add_argument('--native-bin-dir',type=Path,default=ARTIFACT);p.add_argument('--execute',action='store_true');a=p.parse_args()
 dst=a.destination.resolve()
 if not a.execute: print(f'plan: stage integrated runtime into {dst}; pass --execute under scheduler');return
 if dst.exists():raise SystemExit(f'refusing to overwrite destination: {dst}')
 libexec=dst/'libexec/cix'; bindir=dst/'bin'; pyroot=dst/'python'; site=pyroot/'site-packages'
 native=a.native_bin_dir.resolve()
 for name,target in [('cix','cix-native'),('uncix','uncix-native'),('cixcat','cixcat-native'),(NATIVE_LIBRARY,NATIVE_LIBRARY)]:copy_file(native/name,libexec/target)
 for name,path in PAQ.items():copy_file(path,libexec/f'paq8px-{name}')
 shutil.copytree(ROOT/'runtime/cix_runtime',site/'cix_runtime',ignore=ignore_generated)
 venv=ROOT/'.venv/lib/python3.12/site-packages'
 for name in ('numpy','numpy.libs','numpy-2.5.3.dist-info','imagecodecs','imagecodecs.libs','imagecodecs-2026.8.16.dist-info','_brotli.cpython-312-x86_64-linux-gnu.so','brotli.py','brotli-1.2.0.dist-info'):
  source=venv/name
  if source.is_dir(): shutil.copytree(source,site/name,ignore=ignore_generated)
  else: copy_file(source,site/name)
 wrapper='#!/bin/sh\nroot="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"\nunset PYTHONHOME\nexport PYTHONPATH="$root/python/site-packages"\nexport LD_LIBRARY_PATH="$root/python/site-packages/imagecodecs.libs"\nexport CIX_RUNTIME_PROGRAM="$(basename -- "$0")"\nexport CIX_BACKEND_ROOT="$root/libexec/cix"\nexec "$root/python/bin/python3" -m cix_runtime.cli "$@"\n'
 bindir.mkdir(parents=True);(bindir/'cix').write_text(wrapper);(bindir/'cix').chmod(0o755)
 for name in ('uncix','cixcat'):(bindir/name).write_text(wrapper);(bindir/name).chmod(0o755)
 (pyroot/'bin').mkdir(parents=True);shutil.copy2(ROOT/'.venv/bin/python3',pyroot/'bin/python3')
 staged_elfs=elf_files(dst)
 receipt={'schema':'cix-integrated-runtime-stage-v1','destination':str(dst),'native_bin_dir':str(native),'files':{str(p.relative_to(dst)):digest(p) for p in sorted(dst.rglob('*')) if p.is_file()},'external_dependencies':{'elfs':{str(path.relative_to(dst)):elf_dependencies(path) for path in staged_elfs},'python':{'executable':sys.executable,'version':sys.version,'stdlib':sysconfig.get_path('stdlib'),'host_pinned_limitation':'The staged interpreter and standard library remain host-pinned; this is a qualified-host stage, not a portable Python distribution.'},'packages':{'numpy':package_version('numpy'),'imagecodecs':package_version('imagecodecs'),'Brotli':package_version('Brotli')}}}
 (dst/'runtime-stage.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
