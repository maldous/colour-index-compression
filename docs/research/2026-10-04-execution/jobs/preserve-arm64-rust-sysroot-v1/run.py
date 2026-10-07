"""Admitted preparation verification only. Never retires or restores files."""
import json
import os
import subprocess
from verify import JOB, ROOT, TARGET, ARCHIVE, sha, main as verify

OUT=ROOT/'benchmark-work/native-rc-check-v1'/JOB.name
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
assert not OUT.exists()
pins=json.loads((JOB/'execution-inputs.json').read_text())
for name,digest in pins.items(): assert sha(name)==digest,name
OUT.mkdir()
verify()
for name,digest in pins.items(): assert sha(name)==digest,name
result={'status':'PRESERVATION_CANDIDATE_VERIFIED_NOT_RETIRED','target':str(TARGET),
        'archive':str(ARCHIVE),'archive_sha256':sha(ARCHIVE),'target_unchanged':True,
        'manifest_sha256':sha(JOB/'sysroot-manifest.json'),'regular_files':61,
        'target_allocated_bytes':int(subprocess.check_output(['du','-sx','-B1',str(TARGET)]).split()[0]),
        'retirement_authorized':False,'restore_executed':False,
        'claim':'e7e0ad04-ff5e-4832-af36-e609d5ec5e6d','admission':'04926978-b0a0-498c-8117-5c3c7f547c0e'}
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
assert sum(int(subprocess.check_output(['du','-sx','-B1',str(p)]).split()[0]) for p in [JOB,OUT])<2000000
print(json.dumps(result))
