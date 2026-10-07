#!/usr/bin/env python3
"""Bounded ARM64 ABI checks for the remaining CIX PAQ bridge variants."""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess
from pathlib import Path

AREA=Path(__file__).resolve().parent; ROOT=AREA.parents[4]; PARENT=ROOT/'benchmark-work/native-rc-check-v1'
WORK=PARENT/'platform-linux-arm64-paq-variants-v1'; CAP=180_000_000; SHARED=4_000_000_000
RECEIPT=Path(os.environ.get('CIX_ARM64_TOOLCHAIN_RECEIPT', PARENT/'platform-linux-arm64-user-toolchain-v3/receipt.json'))
VARIANTS=(
 ('v216','v216','paq-v216-qualification-v1','cix_paq_v216','vendor/paq/v216'),
 ('joint_discount','joint_discount','paq-joint-discount-qualification-v1','cix_paq_joint_discount','vendor/paq/joint-discount'),
 ('store_state','store_state','paq-store-state-qualification-v1','cix_paq_store_state','vendor/paq/store-state'),
)
def digest(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def used(p): return int(subprocess.run(['du','-sx','-B1',str(p)],text=True,stdout=subprocess.PIPE,check=True).stdout.split()[0])
def cap():
 n=used(WORK)
 if n>CAP:raise RuntimeError(f'local cap exceeded: {n}>{CAP}')
 return n
def command(receipt,name,argv,env=None,timeout=600):
 logs=WORK/'logs';logs.mkdir(exist_ok=True);out=logs/(name+'.stdout.log');err=logs/(name+'.stderr.log')
 try:r=subprocess.run([str(x) for x in argv],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=timeout)
 except subprocess.TimeoutExpired as e:
  out.write_bytes(e.stdout or b'');err.write_bytes(e.stderr or b'');receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'returncode':None,'timeout':True,'stdout':str(out),'stderr':str(err)});raise
 out.write_bytes(r.stdout);err.write_bytes(r.stderr);receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'returncode':r.returncode,'timeout':False,'stdout':str(out),'stderr':str(err)})
 if r.returncode:raise RuntimeError(f'{name} exit {r.returncode}')
 return r.stdout.decode('utf-8','replace')
def maps(root,expect):
 actual={k:digest(root/k) for k in expect}
 if actual!=expect:raise RuntimeError(f'identity mismatch under {root}')
 return actual
def harness(header,symbol,version):
 return f'''#include "{header}"\n#include <cstdio>\n#include <vector>\nint main(int n,char**v){{if(n<4)return 90;std::vector<const char*>a; a.push_back("arm-variant-probe");for(int i=2;i<n;i++)a.push_back(v[i]);char e[512]={{}};int s={symbol}_process((int)a.size(),a.data(),v[1],e,sizeof e);if(s){{std::fprintf(stderr,"CIX_BRIDGE_STATUS=%d %s\\n",s,e);return s;}}std::fprintf(stderr,"CIX_BRIDGE_OK %s\\n",{version}_bridge_version());return 0;}}\n'''
def main():
 if os.environ.get('CIX_RELEASE_LEASE')!='1':raise RuntimeError('root scheduler lease required')
 if WORK.exists():raise RuntimeError('refusing reused work')
 before=used(PARENT) if PARENT.exists() else 0
 if before+CAP>SHARED:raise RuntimeError('shared work admission fails')
 if not RECEIPT.is_file() or not RECEIPT.is_relative_to(PARENT):raise RuntimeError('toolchain receipt outside shared work')
 tr=json.loads(RECEIPT.read_text()); prefix=Path(tr.get('toolchain_prefix',''));hostlib=Path(tr.get('host_library_path',''))
 if tr.get('status')!='pass' or not prefix.is_dir() or not hostlib.is_dir() or not prefix.is_relative_to(PARENT) or not hostlib.is_relative_to(PARENT):raise RuntimeError('toolchain v3 receipt/prefix invalid')
 cc=prefix/'usr/bin/aarch64-linux-gnu-g++';qemu=prefix/'usr/bin/qemu-aarch64-static';target=prefix/'usr/aarch64-linux-gnu';bindir=target/'bin'
 if not cc.is_file() or not qemu.is_file() or not bindir.is_dir() or tr.get('relocated_compiler_sha256')!=digest(cc) or tr.get('relocated_qemu_sha256')!=digest(qemu):raise RuntimeError('toolchain identity mismatch')
 contract=ROOT/'rust/cix-native/src/paq_bridge.rs'; contract_before=digest(contract)
 hostenv={'PATH':'/usr/bin:/bin','LC_ALL':'C','OMP_NUM_THREADS':'1','LD_LIBRARY_PATH':str(hostlib)}; qenv={'PATH':'/usr/bin:/bin','LC_ALL':'C','OMP_NUM_THREADS':'1','LD_LIBRARY_PATH':''}
 WORK.mkdir(parents=True); rec={'schema':'cix-platform-linux-arm64-paq-variants-v1','status':'fail','commands':[],'shared_before':before,'local_cap':CAP,'toolchain_receipt':digest(RECEIPT),'compiler':digest(cc),'qemu':digest(qemu),'full_engine_contract_before':contract_before,'variants':{}}
 try:
  fixture=(b'CIX ARM64 remaining PAQ variants\n'*64)+bytes(range(256))*8
  for name,dirn,qual,sym,descriptor in VARIANTS:
   if descriptor not in contract.read_text() or sym+'_process' not in contract.read_text():raise RuntimeError(f'full-engine descriptor absent: {name}')
   job=ROOT/'docs/research/2026-10-04-native-rc/jobs'/qual; cfg=json.loads((job/'config.json').read_text()); src=json.loads((job/'source.json').read_text())
   vendor=Path(cfg['vendor']); vendor_before=maps(vendor,src['vendor']['files']); xbuild=Path(cfg['build']); xlib=xbuild/f'lib{sym}_bridge.so'; xprobe=xbuild/'paq_abi_probe'; summary=json.loads((job/'raw/qualification.json').read_text())
   if summary.get('status')!='component qualification passed; not full CIX worker integration' or digest(xlib)!=summary['bridge_sha256'] or digest(xprobe)!=summary['probe_sha256']:raise RuntimeError(f'qualified x64 identity mismatch: {name}')
   bridge_src=ROOT/'rust/cix-native/codecs/paq'/dirn; bridge=WORK/(name+'-bridge'); shutil.copytree(bridge_src,bridge)
   bh={p.name:digest(p) for p in bridge.iterdir() if p.is_file()}; build=WORK/(name+'-build')
   command(rec,name+'-configure',['cmake','-S',bridge,'-B',build,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_SYSTEM_NAME=Linux','-DCMAKE_SYSTEM_PROCESSOR=aarch64',f'-DCMAKE_C_COMPILER={prefix}/usr/bin/aarch64-linux-gnu-gcc',f'-DCMAKE_CXX_COMPILER={cc}',f'-DCMAKE_C_FLAGS_INIT=-B{bindir}',f'-DCMAKE_CXX_FLAGS_INIT=-B{bindir}',f'-DCMAKE_SYSROOT={prefix}',f'-DCMAKE_FIND_ROOT_PATH={prefix}','-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER','-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY','-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY',f'-DCIX_PAQ_SOURCE_ROOT={vendor}'],hostenv)
   command(rec,name+'-build',['cmake','--build',build,'--parallel','4'],hostenv);cap()
   lib=build/f'lib{sym}_bridge.so'; probe=WORK/(name+'-probe'); shutil.copy2(lib,WORK/lib.name); hp=WORK/(name+'-probe.cpp'); hp.write_text(harness(f'paq_{name}_bridge.h',sym,sym))
   command(rec,name+'-probe-compile',[cc,f'--sysroot={prefix}','-B',bindir,'-std=c++17','-O2',hp,f'-I{bridge}',f'-L{build}','-Wl,-rpath,$ORIGIN',f'-l{sym}_bridge','-o',probe],hostenv)
   ph=command(rec,name+'-headers',['readelf','-l',probe]);m=re.search(r'Requesting program interpreter: ([^]]+)',ph)
   if not m or not (target/m.group(1).lstrip('/')).is_file():raise RuntimeError(f'ARM runtime root invalid: {name}')
   fx=WORK/(name+'-fixtures');fx.mkdir(); inp=fx/'in';inp.write_bytes(fixture);aa=fx/'arm.paq';ao=fx/'arm.out';xa=fx/'x64.paq';xo=fx/'x64.out';back=fx/'arm-from-x64.out'
   command(rec,name+'-arm-encode',[qemu,'-cpu','cortex-a72','-L',target,probe,aa,'-1',inp,aa],qenv,900)
   command(rec,name+'-arm-decode',[qemu,'-cpu','cortex-a72','-L',target,probe,ao,'-d',aa,ao],qenv,900)
   command(rec,name+'-x64-encode',[xprobe,'once',xa,'-1',inp,xa],qenv,900);command(rec,name+'-x64-decode-arm',[xprobe,'once',xo,'-d',aa,xo],qenv,900);command(rec,name+'-arm-decode-x64',[qemu,'-cpu','cortex-a72','-L',target,probe,back,'-d',xa,back],qenv,900)
   if any(p.read_bytes()!=fixture for p in (ao,xo,back)):raise RuntimeError(f'archive exchange mismatch: {name}')
   if maps(vendor,src['vendor']['files'])!=vendor_before or {p.name:digest(p) for p in bridge.iterdir() if p.is_file()}!=bh:raise RuntimeError(f'input changed: {name}')
   rec['variants'][name]={'vendor':vendor_before,'bridge':bh,'x64_library':digest(xlib),'x64_probe':digest(xprobe),'arm_library':digest(lib),'arm_probe':digest(probe),'arm_archive':digest(aa),'x64_archive':digest(xa)};cap()
  if digest(contract)!=contract_before:raise RuntimeError('full-engine variant contract changed')
  rec['allocated_work']=cap();rec['status']='pass'
 except Exception as e:rec['error']=str(e);raise
 finally:(WORK/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':main()
