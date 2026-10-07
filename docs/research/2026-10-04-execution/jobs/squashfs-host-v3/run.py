import json,os,subprocess
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE') == '1'
r=Path(__file__).resolve().parents[5];w=r/'benchmark-work/native-rc-check-v1';out=w/'squashfs-host-v3';out.mkdir()
b=w/'squashfs-host-v2/tools-build'
env={**os.environ,'CIX_MKSQUASHFS':str(b/'cix-mksquashfs'),'CIX_UNSQUASHFS':str(b/'cix-unsquashfs'),'CIX_SQUASHFS_WORKDIR':str(out/'fixture'),'CIX_SQUASHFS_PROCESSORS':'4','TMPDIR':str(out)}
p=subprocess.run(['python3',str(w/'squashfs-tools-adapter-source-v3/qualify.py')],env=env,capture_output=True,text=True)
(out/'receipt.json').write_text(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n')
print(p.stdout,p.stderr);raise SystemExit(p.returncode)
