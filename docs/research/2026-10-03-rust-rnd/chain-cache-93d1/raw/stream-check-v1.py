import hashlib,json,os,subprocess,threading,time
from pathlib import Path
root=Path('/home/user/src/colour-index-compression');area=root/'docs/research/2026-10-03-rust-rnd/chain-cache-93d1';work=root/'benchmark-work/chain-cache-93d1/stream';work.mkdir(exist_ok=True)
cix=root/'benchmark-work/chain-cache-93d1/target/release-lto/cix';uncix=root/'benchmark-work/combined-bd2-validation/final/uncix';start=time.monotonic();encoded=bytearray();restored=bytearray();first=threading.Event();errors=[];latency={}
cg=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().strip().split(':')[-1]);before={k:(cg/k).read_text().strip() for k in ['cpu.max','cpuset.cpus.effective','memory.max','memory.peak','memory.swap.max','memory.events']}
enc=subprocess.Popen([str(cix),'--best','--format','cixm6','--threads','1','--memory','512MiB','--stream','--block-size','512B','--flush-interval','50ms','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(work/'encode.stderr').open('wb'),bufsize=0)
dec=subprocess.Popen([str(uncix),'--stream','--memory','512MiB','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(work/'decode.stderr').open('wb'),bufsize=0)
def pump():
 try:
  while chunk:=os.read(enc.stdout.fileno(),65536):
   if not encoded:latency['first_encoded_bytes_seconds']=time.monotonic()-start
   encoded.extend(chunk);assert len(encoded)<=1048576
   view=memoryview(chunk)
   while view:
    n=os.write(dec.stdin.fileno(),view);view=view[n:]
  dec.stdin.close()
 except BaseException as e:errors.append(repr(e))
def read():
 try:
  while chunk:=os.read(dec.stdout.fileno(),256):
   restored.extend(chunk);assert len(restored)<=512
   if len(restored)>=256 and not first.is_set():latency['first_decoded_block_seconds']=time.monotonic()-start;first.set()
 except BaseException as e:errors.append(repr(e))
t1=threading.Thread(target=pump);t2=threading.Thread(target=read);t1.start();t2.start()
try:
 os.write(enc.stdin.fileno(),bytes(256))
 assert first.wait(15),'idle partial block did not reconstruct before EOF'
 assert enc.poll() is None and dec.poll() is None
 assert bytes(restored[:256])==bytes(256)
 latency['producer_closed_seconds']=time.monotonic()-start
 os.write(enc.stdin.fileno(),bytes(256));enc.stdin.close()
 assert enc.wait(timeout=30)==0 and dec.wait(timeout=30)==0
 t1.join(2);t2.join(2);assert not t1.is_alive() and not t2.is_alive() and not errors
 assert restored==bytes(512)
 (work/'archive.cix').write_bytes(encoded);(work/'restored.bin').write_bytes(restored)
 after={k:(cg/k).read_text().strip() for k in before}
 result={'status':'VERIFIED_STREAM_CROSS_DECODE','encoder_source':'93d1c0fb1','decoder_source':'bd2a0d97','input_bytes':512,'input_sha256':hashlib.sha256(bytes(512)).hexdigest(),'restored_sha256':hashlib.sha256(restored).hexdigest(),'archive_bytes':len(encoded),'archive_sha256':hashlib.sha256(encoded).hexdigest(),'encoder_sha256':hashlib.sha256(cix.read_bytes()).hexdigest(),'decoder_sha256':hashlib.sha256(uncix.read_bytes()).hexdigest(),'latency':latency,'whole_integrity':'confirmed only after decoder exit0 following EOF/footer','first_block_before_EOF':True,'idle_flush':True,'model_history':'two partial blocks in one persistent M6 stream; cache local to each call','cgroup_before':before,'cgroup_after':after}
 (area/'stream-result.json').write_text(json.dumps(result,indent=2)+'\n');print('VERIFIED idle stream cross-decode',flush=True)
finally:
 for p in [enc,dec]:
  if p.poll() is None:p.kill()
  p.wait()
