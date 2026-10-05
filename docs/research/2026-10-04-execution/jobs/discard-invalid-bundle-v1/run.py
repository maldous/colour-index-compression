from pathlib import Path
import hashlib, importlib.util, json, os, subprocess
J=Path(__file__).resolve().parent
R=J.parents[4]
W=R/'benchmark-work/native-rc-check-v1'
OLD=J.parent/'preserve-artifact-archives-xz-v1'
P=W/'preserved-artifact-archives-xz-v1/preserved-artifacts.tar.xz.partial'
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
spec=importlib.util.spec_from_file_location('preserve',OLD/'run.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
failure=json.loads((OLD/'receipt.json').read_text()); assert failure['status']=='failed' and failure['removed_originals'] is False
assert P.is_file() and not P.is_symlink() and P.stat().st_size==650000000
assert not P.with_suffix('').exists()
m.no_active_users(P.parent)
original=json.loads((OLD/'bundle.manifest.json').read_text())
now,_=m.collect_manifest(); assert original==now,'original artifacts changed'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
before=P.stat(); h=digest(P); assert P.stat()==before
receipt={'status':'verified_invalid_candidate_before_removal','path':str(P.relative_to(R)),'bytes':before.st_size,'allocated_bytes':before.st_blocks*512,'sha256':h,'original_manifest_sha256':digest(OLD/'bundle.manifest.json'),'originals_verified_unchanged':True,'prior_failure_receipt_sha256':digest(OLD/'receipt.json'),'work_before':m.work_bytes()}
(J/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
P.unlink()
assert not P.exists()
receipt.update(status='pass_invalid_partial_removed_originals_preserved',work_after=m.work_bytes())
(J/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
