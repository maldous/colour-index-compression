#!/usr/bin/env python3
"""Disjoint CCA PGO experiment paired with the portable fat-LTO baseline."""
from __future__ import annotations
import hashlib, json, os, platform, resource, subprocess, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIX = Path("/home/user/src/colour-index-compression")
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
OUT = Path(__file__).resolve().parent
CPUS, CAP = "20,22", 2_000_000_000
TEMP_CAP = 1_000_000_000
TRAIN = ((FIX / "benchmark-work/canterbury/alice29.txt", ("--fast", "--threads", "1")),
         (FIX / "benchmark-work/calgary/book1", ("--threads", "1")))
EVAL = (("fast-kennedy", FIX / "benchmark-work/canterbury/kennedy.xls", ("--fast", "--threads", "1")),
        ("default-kennedy", FIX / "benchmark-work/canterbury/kennedy.xls", ("--threads", "1")),
        ("best-constrained-g1-lz-grammar", FIX / "benchmark-work/canterbury/grammar.lsp", ("--best", "--format", "cixg1", "--route", "lz", "--threads", "1")))

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def limit(): resource.setrlimit(resource.RLIMIT_AS,(CAP,CAP))
def tree_bytes(root): return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
def check_temp(root):
 used=tree_bytes(root)
 if used>TEMP_CAP: raise RuntimeError(f'PGO temporary-space cap exceeded: {used}')
 return used
def build(name, rustflags, root):
 env=os.environ.copy(); env.update({"CARGO_TARGET_DIR":str(root/name),"CARGO_BUILD_JOBS":"2","CARGO_PROFILE_RELEASE_OPT_LEVEL":"3","CARGO_PROFILE_RELEASE_LTO":"fat","CARGO_PROFILE_RELEASE_CODEGEN_UNITS":"1","RUSTFLAGS":rustflags})
 cmd=["taskset","-c",CPUS,"cargo","build","--release","--locked","--manifest-path",str(MANIFEST),"--bin","cix","--bin","uncix"]
 t=time.perf_counter_ns(); p=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,preexec_fn=limit)
 (root/f"{name}.stdout.log").write_text(p.stdout); (root/f"{name}.stderr.log").write_text(p.stderr)
 if p.returncode: raise RuntimeError(f"{name} build failed")
 d=root/name/"release"; return {"name":name,"flags":rustflags,"compile_wall_seconds":(time.perf_counter_ns()-t)/1e9,"cix_sha256":sha(d/'cix'),"cix_bytes":(d/'cix').stat().st_size},d/'cix',d/'uncix'
def timed(cmd, input_bytes=None):
 f=tempfile.NamedTemporaryFile(delete=False); f.close(); t=time.perf_counter_ns()
 p=subprocess.run(["/usr/bin/time","-o",f.name,"-f","%U %S %M",*cmd],input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=limit)
 wall=(time.perf_counter_ns()-t)/1e9
 if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace'))
 u,s,r=Path(f.name).read_text().split(); Path(f.name).unlink()
 return {"wall_seconds":wall,"cpu_seconds":float(u)+float(s),"peak_rss_kib":int(r)},p.stdout
def main():
 if subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()!="15426f310f40b9a3d753313741c28e718f7aceb6": raise SystemExit("source freeze failed")
 llvm=Path(subprocess.check_output(["rustc","--print","sysroot"],text=True).strip())/"lib/rustlib/x86_64-unknown-linux-gnu/bin/llvm-profdata"
 if not llvm.is_file(): raise SystemExit("matching LLVM 22 llvm-profdata unavailable")
 freeze={"schema":"cix-build-pgo-v1","source_revision":"15426f310f40b9a3d753313741c28e718f7aceb6","cpus":CPUS,"memory_bytes":CAP,"temporary_bytes":TEMP_CAP,"toolchain":subprocess.check_output(["rustc","-Vv"],text=True),"llvm_profdata":str(llvm),"train":[{"path":str(p),"sha256":sha(p),"flags":f} for p,f in TRAIN],"held_out":[{"label":n,"path":str(p),"sha256":sha(p),"flags":f} for n,p,f in EVAL],"pgo_scope":"Rust compilation only; bundled C++ backends are not instrumented by -Cprofile-generate."}
 OUT.joinpath("pgo-freeze.json").write_text(json.dumps(freeze,indent=2,sort_keys=True)+"\n")
 with tempfile.TemporaryDirectory(prefix="cix-pgo-") as td:
  td=Path(td); raw=td/'raw'; raw.mkdir()
  temp_samples=[]
  generated,gen_cix,_=build('generate',f'-C target-cpu=x86-64 -Cprofile-generate={raw}',td); temp_samples.append(check_temp(td))
  for p,flags in TRAIN:
   _,archive=timed(["taskset","-c",CPUS,str(gen_cix),*flags,"-c",str(p)])
  temp_samples.append(check_temp(td))
  raws=sorted(raw.rglob('*.profraw'))
  if not raws: raise RuntimeError('PGO training emitted no .profraw')
  merged=td/'merged.profdata'; subprocess.run([str(llvm),'merge','-o',str(merged),*map(str,raws)],check=True)
  baseline,base_cix,base_uncix=build('portable-fat-cgu1','-C target-cpu=x86-64',td); temp_samples.append(check_temp(td))
  pgo,pgo_cix,pgo_uncix=build('pgo-portable-fat-cgu1',f'-C target-cpu=x86-64 -Cprofile-use={merged}',td); temp_samples.append(check_temp(td))
  rows=[]
  for repeat in range(5):
   order=EVAL if repeat%2==0 else tuple(reversed(EVAL))
   for label,inp,flags in order:
    for name,cix in ((baseline['name'],base_cix),(pgo['name'],pgo_cix)):
     em,arc=timed(["taskset","-c",CPUS,str(cix),*flags,"-c",str(inp)])
     expected=sha(inp); ah=hashlib.sha256(arc).hexdigest()
     for decoder_name,uncix in ((baseline['name'],base_uncix),(pgo['name'],pgo_uncix)):
      dm,out=timed(["taskset","-c",CPUS,str(uncix),"-c","-"],arc)
      if hashlib.sha256(out).hexdigest()!=expected: raise RuntimeError(f'cross decode mismatch {name}->{decoder_name}')
      if decoder_name==name: own=dm
     rows.append({"repeat":repeat,"workload":label,"variant":name,"input_sha256":expected,"archive_sha256":ah,"archive_bytes":len(arc),"encode":em,"decode_own":own})
  OUT.joinpath("pgo-results.json").write_text(json.dumps({"schema":"cix-build-pgo-v1","status":"completed","freeze_sha256":sha(OUT/'pgo-freeze.json'),"profile_raw_count":len(raws),"temporary_samples_bytes":temp_samples,"temporary_peak_bytes":max(temp_samples),"generate":generated,"variants":[baseline,pgo],"measurements":rows,"cross_decode":"each archive decoded by baseline and PGO executables, fresh process"},indent=2,sort_keys=True)+"\n")
if __name__=='__main__': main()
