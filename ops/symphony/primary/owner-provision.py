"""Owner-only secure final provision/launch; agent must never execute this script."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

root = Path('/home/user/src/cix-approved-migration')
config = root / 'config'
unit = Path('/etc/systemd/system/cix-symphony-primary.service')
source = Path('/run/cix-symphony-primary/linear-api-key')
if os.geteuid() != 0:
    raise SystemExit('Owner must use the reviewed sudo command')
if source.exists() or source.is_symlink():
    raise SystemExit('Existing credential source: reconcile before replacing')
if subprocess.run(['systemctl', 'is-active', '--quiet', 'cix-symphony-primary.service']).returncode == 0:
    raise SystemExit('Existing active primary: reconcile custody before provisioning')
for name in ['WORKFLOW.draft.md', 'service-start.prepared.sh', 'verify-system-placement.py', 'cix-symphony-primary.service.draft']:
    if not (config / name).is_file():
        raise SystemExit('Reviewed configuration input absent')
# Verify exact reviewed configuration against the retained frozen review manifest.
import json
pins = json.loads((root / 'inventory/cix244-bootstrap-review-pins.json').read_text())['files']
for name in ['WORKFLOW.draft.md', 'service-start.prepared.sh', 'verify-system-placement.py', 'cix-symphony-primary.service.draft']:
    if hashlib.sha256((config / name).read_bytes()).hexdigest() != pins['ops/symphony/primary/' + name]:
        raise SystemExit('Reviewed configuration pin mismatch')
if not (root / 'runtime-cix243-v1/overlay/beam-manifest.json').is_file():
    raise SystemExit('Derived artifact absent')
if unit.exists() and unit.read_bytes() != (config / 'cix-symphony-primary.service.draft').read_bytes():
    raise SystemExit('Different installed primary unit: reconcile before replacement')
secret = sys.stdin.buffer.read(65537)
if not secret or len(secret) > 65536:
    raise SystemExit('Owner credential input empty or oversized')
os.umask(0o077)
source.parent.mkdir(mode=0o700, exist_ok=True)
if source.parent.is_symlink() or source.parent.stat().st_uid != 0:
    raise SystemExit('Credential directory must be root-owned and real')
source.parent.chmod(0o700)
fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
with os.fdopen(fd, 'wb') as stream:
    stream.write(secret)
    stream.flush()
    os.fsync(stream.fileno())
del secret
# Preserve the source through ordinary restart; no ExecStop deletion.
subprocess.run(['install', '-m', '0644', str(config / 'cix-symphony-primary.service.draft'), str(unit)], check=True)
subprocess.run(['install', '-o', 'user', '-g', 'user', '-m', '0600', str(config / 'WORKFLOW.draft.md'), str(config / 'WORKFLOW.active.md')], check=True)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'cix-symphony-primary.service'], check=True)
print('Owner provision/start requested; actual service/API/worker acceptance remains required')
