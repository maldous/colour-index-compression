import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=Path(__file__).resolve().parents[5];w=r/"benchmark-work/native-rc-check-v1";out=w/"selection-override-contract-v1";out.mkdir();source=out/"source";cargo=shutil.which("cargo")
receipt={"scope":"RC07 override discovery and existing CLI override contracts, not benchmark","commands":[]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save():(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
def run(label,args):
 start=time.monotonic()
 with (out/(label+".stdout.log")).open("w") as stdout,(out/(label+".stderr.log")).open("w") as stderr:
  result=subprocess.run(args,stdout=stdout,stderr=stderr,env={**os.environ,"TMPDIR":str(out)})
 receipt["commands"].append({"label":label,"argv":args,"returncode":result.returncode,"seconds":time.monotonic()-start});save()
 if result.returncode:raise RuntimeError(label+" failed")
run("format-source",[cargo,"fmt","--manifest-path",str(r/"rust/cix-native/Cargo.toml")])
shutil.copytree(r/"rust/cix-native",source,ignore=shutil.ignore_patterns("target","__pycache__",".scannerwork"))
receipt["source_files_sha256"]={str(p.relative_to(source)):sha(p) for p in source.rglob("*") if p.is_file() and not p.is_symlink()};save()
manifest=str(source/"Cargo.toml")
run("format-check",[cargo,"fmt","--manifest-path",manifest,"--check"])
run("selection-tests",[cargo,"test","--manifest-path",manifest,"--locked","--offline","--lib","full_engine::selection::tests::","--","--test-threads=1"])
run("backend-constraints",[cargo,"test","--manifest-path",manifest,"--locked","--offline","--lib","backend_constraint_reports_supported_and_unsupported_native_routes","--","--test-threads=1"])
run("cli-overrides",[cargo,"test","--manifest-path",manifest,"--locked","--offline","--test","full_engine_constraints","--test","selection_overrides","--","--test-threads=1"])
run("clippy",[cargo,"clippy","--manifest-path",manifest,"--locked","--offline","--all-targets","--","-D","warnings"])
receipt["status"]="PASS";save()
