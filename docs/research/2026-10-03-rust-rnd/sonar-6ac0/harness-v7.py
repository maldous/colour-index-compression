#!/usr/bin/env python3
"""Root-run, lease-gated local Sonar/Clippy scan. Do not run without a lease."""
import argparse, base64, hashlib, json, os, pathlib, secrets, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[2]
SERVER_NAME='cix-sonarqube-4af6'; SCANNER_NAME='cix-scanner-4af6'
SERVER_REF='sonarqube:latest'; SCANNER_REF='sonarsource/sonar-scanner-cli:latest'

def run(a, **kw): return subprocess.run(a, check=True, text=True, timeout=kw.pop('timeout',120), **kw)
def digest(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def manifest(ref):
 x=json.loads(run(['docker','manifest','inspect',ref,'--verbose'],capture_output=True).stdout)
 records=x if isinstance(x,list) else x.get('manifests',[x])
 for i in records:
  if not isinstance(i,dict): continue
  d=i.get('Descriptor',i)
  p=d.get('platform',{})
  if p.get('os')=='linux' and p.get('architecture')=='amd64' and d.get('digest'): return d['digest']
 raise RuntimeError('no amd64 manifest')
def api(url,path,user,pw,data=None):
 req=urllib.request.Request(url+path,data=data,method='POST' if data else 'GET')
 req.add_header('Authorization','Basic '+base64.b64encode(f'{user}:{pw}'.encode()).decode())
 if data:req.add_header('Content-Type','application/x-www-form-urlencoded')
 with urllib.request.urlopen(req,timeout=15) as r:
  body=r.read()
  return json.loads(body) if body else {}
def scrub(text, values):
 for value, label in values:
  if value:
   text=text.replace(value,label).replace(urllib.parse.quote_plus(value),label)
 return text
def scrub_http_error(error, values):
 body=scrub(error.read().decode('utf-8','replace'),values)
 return f'status={error.code}\nbody={body[:4096]}\n'
def assert_cg(text, memory, role):
 d=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
 # Docker's private cgroup namespace may expose only `/` in /proc/self/cgroup.
 # An explicit role hostname binds that live receipt to its dedicated container.
 if d.get('hostname')!=role or not d.get('cgroup') or d.get('memory.swap.max')!='0' or d.get('cpuset') not in ('24-25','24,25') or int(d.get('memory.max','0')) != memory or d.get('cpu.max')!='200000 100000' or not d.get('Cpus_allowed_list'): raise RuntimeError('cgroup role limits/identity mismatch')
 return d
def cg(name):
 return run(['docker','exec',name,'sh','-c',"c=$(sed -n 's/^0:://p' /proc/self/cgroup); b=/sys/fs/cgroup; printf 'hostname=%s\ncgroup=%s\nmemory.max=%s\nmemory.peak=%s\nmemory.swap.max=%s\ncpu.max=%s\ncpuset=%s\n' \"$(cat /proc/sys/kernel/hostname)\" \"$c\" \"$(cat $b$c/memory.max)\" \"$(cat $b$c/memory.peak)\" \"$(cat $b$c/memory.swap.max)\" \"$(cat $b$c/cpu.max)\" \"$(cat $b$c/cpuset.cpus.effective)\"; sed -n 's/^Cpus_allowed_list:[[:space:]]*/Cpus_allowed_list=/p' /proc/self/status"],capture_output=True).stdout
def host_cg(name):
 info=json.loads(run(['docker','inspect',name],capture_output=True).stdout)[0]
 pid=int(info['State']['Pid']); cid=info['Id']; raw=pathlib.Path(f'/proc/{pid}/cgroup').read_text()
 path=next(line[3:] for line in raw.splitlines() if line.startswith('0::'))
 base=pathlib.Path('/sys/fs/cgroup'+path)
 status=pathlib.Path(f'/proc/{pid}/status').read_text()
 allowed=next(line.split(':',1)[1].strip() for line in status.splitlines() if line.startswith('Cpus_allowed_list:'))
 return '\n'.join((f'container_id={cid}',f'pid={pid}',f'host_cgroup={path}',f'memory.max={(base/"memory.max").read_text().strip()}',f'memory.peak={(base/"memory.peak").read_text().strip()}',f'memory.swap.max={(base/"memory.swap.max").read_text().strip()}',f'cpu.max={(base/"cpu.max").read_text().strip()}',f'cpuset={(base/"cpuset.cpus.effective").read_text().strip()}',f'Cpus_allowed_list={allowed}',''))
def assert_host_cg(text, memory):
 d=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
 if not d.get('container_id') or d['container_id'][:12] not in d.get('host_cgroup','') or d.get('memory.swap.max')!='0' or d.get('cpuset') not in ('24-25','24,25') or int(d.get('memory.max','0')) != memory or d.get('cpu.max')!='200000 100000' or not d.get('Cpus_allowed_list'): raise RuntimeError('host cgroup identity/limits mismatch')
 return d
def snapshot(name, stem):
 stem.with_suffix('.docker-inspect.json').write_text(run(['docker','inspect',name],capture_output=True).stdout)
 stem.with_suffix('.mountinfo.txt').write_text(run(['docker','exec',name,'cat','/proc/self/mountinfo'],capture_output=True).stdout)
def assert_tmpfs(name, expected):
 info=json.loads(run(['docker','inspect',name],capture_output=True).stdout)[0]
 if (info.get('HostConfig',{}).get('Tmpfs') or {}) != expected: raise RuntimeError('tmpfs mount configuration mismatch')
def cleanup(a, **kw):
 try: subprocess.run(a,check=False,timeout=30,**kw)
 except subprocess.TimeoutExpired: pass
def capture_logs(name, path, values):
 try: result=subprocess.run(['docker','logs',name],check=False,capture_output=True,text=True,timeout=30)
 except subprocess.TimeoutExpired: return
 path.write_text(scrub(result.stdout+result.stderr,values))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--lease',required=True);ap.add_argument('--source',required=True);ap.add_argument('--expected-revision',required=True);ap.add_argument('--clippy-json',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 lease=json.load(open(a.lease));
 if lease.get('status')!='ACTIVE':raise RuntimeError('active root scan lease required')
 src=pathlib.Path(a.source).resolve(); raw=pathlib.Path(a.clippy_json).resolve(); out=pathlib.Path(a.out).resolve(); out.mkdir(parents=True,exist_ok=False); (out/'raw').mkdir()
 if not (src/'.git').exists() or subprocess.run(['git','-C',str(src),'status','--porcelain'],capture_output=True,text=True).stdout:raise RuntimeError('source must be clean immutable worktree')
 if subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()!=a.expected_revision:raise RuntimeError('source revision differs from expected')
 crate=src/'rust/cix-native'
 if not crate.is_dir():raise RuntimeError('--source must be worktree root containing rust/cix-native')
 if not raw.is_file():raise RuntimeError('missing root-produced Clippy JSON')
 server_digest=manifest(SERVER_REF); scanner_digest=manifest(SCANNER_REF)
 run(['docker','pull',f'{SERVER_REF}@{server_digest}']);run(['docker','pull',f'{SCANNER_REF}@{scanner_digest}'])
 (out/'raw/server-image-inspect.json').write_text(run(['docker','image','inspect',f'{SERVER_REF}@{server_digest}'],capture_output=True).stdout)
 (out/'raw/scanner-image-inspect.json').write_text(run(['docker','image','inspect',f'{SCANNER_REF}@{scanner_digest}'],capture_output=True).stdout)
 run(['docker','run','-d','--name',SERVER_NAME,'--hostname',SERVER_NAME,'--rm','-p','127.0.0.1:9014:9000','--cpuset-cpus','24,25','--cpu-quota','200000','--memory','4g','--memory-swap','4g','--tmpfs','/opt/sonarqube/data:rw,uid=1000,gid=0,size=1g','--tmpfs','/opt/sonarqube/logs:rw,uid=1000,gid=0,size=128m','--tmpfs','/opt/sonarqube/temp:rw,uid=1000,gid=0,size=1536m',f'{SERVER_REF}@{server_digest}'])
 assert_tmpfs(SERVER_NAME,{'/opt/sonarqube/data':'rw,uid=1000,gid=0,size=1g','/opt/sonarqube/logs':'rw,uid=1000,gid=0,size=128m','/opt/sonarqube/temp':'rw,uid=1000,gid=0,size=1536m'})
 password='Aa1!'+secrets.token_urlsafe(32); token=None; envfile=None
 try:
  for _ in range(90):
   try:
    if api('http://127.0.0.1:9014','/api/system/status','admin','admin').get('status')=='UP':break
   except Exception:pass
   time.sleep(2)
  else:raise RuntimeError('server did not become ready')
  try:
   api('http://127.0.0.1:9014','/api/users/change_password','admin','admin',urllib.parse.urlencode({'login':'admin','previousPassword':'admin','password':password}).encode())
  except urllib.error.HTTPError as error:
   (out/'raw/change-password-error.txt').write_text(scrub_http_error(error,[('admin','[ADMIN]'),(password,'[PASSWORD]'),(token,'[TOKEN]')]))
   raise RuntimeError('initial password change failed; retained scrubbed HTTP diagnostic')
  server_before=cg(SERVER_NAME); (out/'raw/server-cgroup-before.txt').write_text(server_before); assert_cg(server_before,4294967296,SERVER_NAME); server_host=host_cg(SERVER_NAME); (out/'raw/server-host-cgroup-before.txt').write_text(server_host); assert_host_cg(server_host,4294967296); snapshot(SERVER_NAME,out/'raw/server-before')
  token=api('http://127.0.0.1:9014','/api/user_tokens/generate','admin',password,b'name=cix-4af6') ['token']
  envfile=ROOT/'benchmark-work/sonar-4af6/.scanner-env';envfile.write_text('SONAR_HOST_URL=http://127.0.0.1:9014\nSONAR_TOKEN='+token+'\n');os.chmod(envfile,0o600)
  # Compact only duplicate Clippy target diagnostics; raw input stays copied.
  seen=set(); compact=[]
  for line in raw.open():
   x=json.loads(line);m=x.get('message',{});code=(m.get('code')or{}).get('code','')
   if x.get('reason')!='compiler-message' or m.get('level')!='warning' or not code.startswith('clippy::'):continue
   spans=[s for s in m.get('spans',[]) if s.get('is_primary')]
   key=(code,tuple((s.get('file_name'),s.get('line_start'),s.get('column_start')) for s in spans),m.get('message'))
   if key not in seen:seen.add(key);compact.append(x)
  (out/'raw/clippy-raw.jsonl').write_bytes(raw.read_bytes());(out/'raw/importer-accounting.json').write_text(json.dumps({'raw_clippy':sum(1 for line in raw.open() if 'clippy::' in line),'compact_attempted':len(compact)},indent=2));(out/'clippy-compact.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in compact))
  # The receipt barrier diagnoses the live scanner container once; it never releases a scan until the named role and limits verify.
  scanner_script="c=$(sed -n 's/^0:://p' /proc/self/cgroup); b=/sys/fs/cgroup; printf 'hostname=%s\ncgroup=%s\nmemory.max=%s\nmemory.peak=%s\nmemory.swap.max=%s\ncpu.max=%s\ncpuset=%s\n' \"$(cat /proc/sys/kernel/hostname)\" \"$c\" \"$(cat $b$c/memory.max)\" \"$(cat $b$c/memory.peak)\" \"$(cat $b$c/memory.swap.max)\" \"$(cat $b$c/cpu.max)\" \"$(cat $b$c/cpuset.cpus.effective)\" > /out/raw/scanner-cgroup-before.txt; sed -n 's/^Cpus_allowed_list:[[:space:]]*/Cpus_allowed_list=/p' /proc/self/status >> /out/raw/scanner-cgroup-before.txt; cat /proc/self/mountinfo > /out/raw/scanner-mountinfo.txt; : > /out/raw/scanner-ready; while [ ! -e /out/raw/scanner-go ]; do sleep 0.1; done; exec sonar-scanner \"$@\""
  scanner_cmd=['docker','run','-d','--name',SCANNER_NAME,'--hostname',SCANNER_NAME,'--network','host','--cpuset-cpus','24,25','--cpu-quota','200000','--memory','1g','--memory-swap','1g','--tmpfs','/tmp:rw,size=512m','--env','SONAR_USER_HOME=/tmp/.sonar','--env','SONAR_SCANNER_JAVA_OPTS=-Xmx512m','--env-file',str(envfile),'-v',f'{crate}:/usr/src:ro','-v',f'{out}:/out','-w','/usr/src','--entrypoint','sh',f'{SCANNER_REF}@{scanner_digest}','-c',scanner_script,'scanner-wrapper','-Dsonar.projectKey=cix-native-rust-local-4af6','-Dsonar.sources=src','-Dsonar.tests=tests,examples,benches','-Dsonar.scm.revision='+a.expected_revision,'-Dsonar.working.directory=/tmp/.scannerwork','-Dsonar.rust.clippy.enabled=false','-Dsonar.rust.clippyReport.reportPaths=/out/clippy-compact.jsonl']
  run(scanner_cmd)
  for _ in range(100):
   if (out/'raw/scanner-ready').exists(): break
   time.sleep(.1)
  else: raise RuntimeError('scanner did not reach receipt barrier')
  scanner_cg=(out/'raw/scanner-cgroup-before.txt').read_text(); assert_cg(scanner_cg,1073741824,SCANNER_NAME); scanner_host=host_cg(SCANNER_NAME); (out/'raw/scanner-host-cgroup-before.txt').write_text(scanner_host); assert_host_cg(scanner_host,1073741824); snapshot(SCANNER_NAME,out/'raw/scanner-before')
  assert_tmpfs(SCANNER_NAME,{'/tmp':'rw,size=512m'})
  (out/'raw/scanner-go').touch()
  scanner_exit=run(['docker','wait',SCANNER_NAME],capture_output=True).stdout.strip(); (out/'raw/scanner-exit.txt').write_text(scanner_exit+'\n'); capture_logs(SCANNER_NAME,out/'raw/scanner.log',[('admin','[ADMIN]'),(password,'[PASSWORD]'),(token,'[TOKEN]')])
  if scanner_exit!='0': raise RuntimeError('scanner exited nonzero')
  server_after=cg(SERVER_NAME); (out/'raw/server-cgroup-after.txt').write_text(server_after); assert_cg(server_after,4294967296,SERVER_NAME); server_host=host_cg(SERVER_NAME); (out/'raw/server-host-cgroup-after.txt').write_text(server_host); assert_host_cg(server_host,4294967296); snapshot(SERVER_NAME,out/'raw/server-after');
  task=None
  for line in (out/'raw/scanner.log').read_text().splitlines():
   if 'api/ce/task?id=' in line:task=line.rsplit('=',1)[-1]
  if not task:raise RuntimeError('missing CE task')
  for _ in range(60):
   ce=api('http://127.0.0.1:9014','/api/ce/task?id='+task,'admin',password)
   if ce['task']['status'] in ('SUCCESS','FAILED','CANCELED'):break
   time.sleep(1)
  (out/'raw/importer-drops.txt').write_text('\n'.join(x for x in (out/'raw/scanner.log').read_text().splitlines() if 'Failed to save Clippy diagnostic' in x)+'\n'); (out/'raw/ce-task.json').write_text(json.dumps(ce,indent=2))
  if ce['task']['status']!='SUCCESS':raise RuntimeError('compute engine did not succeed')
  issues=api('http://127.0.0.1:9014','/api/issues/search?componentKeys=cix-native-rust-local-4af6&resolved=false&ps=500','admin',password); all_issues=list(issues['issues']);
  for page in range(2, (issues['paging']['total']+499)//500+1): all_issues.extend(api('http://127.0.0.1:9014',f'/api/issues/search?componentKeys=cix-native-rust-local-4af6&resolved=false&ps=500&p={page}','admin',password)['issues'])
  issues['issues']=all_issues;(out/'raw/issues.json').write_text(json.dumps(issues,indent=2)); quality=api('http://127.0.0.1:9014','/api/qualitygates/project_status?projectKey=cix-native-rust-local-4af6','admin',password);(out/'raw/quality-gate.json').write_text(json.dumps(quality,indent=2))
  (out/'manifest.json').write_text(json.dumps({'source':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip(),'source_tree':subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD^{tree}'],text=True).strip(),'server_digest':server_digest,'scanner_digest':scanner_digest,'raw_clippy_sha256':digest(raw),'compact_records':len(compact),'current_issues':issues['paging']['total']},indent=2)+'\n')
 finally:
  if token:
   try: api('http://127.0.0.1:9014','/api/user_tokens/revoke','admin',password,b'name=cix-4af6'); (out/'raw/token-lifecycle.txt').write_text('revocation=success\n')
   except Exception: (out/'raw/token-lifecycle.txt').write_text('revocation=failed\n')
  if envfile:
   try:envfile.unlink()
   except FileNotFoundError:pass
  if not (out/'raw/scanner.log').exists():
   capture_logs(SCANNER_NAME,out/'raw/scanner.log',[('admin','[ADMIN]'),(password,'[PASSWORD]'),(token,'[TOKEN]')])
  cleanup(['docker','stop',SCANNER_NAME],capture_output=True)
  cleanup(['docker','rm','-f',SCANNER_NAME],capture_output=True)
  capture_logs(SERVER_NAME,out/'raw/server.log',[('admin','[ADMIN]'),(password,'[PASSWORD]'),(token,'[TOKEN]')])
  cleanup(['docker','stop',SERVER_NAME],capture_output=True)
if __name__=='__main__':main()
