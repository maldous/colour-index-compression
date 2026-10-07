"""Execute exactly one frozen G2 scaling point under the root lease."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
A=Path(__file__).resolve().parent
R=A.parents[2]
W=R/'benchmark-work/release-performance-01'
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
p=json.loads((A/'g2-protocol.json').read_text());c=next(c for c in p['cells'] if c['id']==sys.argv[1])
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(W/'selected/cix')==p['preconditions']['selected_cix_sha256']
assert sha(W/'selected/uncix')==p['preconditions']['selected_uncix_sha256']
out=W/'evidence'/c['id'];out.mkdir(parents=True,exist_ok=False)
(out/'artifacts').mkdir();(out/'verification').mkdir()
for name,command in [('encode',c['argv']),('decode',c['fresh_decode'])]:
    with (out/(name+'.stdout')).open('wb') as stdout, (out/(name+'.stderr')).open('wb') as stderr:
        result=subprocess.run(['/usr/bin/time','-v','-o',str(out/(name+'.time')),*command],stdout=stdout,stderr=stderr)
    assert result.returncode==0,(name,result.returncode)
archive=Path(c['argv'][c['argv'].index('-o')+1]);restored=out/'verification/restored'
assert sha(restored)==p['preconditions']['input_sha256']
result={'status':'VERIFIED','cell':c,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'restored_sha256':sha(restored)}
if c['id'].endswith('-4'):
    prior=json.loads((W/'evidence/S-G2-AUTO-1/result.json').read_text())
    assert prior['archive_sha256']==result['archive_sha256']
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
