import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path('/home/user/src/colour-index-compression');J=Path(__file__).resolve().parent;O=R/'benchmark-work/native-rc-check-v1'/J.name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['source-inputs.json','tool-inputs.json','execution-inputs.json']:
    for path,digest in json.loads((J/name).read_text()).items():assert sha(Path(path))==digest,path
assert os.environ.get('CIX_RELEASE_LEASE')=='1' and not O.exists()
O.mkdir();(O/'scratch').mkdir()
command=['/usr/bin/bwrap','--die-with-parent','--unshare-pid','--unshare-net',*json.loads((J/'mounts.json').read_text()),'--','/usr/bin/python3','-I','-B',str(J/'probe.py')]
p=subprocess.run(command,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'},capture_output=True,timeout=45)
assert len(p.stdout)<=65536 and len(p.stderr)<=65536
(O/'probe.stdout').write_bytes(p.stdout);(O/'probe.stderr').write_bytes(p.stderr)
(O/'command.json').write_text(json.dumps(command,indent=2)+'\n')
assert not list((O/'scratch').iterdir())
for name in ['source-inputs.json','tool-inputs.json','execution-inputs.json']:
    for path,digest in json.loads((J/name).read_text()).items():assert sha(Path(path))==digest,path
n=sum(int(subprocess.check_output(['du','-sx','--block-size=1',str(p)]).split()[0]) for p in [J,O]);assert n+1048576+65536<=2000000,n
print(json.dumps({'returncode':p.returncode,'retained':n,'no_codec_executed':True,'scratch_empty':True}),flush=True)
sys.exit(p.returncode)
