from pathlib import Path
import subprocess,json
AREA=Path(__file__).resolve().parent
ROOT=AREA.parents[2]
BINS=Path('/home/user/src/cix-0.1-artifacts/bin')
WORK=ROOT/'benchmark-work/release-final-checks'
WORK.mkdir(exist_ok=False)
checks={
 't1':['python3',str(AREA/'t1_test.py'),'--before-cix',str(ROOT/'benchmark-work/release-d3a2/final/cix'),'--after-cix',str(BINS/'cix'),'--after-uncix',str(BINS/'uncix'),'--work-dir',str(WORK/'t1')],
 'abi':['python3',str(AREA/'abi_test.py'),'--library',str(BINS/'libcix_native.so'),'--work-dir',str(WORK/'abi')],
 'squashfs':['python3',str(AREA/'squashfs_test.py'),'--fixture',str(ROOT/'benchmark-work/canterbury/alice29.txt'),'--work-dir',str(WORK/'squashfs'),'--cix',str(BINS/'cix'),'--cixcat',str(BINS/'cixcat')]
}
results={}
for name,cmd in checks.items():
 r=subprocess.run(cmd,capture_output=True,text=True)
 (AREA/f'check-{name}.stdout.log').write_text(r.stdout)
 (AREA/f'check-{name}.stderr.log').write_text(r.stderr)
 results[name]={'exit':r.returncode,'command':cmd,'work':str(WORK/name)}
 (AREA/'release-check-results.json').write_text(json.dumps(results,indent=2)+'\n')
 if r.returncode: raise SystemExit(f'{name} failed, see log')
