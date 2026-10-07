import hashlib,json,subprocess
from pathlib import Path
job=Path(__file__).resolve().parent
packages=json.loads((job/'packages.json').read_text())
work=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/codec-sdk-v1')
archives=work/'archives';prefix=work/'prefix'
archives.mkdir(parents=True,exist_ok=False);prefix.mkdir()
receipts=[]
for item in packages:
 selector=item['name']+':'+item['architecture']+'='+item['version']
 subprocess.run(['apt-get','download',selector],cwd=archives,check=True)
 files=[p for p in archives.glob(item['name']+'_*.deb')]
 assert len(files)==1,files
 path=files[0];actual=hashlib.sha256(path.read_bytes()).hexdigest()
 assert actual==item['sha256'],(selector,actual)
 subprocess.run(['dpkg-deb','-x',str(path),str(prefix)],check=True)
 receipts.append({**item,'verified_sha256':actual,'local_archive':str(path)})
(job/'provisioned.json').write_text(json.dumps({'packages':receipts,'prefix':str(prefix),'no_system_install':True},indent=2)+'\n')
