from pathlib import Path
import hashlib
import json
import os
import shutil
import tarfile

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
JOB = Path(__file__).resolve().parent
WORK = Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1')
ARCHIVES = WORK / 'preserved-consumer-artifacts-v1'
ARCHIVES.mkdir()
receipts = []
for index, relative in enumerate(json.loads((JOB / 'targets.json').read_text())):
    source = WORK / relative
    assert source.is_relative_to(WORK) and not source.is_symlink()
    paths = list(source.rglob('*')) if source.is_dir() else [source]
    before = {}
    for path in paths:
        key = str(path.relative_to(WORK))
        if path.is_symlink():
            before[key] = {'symlink': os.readlink(path)}
        elif path.is_file():
            before[key] = {'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()}
    archive = ARCHIVES / f'{index:02d}-{source.name}.tar.gz'
    with tarfile.open(archive, 'w:gz', compresslevel=1) as out:
        out.add(source, arcname=relative)
    after = {}
    with tarfile.open(archive, 'r:gz') as incoming:
        for member in incoming:
            if member.issym():
                after[member.name] = {'symlink': member.linkname}
            elif member.isfile():
                with incoming.extractfile(member) as stream:
                    after[member.name] = {'bytes': member.size,
                        'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
    assert before == after, f'archive member verification failed: {relative}'
    receipts.append({'source': str(source), 'archive': str(archive),
        'sha256': hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest(),
        'verified_members': before, 'verified_before_expanded_removal': True})
    (JOB / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    if source.is_dir():
        shutil.rmtree(source)
    else:
        source.unlink()
    print(json.dumps({'preserved': relative, 'archive_bytes': archive.stat().st_size}), flush=True)
