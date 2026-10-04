import hashlib,json,os,subprocess,time
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=Path(__file__).resolve().parents[5];w=r/"benchmark-work/native-rc-check-v1";prior=w/"selection-override-contract-v1";source=prior/"source";out=w/"selection-override-clippy-v2";out.mkdir();record=json.loads((prior/"receipt.json").read_text())
actual={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file() and not p.is_symlink()};assert actual==record["source_files_sha256"]
cmd=record["commands"][-1]["argv"];assert "clippy" in cmd
with (out/"stdout.log").open("w") as stdout,(out/"stderr.log").open("w") as stderr:
 result=subprocess.run(cmd,stdout=stdout,stderr=stderr,env={**os.environ,"TMPDIR":str(out)})
(out/"receipt.json").write_text(json.dumps({"reason":"Single retry of unchanged source after GCC13 internal compiler segmentation fault while compiling unchanged libzpaq vendor TU","source_receipt_sha256":hashlib.sha256((prior/"receipt.json").read_bytes()).hexdigest(),"source_files_verified":len(actual),"argv":cmd,"returncode":result.returncode},indent=2)+"\n")
raise SystemExit(result.returncode)
