from pathlib import Path
import hashlib,json,os,subprocess
J=Path(__file__).resolve().parent; R=J.parents[4]
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
policy=R/'docs/research/2026-10-04-execution/reviews/cix-header-policy-v1.json'
x=json.loads(policy.read_text());files=[R/p for p in x['userspace_mit']+x['kernel_gpl_2_only']]+[policy,R/'tools/sonar-cxx/header_policy.py',R/'tools/sonar-cxx/test_header_policy.py']
def hashes():return {str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
before=hashes(); results=[]
for label,cmd in [('unit',['/usr/bin/python3','-m','unittest','discover','-s','tools/sonar-cxx','-p','test_header_policy.py','-v']),('source',['/usr/bin/python3','tools/sonar-cxx/header_policy.py'])]:
 p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=30)
 (J/(label+'.stdout.log')).write_text(p.stdout);(J/(label+'.stderr.log')).write_text(p.stderr)
 results.append({'label':label,'returncode':p.returncode})
after=hashes(); passed=all(x['returncode']==0 for x in results) and before==after
(J/'receipt.json').write_text(json.dumps({'status':'pass' if passed else 'fail','inputs_before':before,'inputs_after':after,'commands':results,'scope':'55 first-party selected C/C++ file headers; vendor untouched; finalSonarpending'},indent=2)+'\n')
raise SystemExit(0 if passed else 1)
