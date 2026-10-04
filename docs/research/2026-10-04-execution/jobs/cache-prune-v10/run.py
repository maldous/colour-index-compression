import hashlib,json,os
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=Path(__file__).resolve().parents[5];w=r/"benchmark-work/native-rc-check-v1";base=w/"target/debug/deps"
items=[p for p in base.iterdir() if p.is_file() and not p.is_symlink() and (p.suffix in (".a",".rlib",".so") or (p.stat().st_mode&0o111 and p.suffix not in (".d",".rmeta")))];removed=[]
for p in items:
 with p.open("rb") as f:h=hashlib.file_digest(f,"sha256").hexdigest()
 removed.append({"path":str(p),"bytes":p.stat().st_size,"sha256":h});p.unlink()
(Path(__file__).parent/"receipt.json").write_text(json.dumps({"reason":"Reclaim only reproducible Cargo dependency build cache after source-bound override tests and Clippy continuation passed, before bounded Sonar qualification","removed_cache":removed,"preserved":"All source snapshots, test logs, receipts, installed providers/SDKs and current top-level cix/uncix/cixcat remain"},indent=2)+"\n")
