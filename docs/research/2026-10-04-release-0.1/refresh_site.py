"""Root-owned static review data refresh, no publication and no measurements."""
from pathlib import Path
import subprocess,json,hashlib,shutil,markdown
A=Path(__file__).resolve().parent;S=Path('/home/user/src/cix-release-review-site/dist');D=S/'downloads';E=Path('/home/user/src/cix-0.1-distribution');B=Path('/home/user/src/cix-0.1-artifacts/final');P=Path('/home/user/src/cix-0.1-artifacts/distribution-v2/packages');SUMMARY=A/'distribution-summary-final'
subprocess.run(['python3',str(A/'summarize_release.py'),'--benchmark',str(A/'distribution-benchmark-final'),'--output',str(SUMMARY)],check=True)
x=json.loads((SUMMARY/'results.json').read_text());pub={'schema':x['schema'],'counts':x['counts'],'policy':x['policy'],'rows':x['rows'],'totals':x['totals']}
for row in pub['rows']:
 for p in row['profiles'].values():
  # Preserve the public measurements and result classification, not host paths.
  receipt=p.get('scheduler_receipt')
  if receipt is not None:
   p['resource_receipt']={k:receipt.get(k) for k in ('exit_code','stop_reason','elapsed_seconds','sampled_cgroup_memory_high_water_bytes','memory_measurement_note','peak_temp_bytes','cpu_usage_seconds','cgroup_verified')}
  for key in ('scheduler','scheduler_receipt','scheduler_raw','child_diagnostics'):p.pop(key,None)
  p.pop('source_path',None)
(S/'results.json').write_text(json.dumps(pub,indent=2)+'\n')
D.mkdir(exist_ok=True)
for p in P.iterdir():
 if p.is_file():shutil.copy2(p,D/p.name)
for name in ('results.csv','totals.csv'):shutil.copy2(SUMMARY/name,D/name)
shutil.copy2(A/'public-records.json',D/'records.json')
freeze=json.loads((A/'release-binary-freeze-final.json').read_text()); binaries=[{'name':Path(v['path']).name,'bytes':v['bytes'],'sha256':v['sha256']} for v in freeze['files']];plan=json.loads((A/'distribution-benchmark-final/plan.json').read_text());source=plan['release']['source_export'];dsos=plan['release']['runtime_dsos']
manifest={'version':'0.1.0','stage':'Private review candidate','build':freeze['selection'],'binaries':binaries,'packages':json.loads((P/'package-receipt.json').read_text())['artifacts'],'source':{'files':source['files'],'sha256':source['sha256']},'host':json.loads((A/'release-host.json').read_text()),'dependencies':dsos,'qualification':{'library_tests':115,'CLI_tests':4,'streaming_tests':7,'Clippy':'PASS; zero Rust diagnostics','Sonar':'PASS; zero current Rust issues; gate OK; vendored C++ outside scan','packages':'clean source build; staged install/uninstall; extracted Debian/RPM exact hashes and roundtrips','SquashFS':'standard Zstd SquashFS file transport; not native kernel CIX codec'},'limits':'macOS/Windows source recipes unqualified; RPM target distro runtime unqualified; private MIT proposal pending owner confirmation'}
from benchmark_driver import tree_manifest
shipping=tree_manifest(E);amendment=json.loads((A/'dependency-notices/amendment.json').read_text())
manifest['source']={'files':shipping['files'],'sha256':shipping['sha256'],'role':'Shipping documentation-amended source'}
manifest['measured_source']={'files':source['files'],'sha256':source['sha256'],'role':'Source used for frozen measured binaries'}
manifest['documentation_amendment']={k:amendment[k] for k in ('changed_paths','runtime_equivalence','notice_integration')}
manifest['qualification']['dependency_notices']='All 32 locked Rust crates, source/binary archives, staged install, Debian/RPM and DSC notice hashes verified; code and measured binaries unchanged'
for name in ('LICENSE','THIRD_PARTY_NOTICES.txt','THIRD_PARTY_NOTICES_RUST.md','SECURITY.md'):shutil.copy2(E/name,S/name)
(D/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(D/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(D.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
# Update already-authored styled documentation pages from final shipping text.
for name,body in [('build',markdown.markdown((E/'README.md').read_text(),extensions=['fenced_code','tables']).replace('<h2>Platform status</h2>','<h2 id="platforms">Platform status</h2>')),('manual','<h1>CIX command manual</h1>'+''.join(subprocess.check_output(['pandoc','-f','man','-t','html',str(E/'man'/f'{n}.1')],text=True) for n in ('cix','uncix','cixcat')))]:
 p=S/f'{name}.html';old=p.read_text();head=old.split('<main class="doc">',1)[0]+'<main class="doc">';foot='</main>'+old.split('</main>',1)[1];p.write_text(head+body+foot)
print(json.dumps({'physical_inputs':x['counts'],'verified':sum(v['status']=='VERIFIED' for r in x['rows'] for v in r['profiles'].values()),'pending':sum(v['status']=='PENDING' for r in x['rows'] for v in r['profiles'].values()),'publication':'not requested by this helper'}))
