"""Future separately admitted offline restore; never invoked by preparation."""
import json
import os
import shutil
import sys
import tarfile
from pathlib import Path
from verify import JOB, TARGET, ARCHIVE, PREFIX, sha, snapshot, verify_archive

def main():
    assert os.environ.get('CIX_RELEASE_LEASE') == '1', 'separate root scheduler lease required'
    assert len(sys.argv) == 2, 'supply separately approved restore admission JSON'
    admission = json.loads(Path(sys.argv[1]).read_text())
    assert admission['operation'] == 'restore-arm64-rust-sysroot'
    assert admission['comment_id'] and admission['reserved_bytes'] >= 164000000
    assert not TARGET.exists(), 'never overwrite an existing sysroot'
    manifest_path = JOB/'sysroot-manifest.json'
    assert sha(manifest_path) == admission['manifest_sha256']
    manifest = json.loads(manifest_path.read_text())
    verify_archive(manifest)
    # Allocation and concurrent reservations must be independently admitted before
    # invoking this recipe. The approved target tree is its only write location.
    for name,row in sorted(manifest.items(), key=lambda item:len(Path(item[0]).parts)):
        if row['type']=='directory':
            (TARGET/name).mkdir(mode=0o700)
    found = set()
    with tarfile.open(ARCHIVE,'r:xz') as tar:
        for member in tar:
            if not member.isfile() or not member.name.startswith(PREFIX+'lib/'):
                continue
            name=member.name[len(PREFIX):]
            assert name in manifest and manifest[name]['type']=='file' and name not in found
            dest=TARGET/name
            with tar.extractfile(member) as source, dest.open('xb') as output:
                shutil.copyfileobj(source,output,1024*1024)
            assert sha(dest)==manifest[name]['sha256'] and dest.stat().st_size==manifest[name]['bytes']
            found.add(name)
    assert found=={name for name,row in manifest.items() if row['type']=='file'}
    for name,row in sorted(manifest.items(),key=lambda item:len(Path(item[0]).parts),reverse=True):
        path=TARGET/name
        if (path.stat().st_uid,path.stat().st_gid)!=(row['uid'],row['gid']):
            os.chown(path,row['uid'],row['gid'])
        os.chmod(path,row['mode'])
        os.utime(path,ns=(path.stat().st_atime_ns,row['mtime_ns']))
    assert snapshot()==manifest
    print(json.dumps({'status':'RESTORED_EXACT_BYTES_AND_DECLARED_METADATA','files':len(found)}))

if __name__=='__main__':
    main()
