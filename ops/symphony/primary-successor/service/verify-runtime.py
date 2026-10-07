"""One-shot public closure integrity check before credential consumption."""
from pathlib import Path
import hashlib,json
control=Path(__file__).resolve().parent
pins=json.loads((control/'runtime-pins.json').read_text())
runtime=Path('/home/user/src/cix-approved-migration/runtime-cix243-v2')
if pins['runtime']!=str(runtime):raise SystemExit('Unexpected successor runtime')
for rel,digest in pins['files'].items():
 path=runtime/rel
 if path.is_symlink() or not path.resolve().is_relative_to(runtime) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
  raise SystemExit('Public successor artifact pin mismatch')
print('SUCCESSOR_PUBLIC_ARTIFACT_PINS_PASS')
