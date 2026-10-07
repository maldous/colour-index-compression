from pathlib import Path
import json,subprocess,hashlib
A=Path(__file__).resolve().parent;R=A.parents[2];W=R/'benchmark-work/release-g1-controls-final';W.mkdir(exist_ok=True);B=Path('/home/user/src/cix-0.1-artifacts/final/bin');src=R/'benchmark-work/canterbury/kennedy.xls'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
configs=[('baseline','64KiB','512MiB'),('block-only','16KiB','512MiB'),('memory-only','64KiB','256MiB')]
freeze={'input_sha256':sha(src),'binary_sha256':sha(B/'cix'),'configs':configs,'threads':1,'cpu':8,'format':'cixg1','parallelism':'blocks','effort':'default','observation':'One observation each; altered block size may change complete archive, memory-only may change admission; no universal speed claim'};(A/'g1-final-controls-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n');rows=[]
for name,block,memory in configs:
 archive=W/f'{name}.cix';timer=W/f'{name}.time';log=W/f'{name}.stderr'
 cmd=['/usr/bin/time','-v','-o',str(timer),str(B/'cix'),'--format','cixg1','--parallelism','blocks','--threads','1','--block-size',block,'--memory',memory,'-f','-o',str(archive),str(src)]
 p=subprocess.run(cmd,capture_output=True,text=True);log.write_text(p.stderr)
 if p.returncode:raise RuntimeError(name+' encoding failed')
 restored=W/f'{name}.restored';q=subprocess.run([str(B/'uncix'),'-f','-o',str(restored),str(archive)],capture_output=True,text=True)
 if q.returncode or sha(restored)!=sha(src):raise RuntimeError(name+' restoration failed')
 rows.append({'config':name,'block':block,'memory':memory,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'restore':'VERIFIED','time_file':str(timer),'command':cmd})
(A/'g1-final-controls-results.json').write_text(json.dumps({'status':'PASS','rows':rows},indent=2)+'\n')
