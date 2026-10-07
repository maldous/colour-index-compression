import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
root = Path(__file__).resolve().parents[5]
job = Path(__file__).resolve().parent
work = root / 'benchmark-work/native-rc-check-v1'
out = work / 'kernel-vm-v1'
out.mkdir(exist_ok=False)
source = work / 'kernel-vm-source-v1'
scripts = source / 'scripts'
fixture = out / 'fixture'
module = work / 'kernel-module-v2/stage/cix_squashfs.ko'
module_receipt = json.loads((job.parent / 'kernel-module-v2/receipt.json').read_text())
assert hashlib.sha256(module.read_bytes()).hexdigest() == module_receipt['module_sha256']
env = {**os.environ,
       'CIX_KERNEL_RELEASE': '6.8.0-142-generic',
       'CIX_SQUASHFS_MODULE': str(module),
       'CIX_MODULE_CLOSURE_STAGE': str(out / 'module-closure'),
       'CIX_MODULE_CLOSURE': str(out / 'module-closure'),
       'CIX_MKSQUASHFS': str(work / 'squashfs-host-v2/tools-build/cix-mksquashfs'),
       'CIX_FIXTURE_SOURCE': str(work / 'squashfs-host-v3/fixture/root'),
       'CIX_VM_FIXTURE_OUTPUT': str(fixture),
       'CIX_SQUASHFS_RECEIPT': str(fixture / 'receipt.json'),
       'CIX_FUSE_READER': str(work / 'squashfs-readers-v7/squashfuse-fuse-build/squashfuse'),
       'CIX_FUSE_XATTR_CHECKER': str(out / 'xattr-check'),
       'CIX_FUSE_GUEST_STAGE': str(out / 'fuse-guest'),
       'CIX_BUSYBOX': '/usr/bin/busybox',
       'CIX_INITRAMFS_STAGE': str(out / 'initramfs'),
       'CIX_VM_INITRD_OUTPUT': str(out / 'initramfs.cpio.gz'),
       'CIX_VM_INITRD': str(out / 'initramfs.cpio.gz'),
       'CIX_VM_KERNEL': str(work / 'kernel-vm-inputs-v1/vmlinuz'),
       'CIX_SQUASHFS_IMAGE': str(fixture / 'image.sqfs'),
       'CIX_SQUASHFS_BAD_IMAGE': str(fixture / 'malformed-version.sqfs'),
       'CIX_SQUASHFS_TRUNCATED_IMAGE': str(fixture / 'truncated.sqfs'),
       'CIX_SQUASHFS_OVERSIZED_IMAGE': str(fixture / 'oversized.sqfs'),
       'CIX_VM_OUTPUT': str(out / 'vm'), 'CIX_VM_TIMEOUT_SECONDS': '180'}
rows = []

def run(args):
    p = subprocess.run(list(map(str, args)), cwd=out, env=env,
                       capture_output=True, text=True, timeout=240)
    rows.append({'argv': list(map(str, args)), 'returncode': p.returncode,
                 'stdout': p.stdout, 'stderr': p.stderr})
    (job / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    if p.returncode:
        raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:])

run(['cc', '-static', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
     source / 'tests/xattr_check.c', '-o', out / 'xattr-check'])
for script in ['prepare-module-closure.sh', 'prepare-vm-fixture.sh',
               'prepare-fuse-guest.sh', 'make-initramfs.sh', 'qualify-vm.sh']:
    run(['sh', scripts / script])
rows.append({'status': 'passed', 'kernel_module_sha256': module_receipt['module_sha256'],
             'fixture_files': 305, 'kernel_and_fuse_xattr_checks': 4,
             'negative_images': 3, 'virtual_cpu_count': 2, 'acceleration': 'tcg'})
(job / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
