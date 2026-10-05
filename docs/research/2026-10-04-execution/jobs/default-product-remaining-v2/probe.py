import ctypes, hashlib, json, os, stat, sys, tarfile, zlib
from pathlib import Path
J=Path(__file__).resolve().parent
R=Path('/home/user/src/colour-index-compression')
O=R/'benchmark-work/native-rc-check-v1'/J.name
S=O/'scratch'
result={'scope':'namespace ownership/provider loadability/ABI identity/envelope/route preflight; no codec or compiler','status':'FAILED'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:
    assert (S/'run').is_dir();private=S/'run/private-paq';private.mkdir(mode=0o700)
    rows=[]
    for p in [private,*private.parents]:
        s=p.lstat();rows.append({'path':str(p),'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'directory':stat.S_ISDIR(s.st_mode),'symlink':stat.S_ISLNK(s.st_mode)})
    root=os.statvfs('/');scratch=os.statvfs(S)
    result.update(euid=os.geteuid(),egid=os.getegid(),uid_map=Path('/proc/self/uid_map').read_text(),gid_map=Path('/proc/self/gid_map').read_text(),ancestors=rows,root_readonly=bool(root.f_flag & os.ST_RDONLY),root_metadata_bytes=(root.f_blocks-root.f_bfree)*root.f_frsize,scratch_cap_bytes=scratch.f_blocks*scratch.f_frsize,namespaces={n:os.readlink('/proc/self/ns/'+n) for n in ['user','mnt','pid','net']})
    assert result['root_readonly'] and result['root_metadata_bytes']<=65536 and result['scratch_cap_bytes']<=169996288
    assert all(r['directory'] and not r['symlink'] and r['uid'] in [os.geteuid(),0] and int(r['mode'],8)&0o022==0 for r in rows),rows
    assert rows[0]['uid']==os.geteuid() and rows[0]['mode']=='0o700'
    allowed=json.loads((J/'allowed-links.json').read_text())
    for name,target in allowed.items():
        p=Path(name);assert p.is_symlink() and os.readlink(p)==target,(name,target)
    observed_links={}
    def inspect_chain(value):
        parts=list(Path(value).parts)[1:];cursor=Path('/');steps=0
        while parts:
            cursor=cursor/parts.pop(0);node=cursor.lstat()
            if stat.S_ISLNK(node.st_mode):
                steps+=1;assert steps<=40
                target=os.readlink(cursor);observed_links[str(cursor)]=target
                assert allowed.get(str(cursor))==target,(str(cursor),target)
                absolute=target if target.startswith('/') else str(cursor.parent/target)
                parts=list(Path(os.path.normpath(absolute)).parts)[1:]+parts;cursor=Path('/')
            elif parts:assert stat.S_ISDIR(node.st_mode),str(cursor)
        return cursor
    for expected in json.loads((J/'providers.json').read_text()).values():
        assert str(inspect_chain(expected['path']))==expected['resolved']
    for alias in ['/bin','/lib','/lib64']:inspect_chain(alias)
    assert observed_links==allowed
    result['allowed_symlink_targets']=observed_links
    loaded=[];handles=[];result['providers']=loaded
    for name,expected in json.loads((J/'providers.json').read_text()).items():
        p=Path(expected['path']);resolved=p.resolve(strict=True)
        assert str(resolved)==expected['resolved'] and stat.S_ISREG(resolved.lstat().st_mode) and resolved.stat().st_size==expected['bytes'] and sha(resolved)==expected['sha256'],name
        lib=ctypes.CDLL(str(resolved),mode=os.RTLD_NOW|os.RTLD_LOCAL);handles.append(lib)
        for symbol in expected['symbols']:assert getattr(lib,symbol)
        row={'name':name,**expected,'loadable':True,'symbols_resolved':True}
        if name=='paq-v215':
            version=lib.cix_paq_v215_bridge_version;version.argtypes=[];version.restype=ctypes.c_char_p
            identity=version();assert identity==b'cix-paq-v215-bridge/1';row['version']=identity.decode()
        loaded.append(row)
    result['providers']=loaded
    prior=R/'benchmark-work/native-rc-check-v1/default-product-runtime-v4/evidence'
    with tarfile.open(prior/'scratch-recovery.tar.gz','r:gz') as tar:
        member=tar.getmember('run/bin/cix');assert member.isfile() and member.size==5252912 and member.mode&0o111
        digest=hashlib.sha256();length=0;stream=tar.extractfile(member)
        for b in iter(lambda:stream.read(65536),b''):digest.update(b);length+=len(b)
        assert digest.hexdigest()=='e02ba48b7749536de5e35f667750f77be17d297db6b41af23aa8fa4ae0284747'
        result['cix']={'sha256':digest.hexdigest(),'bytes':length,'mode':oct(member.mode),'extracted':False,'executed':False}
    fixtures=R/'docs/research/2026-10-04-execution/jobs/default-product-remaining-v2/fixtures'
    new=(fixtures/'paq-cixp.cix').read_bytes();old=(fixtures/'paq-native.cix').read_bytes();original=(fixtures/'relocated.input').read_bytes()
    assert len(new)==len(old)==295 and new[:6]==b'CIXB\x0a\x01' and new[12:18]==b'CIXP\x01\x01'
    assert new[:12]==old[:12] and new[18:]==old[18:] and b'paq8px'+new[18:]==old[12:]
    n=0;shift=0;pos=6
    while True:
        b=new[pos];pos+=1;n|=(b&127)<<shift
        if b<128:break
        shift+=7
    assert pos==8 and n==len(original)==10240 and int.from_bytes(new[8:12],'big')==zlib.crc32(original)
    result['frame']={'sha256':hashlib.sha256(new).hexdigest(),'bytes':len(new),'paid_length':n,'crc_verified':True,'nested_version':'v215','raw_member_sha256':hashlib.sha256(old[12:]).hexdigest(),'first12_and_suffix_unchanged':True}
    result['route']=json.loads((J/'route.json').read_text())
    result['status']='PASS'
except BaseException as e:result['error']=repr(e)
output=json.dumps(result,indent=2)+'\n';assert len(output.encode())<=65536;print(output,end='')
sys.exit(0 if result['status']=='PASS' else 1)
