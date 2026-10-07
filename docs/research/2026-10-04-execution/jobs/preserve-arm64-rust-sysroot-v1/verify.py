"""Verify an unchanged extracted Rust sysroot against its retained archive."""
import hashlib
import json
import stat
import tarfile
from pathlib import Path

JOB = Path(__file__).resolve().parent
ROOT = JOB.parents[4]
TARGET = ROOT / 'benchmark-work/native-rc-check-v1/platform-linux-arm64-rust-target-v2/sysroot'
ARCHIVE = ROOT / 'benchmark-work/native-rc-check-v1/platform-linux-arm64-rust-target-v1/rust-std.tar.xz'
PREFIX = 'rust-std-1.98.1-aarch64-unknown-linux-gnu/rust-std-aarch64-unknown-linux-gnu/'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def snapshot():
    result = {}
    for path in [TARGET, *sorted(TARGET.rglob('*'))]:
        st = path.lstat()
        assert stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode), str(path)
        row = {'type': 'file' if stat.S_ISREG(st.st_mode) else 'directory',
               'mode': stat.S_IMODE(st.st_mode), 'uid': st.st_uid, 'gid': st.st_gid,
               'mtime_ns': st.st_mtime_ns, 'nlink': st.st_nlink}
        if row['type'] == 'file':
            assert st.st_nlink == 1, str(path)
            row.update(bytes=st.st_size, sha256=sha(path), archive_member=PREFIX+str(path.relative_to(TARGET)))
        result[str(path.relative_to(TARGET))] = row
    return result

def verify_archive(manifest):
    assert sha(ARCHIVE) == '9bf796a6ec5b004813ebd0b650775a7c6a4f3aae97ad362ae294798dca4f3b23'
    assert ARCHIVE.stat().st_size == 30815124
    found = {}
    dirs = set()
    with tarfile.open(ARCHIVE, 'r:xz') as tar:
        for member in tar:
            if not member.name.startswith(PREFIX+'lib/'):
                continue
            name = member.name[len(PREFIX):].rstrip('/')
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert member.isfile() or member.isdir()
            if member.isdir():
                dirs.add(name)
                continue
            assert name not in found
            with tar.extractfile(member) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            found[name] = {'bytes': member.size, 'sha256': digest, 'archive_member': member.name}
    expected = {name: {k: row[k] for k in ['bytes','sha256','archive_member']}
                for name,row in manifest.items() if row['type']=='file'}
    expected_dirs = {name for name,row in manifest.items() if row['type']=='directory'}
    # tar prefix filtering omits the root and bare lib directory entries.
    assert dirs <= expected_dirs
    for name in found:
        assert all(str(parent) in expected_dirs for parent in Path(name).parents)
    assert found == expected
    assert len(found) == 61 and sum(r['bytes'] for r in found.values()) == 162083111
    return {'files':len(found), 'bytes':sum(r['bytes'] for r in found.values()), 'archive_sha256':sha(ARCHIVE)}

def main():
    manifest = json.loads((JOB/'sysroot-manifest.json').read_text())
    assert snapshot() == manifest, 'live sysroot changed'
    result = verify_archive(manifest)
    assert snapshot() == manifest, 'live sysroot changed during archive verification'
    print(json.dumps(result))

if __name__ == '__main__':
    main()
