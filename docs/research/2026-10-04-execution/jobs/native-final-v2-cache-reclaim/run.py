import hashlib,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
WORK=ROOT/"benchmark-work/native-rc-check-v1";COPY=WORK/"native-final-source-v2/target";ORIGINAL=WORK/"distribution-engineering-v4/target"
if os.environ.get("CIX_RELEASE_LEASE")!="1":raise RuntimeError("root lease required")
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}
def ids(root):return {(p.stat().st_dev,p.stat().st_ino) for p in root.rglob("*") if p.is_file() and not p.is_symlink()}
v1=ROOT/"docs/research/2026-10-04-execution/jobs/native-final-source-v2/receipt.json"
r=json.loads(v1.read_text());assert r["status"]=="fail" and r["phases"]["clippy"]["returncode"]==101
expected=r["copied_lto_target"]["files_sha256"];actual=hashes(COPY);retained=hashes(ORIGINAL)
assert actual==expected==retained,"copy is not exact retained cache; do not remove"
assert COPY.is_dir() and not COPY.is_symlink() and COPY.resolve()==COPY
assert not ids(COPY)&ids(ORIGINAL),"unexpected hardlink to retained evidence"
symlinks={str(p.relative_to(COPY)):os.readlink(p) for p in COPY.rglob("*") if p.is_symlink()}
assert symlinks=={str(p.relative_to(ORIGINAL)):os.readlink(p) for p in ORIGINAL.rglob("*") if p.is_symlink()}
receipt={"status":"verified_duplicate_reclaimed","removed":str(COPY),"retained_equivalent":str(ORIGINAL),"member_sha256":actual,"symlinks":symlinks,"failed_job_receipt_sha256":hashlib.sha256(v1.read_bytes()).hexdigest(),"scope":"only duplicate unused cache from Cargo environment-configuration failure; frozen export and all failure logs preserved"}
(OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
shutil.rmtree(COPY)
assert hashes(ORIGINAL)==retained
