"""One specifically admitted retirement of archive-reconstructible files."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

JOB=Path(__file__).resolve().parent
PREP=JOB.parent/'preserve-arm64-rust-sysroot-v1'
sys.path.insert(0,str(PREP))
from verify import ROOT,TARGET,ARCHIVE,sha,snapshot,verify_archive
OUT=ROOT/'benchmark-work/native-rc-check-v1'/JOB.name

def census():
    roots=json.loads((JOB/'capacity-roots.json').read_text())
    lines=subprocess.check_output(['du','-sx','-B1',*roots],text=True).splitlines()
    rows=[{'bytes':int(line.split('\t',1)[0]),'path':line.split('\t',1)[1]} for line in lines]
    return {'rows':rows,'retained_git_delta_bytes':2486272,'total_bytes':sum(r['bytes'] for r in rows)+2486272}

def write(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    assert sum(int(subprocess.check_output(['du','-sx','-B1',str(p)]).split()[0]) for p in [JOB,OUT])<2000000

def parent_fd(root_fd,path):
    parts=Path(path).parts
    assert parts and not Path(path).is_absolute() and all(p not in ['.','..'] for p in parts)
    fd=os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
        return fd,parts[-1]
    except BaseException:
        os.close(fd);raise

def main():
    assert os.environ.get('CIX_RELEASE_LEASE')=='1'
    pins=json.loads((JOB/'execution-inputs.json').read_text())
    for path,digest in pins.items():assert sha(path)==digest,path
    assert not OUT.exists()
    OUT.mkdir()
    done=[];result={'status':'FAILED','operation_count':0,'implicit_restore':False}
    try:
        before=census();assert before['total_bytes']+2000000+30000000<=4000000000
        write('before.json',before)
        reader=json.loads((JOB/'process-prelaunch.json').read_text())
        age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(reader['at_utc'])).total_seconds()
        assert 0<=age<=90 and not reader['target_matches'] and not reader['inspection_errors'], 'reader recheck missing/stale/failed'
        manifest=json.loads((PREP/'sysroot-manifest.json').read_text())
        assert snapshot()==manifest
        assert TARGET.resolve()==TARGET
        for path in [TARGET,*TARGET.parents]:
            assert stat.S_ISDIR(path.lstat().st_mode) and not path.is_symlink()
        assert all(not os.listxattr(TARGET/name,follow_symlinks=False) for name in manifest)
        verify_archive(manifest)
        assert snapshot()==manifest
        target_allocated=int(subprocess.check_output(['du','-sx','-B1',str(TARGET)]).split()[0])
        assert target_allocated==162226176
        operations=json.loads((JOB/'operations.json').read_text())
        assert operations==([{'op':'unlink','path':name} for name,row in sorted(manifest.items()) if row['type']=='file']+
                           [{'op':'rmdir','path':name} for name,row in sorted(manifest.items(),key=lambda item:(-len(Path(item[0]).parts),item[0])) if row['type']=='directory'])
        write('verified-before.json',{'manifest':manifest,'archive_sha256':sha(ARCHIVE),'operations':operations,'reader_age_seconds':age,'all_xattrs_empty':True,'target_allocated_bytes':target_allocated})
        root_fd=os.open(TARGET,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        identity=os.fstat(root_fd)
        try:
            for operation in operations:
                name=operation['path'];row=manifest[name]
                if name=='.':
                    assert operation['op']=='rmdir'
                    pfd=os.open(TARGET.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                    leaf=TARGET.name
                else:pfd,leaf=parent_fd(root_fd,name)
                try:
                    current=os.stat(leaf,dir_fd=pfd,follow_symlinks=False)
                    assert (stat.S_IMODE(current.st_mode),current.st_uid,current.st_gid)==(row['mode'],row['uid'],row['gid'])
                    if operation['op']=='unlink':
                        assert stat.S_ISREG(current.st_mode) and current.st_nlink==1
                        assert current.st_size==row['bytes'] and current.st_mtime_ns==row['mtime_ns']
                        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=pfd)
                        with os.fdopen(fd,'rb') as stream:
                            opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(current.st_dev,current.st_ino)
                            assert hashlib.file_digest(stream,'sha256').hexdigest()==row['sha256']
                        again=os.stat(leaf,dir_fd=pfd,follow_symlinks=False)
                        assert (again.st_dev,again.st_ino,again.st_size,again.st_mtime_ns,again.st_nlink)==(current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns,1)
                        os.unlink(leaf,dir_fd=pfd)
                    else:
                        assert stat.S_ISDIR(current.st_mode)
                        if name=='.':assert (current.st_dev,current.st_ino)==(identity.st_dev,identity.st_ino)
                        os.rmdir(leaf,dir_fd=pfd)
                    done.append(operation)
                    write('completed-operations.json',done)
                finally:os.close(pfd)
        finally:os.close(root_fd)
        assert not TARGET.exists()
        for path,digest in pins.items():assert sha(path)==digest,path
        after=census();write('after.json',after)
        result.update(status='RETIRED_EXACT_RECONSTRUCTIBLE_TREE',target_absent=True,archive_and_protected_pins_unchanged=True,
                      retired_allocated_bytes=target_allocated,before_total=before['total_bytes'],after_total=after['total_bytes'],
                      future_ARM64_Rust_condition='Separately admitted 164MB offline exact restore and new smoke before use')
    except BaseException as error:
        result.update(error=repr(error),target_exists=TARGET.exists())
    finally:
        result.update(operation_count=len(done),completed_operations=done,admission='a372f068-42a0-481a-8c1c-b1e439df2cd1')
        write('result.json',result)
        print(json.dumps({k:v for k,v in result.items() if k!='completed_operations'}))
    return 0 if result['status']=='RETIRED_EXACT_RECONSTRUCTIBLE_TREE' else 1

if __name__=='__main__':
    sys.exit(main())
