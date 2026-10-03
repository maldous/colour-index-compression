from pathlib import Path
import subprocess,json,os
A=Path(__file__).resolve().parent;R=A.parents[2];W=R/'benchmark-work/release-final-qualification';W.mkdir(exist_ok=True);B=Path('/home/user/src/cix-0.1-artifacts/final/bin');P=B.parent/'packages';S='/home/user/src/cix-0.1-release';C='/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo'
for n in ('package-work','third-party'): (W/n).mkdir(exist_ok=False)
commands=[
 ('packages',['python3',str(A/'package_release.py'),'--source-dir',S,'--binary-dir',str(B),'--output-dir',str(P),'--work-dir',str(W/'package-work'),'--source-date-epoch','1791072000','--execute']),
 ('third-party',['python3',str(A/'third_party_validate.py'),'--packages-dir',str(P),'--reference-bin',str(B),'--work-dir',str(W/'third-party'),'--cargo',C,'--jobs','4','--timeout','1000','--execute']),
 ('stream',['python3',str(A/'t1_test.py'),'--before-cix',str(R/'benchmark-work/release-d3a2/final/cix'),'--after-cix',str(B/'cix'),'--after-uncix',str(B/'uncix'),'--work-dir',str(W/'stream')]),
 ('abi',['python3',str(A/'abi_test.py'),'--library',str(B/'libcix_native.so'),'--work-dir',str(W/'abi')]),
 ('squashfs',['python3',str(A/'squashfs_test.py'),'--fixture',str(R/'benchmark-work/canterbury/alice29.txt'),'--work-dir',str(W/'squashfs'),'--cix',str(B/'cix'),'--cixcat',str(B/'cixcat')])]
results=[]
for name,cmd in commands:
 with (W/f'{name}.stdout').open('w') as out,(W/f'{name}.stderr').open('w') as err:r=subprocess.run(cmd,stdout=out,stderr=err)
 results.append({'name':name,'command':cmd,'exit':r.returncode,'stdout':str(W/f'{name}.stdout'),'stderr':str(W/f'{name}.stderr')});(A/'final-qualification-results.json').write_text(json.dumps(results,indent=2)+'\n')
 if r.returncode:raise SystemExit(f'{name} failed')
