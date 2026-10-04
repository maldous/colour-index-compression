import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
SUBJECT=OUT.parent/"preserve-debug-cache-v1"
def hashes():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SUBJECT.iterdir() if p.suffix in (".py",".json")}
if os.environ.get("CIX_RELEASE_LEASE")!="1":raise RuntimeError("root lease required")
before=hashes()
for name in before:(OUT/(name+".txt")).write_bytes((SUBJECT/name).read_bytes())
command=[sys.executable,"-m","unittest","discover","-s",str(SUBJECT),"-p","test_*.py","-v"]
r=subprocess.run(command,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
unchanged=before==hashes();receipt={"command":command,"returncode":r.returncode,"source_sha256":before,"inputs_unchanged":unchanged,"status":"pass" if r.returncode==0 and unchanged else "fail","scope":"isolated temporary fixtures; actual retained cache not touched"}
(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
sys.exit(0 if receipt["status"]=="pass" else 1)
