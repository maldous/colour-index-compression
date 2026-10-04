from pathlib import Path
import hashlib,json,os,shutil,tarfile,time
WORK=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1')
JOB=Path(__file__).parent
names=json.loads((JOB/'targets.json').read_text())
archive_root=WORK/'preserved-sdk-artifacts-v1';archive_root.mkdir(exist_ok=False)
receipts=[]
for name in names:
 target=WORK/name
 assert target.parent==WORK and target.is_dir() and name.startswith('sdk-')
 files={}
 for p in target.rglob('*'):
  key=str(p.relative_to(WORK))
  if p.is_symlink(): files[key]={'symlink':os.readlink(p)}
  elif p.is_file(): files[key]={'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest(),'bytes':p.stat().st_size}
 path=archive_root/(name+'.tar.gz');part=path.with_suffix(path.suffix+'.partial')
 with tarfile.open(part,'w:gz',compresslevel=1) as archive: archive.add(target,arcname=name,recursive=True)
 seen={}
 with tarfile.open(part,'r:gz') as archive:
  for member in archive:
   if member.issym(): seen[member.name]={'symlink':member.linkname}
   elif member.isfile():
    with archive.extractfile(member) as f: seen[member.name]={'sha256':hashlib.file_digest(f,'sha256').hexdigest(),'bytes':member.size}
 assert files==seen, 'archive verification failed: '+name
 part.rename(path)
 receipt={'original':str(target),'archive':str(path),'archive_sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'archive_bytes':path.stat().st_size,'preserved_files':files,'verified_before_original_removal':True}
 receipts.append(receipt)
 (JOB/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n')
 shutil.rmtree(target)
 print(json.dumps({'compacted':name,'files':len(files),'archive_bytes':path.stat().st_size}),flush=True)
