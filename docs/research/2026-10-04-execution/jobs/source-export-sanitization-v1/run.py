#!/usr/bin/env python3
"""Root-scheduled no-build validation of the current engineering source export."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
PROJECT=Path('/home/user/src/colour-index-compression')
JOB=PROJECT/'docs/research/2026-10-04-execution/jobs/source-export-sanitization-v1'
WORK=PROJECT/'benchmark-work/native-rc-check-v1/source-export-sanitization-v1'
def main():
 if os.environ.get('CIX_RELEASE_LEASE')!='1': raise RuntimeError('root scheduler lease is required')
 if WORK.exists(): raise RuntimeError('work directory already exists')
 WORK.mkdir(parents=True)
 root=PROJECT/'rust/cix-native'; export=WORK/'export'
 sys.path.insert(0, str(root/'packaging/export'))
 from engineering_export_job import stage_provider_notices
 subprocess.run(['/usr/bin/python3',str(root/'packaging/export/export_source.py'),'--source-root',str(root),'--manifest',str(root/'packaging/export/source-allowlist.json'),'--output-directory',str(export),'--profile','engineering-validation'],check=True)
 out=export/'cix-0.1.0'
 closure=PROJECT/'docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json'
 stage_provider_notices(closure, root/'packaging/notices/provider-notices.json', out)
 subprocess.run(['/usr/bin/python3',str(root/'packaging/export/stage_provider_sources.py'),'--closure',str(closure),'--receipt-root',str(PROJECT),'--export-root',str(out),'--gpl2-text','/usr/share/common-licenses/GPL-2'],check=True)
 for value in ('/home/user/','benchmark-work/','docs/research/','colour-index-compression/'):
  found=[]
  for path in out.rglob('*'):
   if path.is_file():
    try: text=path.read_text(encoding='utf-8')
    except UnicodeDecodeError: continue
    if value in text: found.append(str(path.relative_to(out)))
  if found: raise RuntimeError(f'private marker {value!r} remains: {found}')
 if not (out/'third_party/paq/SOURCE-IDENTITY.json').is_file(): raise RuntimeError('missing PAQ identity output')
 if not (out/'rust/cix-native/packaging/notices/provider-provenance-v3.json').is_file(): raise RuntimeError('missing sanitized provenance manifest')
 (WORK/'PASS').write_text('source export and notice staging passed; no build performed\n')
if __name__=='__main__': main()
