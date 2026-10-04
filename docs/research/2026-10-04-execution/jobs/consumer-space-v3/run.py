from pathlib import Path
import hashlib,json,os,shutil,tarfile
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
work=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1')
source=work/'dotnet-sdk-8.0.425'
archive=work/'dotnet-sdk-8.0.425-linux-x64.tar.gz'
receipt={'source':str(source),'archive':str(archive),'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),'members':{}}
with tarfile.open(archive,'r:gz') as contents:
 for member in contents:
  path=source/member.name
  if member.isfile():
   with contents.extractfile(member) as stream: want=hashlib.file_digest(stream,'sha256').hexdigest()
   actual=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
   assert want==actual,member.name
   receipt['members'][str(path.relative_to(source))]={'sha256':actual,'bytes':member.size}
  elif member.issym():
   assert path.is_symlink() and os.readlink(path)==member.linkname,member.name
   receipt['members'][str(path.relative_to(source))]={'symlink':member.linkname}
actual={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() or p.is_symlink()}
assert actual==set(receipt['members']),str(actual-set(receipt['members']))
receipt['verified_before_expanded_removal']=True
Path('/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/consumer-space-v3/receipts.json').write_text(json.dumps(receipt,indent=2)+'\n')
shutil.rmtree(source)
print('SDK preserved in original publisher tar; verified',len(actual),'members',flush=True)
