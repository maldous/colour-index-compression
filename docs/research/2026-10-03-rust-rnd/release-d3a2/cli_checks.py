import hashlib,json,os,select,signal,subprocess,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');work=root/'benchmark-work/release-d3a2/checks';work.mkdir(exist_ok=True);area=root/'docs/research/2026-10-03-rust-rnd/release-d3a2';release=root/'benchmark-work/release-d3a2/target/release-lto';rows=[]
def run(label,args,data=None,expected=None,reject=False):
 start=time.monotonic();p=subprocess.run(args,input=data,capture_output=True,timeout=15);(work/(label+'.stdout')).write_bytes(p.stdout);(work/(label+'.stderr')).write_bytes(p.stderr)
 assert (p.returncode!=0 if reject else p.returncode==0),label
 if expected is not None:assert p.stdout==expected,label
 rows.append({'case':label,'argv':args,'exit':p.returncode,'wall':time.monotonic()-start,'stdout_bytes':len(p.stdout),'stdout_sha256':hashlib.sha256(p.stdout).hexdigest(),'stderr':p.stderr.decode(errors='replace')});return p.stdout
source=bytes(1024);reference=(root/'benchmark-work/chain-cache-93d1/m6-full/archive.cix').read_bytes();assert hashlib.sha256(reference).hexdigest()=='cc9160a57de3755abc38b46daff53510857c109a8e2cf5ee85b5bb8c4c4556ab'
cix=str(release/'cix');uncix=str(release/'uncix');opts=['--fast','--format','cixm6','--threads','1','--memory','16MiB','--stream','--block-size','512B','-c','-'];dec=[uncix,'--stream','--memory','16MiB','-c','-']
run('old-m6-decode',dec,reference,source)
name=b'data.bin';valid=reference+name+len(name).to_bytes(4,'little')+b'CIXF1';run('valid-cixf1-footer',dec,valid,source)
run('bad-cixf1-name-length',dec,reference+name+(len(name)+1).to_bytes(4,'little')+b'CIXF1',reject=True)
run('bad-cixf1-utf8',dec,reference+b'\xff'+(1).to_bytes(4,'little')+b'CIXF1',reject=True)
run('trailing-m6-data',dec,reference+b'garbage',reject=True)
run('explicit-m6-parallelism-rejected',[cix,*opts,'--parallelism','blocks'],b'',reject=True)
run('decode-parallelism-rejected',[uncix,'--parallelism','candidates','-c','-'],reference,reject=True)
err=(work/'held-open.stderr').open('wb');p=subprocess.Popen(dec,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,start_new_session=True,bufsize=0);start=time.monotonic();restored=bytearray()
try:
 os.write(p.stdin.fileno(),reference)
 deadline=start+5
 while len(restored)<len(source):
  assert time.monotonic()<deadline,'decoder output timeout'
  if select.select([p.stdout],[],[],.05)[0]:
   chunk=os.read(p.stdout.fileno(),4096);assert chunk,'premature decoder EOF';restored.extend(chunk)
 assert restored==source and p.poll() is None
 time.sleep(.1);assert p.poll() is None
 interrupted=time.monotonic();os.killpg(p.pid,signal.SIGINT);status=p.wait(timeout=2);assert status!=0
 rows.append({'case':'complete-footer-input-kept-open-SIGINT','exit':status,'interrupt_seconds':time.monotonic()-interrupted,'SIGKILL_fallback':False,'restored_sha256':hashlib.sha256(restored).hexdigest(),'input_pipe_remained_open':True})
finally:
 if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
 p.stdin.close();p.stdout.close();err.close()
(area/'cli-result.json').write_text(json.dumps({'status':'VERIFIED_FOCUSED_CLI','rows':rows},indent=2)+'\n');print('VERIFIED footer, old format and override checks')
