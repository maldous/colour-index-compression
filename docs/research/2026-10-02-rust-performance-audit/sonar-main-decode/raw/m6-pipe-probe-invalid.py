import os,subprocess,time,json,hashlib,select
c='/tmp/cix-main-decode-candidate-target/release/cix';u='/tmp/cix-main-decode-candidate-target/release/uncix';src=b'A'*8192
pre=lambda:os.sched_setaffinity(0,{16})
p=subprocess.Popen([c,'--format','cixm6','--fast','--block-size','4KiB','--memory','128MiB','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=pre)
q=subprocess.Popen([u,'-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=pre)
p.stdin.write(src);p.stdin.flush();os.set_blocking(p.stdout.fileno(),False);os.set_blocking(q.stdout.fileno(),False)
arc=bytearray();dec=bytearray();start=time.monotonic();first=None
while time.monotonic()-start<60 and not dec:
 r,_,_=select.select([p.stdout.fileno(),q.stdout.fileno()],[],[],.05)
 if p.stdout.fileno() in r:
  try:x=os.read(p.stdout.fileno(),65536)
  except BlockingIOError:x=b''
  if x: arc+=x; q.stdin.write(x);q.stdin.flush()
 if q.stdout.fileno() in r:
  try:x=os.read(q.stdout.fileno(),65536)
  except BlockingIOError:x=b''
  if x: dec+=x;first=time.monotonic()-start
p.stdin.close();os.set_blocking(p.stdout.fileno(),True);rest=p.stdout.read() or b'';arc+=rest;q.stdin.write(rest);q.stdin.close();os.set_blocking(q.stdout.fileno(),True);dec+=q.stdout.read() or b'';rc=p.wait();dq=q.wait()
print(json.dumps({'chunk_schedule':[8192,'producer_open'],'timeout_seconds':60,'archive_before_eof':len(arc)-len(rest),'decoded_before_eof':len(dec) if first else 0,'first_decoded_seconds':first,'encode_alive_before_close':rc==0,'encode_exit':rc,'decode_exit':dq,'exact':dec==src,'end_sha256':hashlib.sha256(dec).hexdigest()}))
