from pathlib import Path
import hashlib,json,subprocess,tempfile,sys,os
root=Path('/home/user/src/colour-index-compression')
base=root/'benchmark-work/combined-45e7-validation/final'
candidate=root/'benchmark-work/root-decode-current/target/debug'
work=Path(tempfile.mkdtemp(prefix='cix-root-decode-matrix-'))
source=work/'input.bin';source.write_bytes(bytes(range(16))*128)
records=[]
for name,flags in [('g1raw',['--fast','--stream','--format','cixg1','--route','raw']),('g1composition',['--fast','--stream','--format','cixg1','--route','composition']),('g2raw',['--fast','--stream','--format','cixg2','--route','raw']),('m6',['--fast','--format','cixm6']),('b1',['--external','bzip2'])]:
 case={'name':name,'commands':[]}
 memory = '512MiB' if name == 'b1' else '128MiB'
 for label,directory in [('parent',base),('candidate',candidate)]:
  archive=work/(name+'.'+label+'.cix')
  cmd=[str(directory/'cix'),*flags,'--threads','1','--memory',memory,'-f','-o',str(archive),str(source)]
  r=subprocess.run(cmd,capture_output=True);case['commands'].append({'command':cmd,'exit':r.returncode,'stderr':r.stderr.decode(errors='replace')});print(json.dumps(case['commands'][-1]),flush=True);(work/'partial.json').write_text(json.dumps(case,indent=2));assert r.returncode==0
  for decoder_label,decoder in [('parent',base/'uncix'),('candidate',candidate/'uncix')]:
   restored=work/(name+'.'+label+'.'+decoder_label+'.bin');cmd=[str(decoder),'--memory','128MiB','-f','-o',str(restored),str(archive)];r=subprocess.run(cmd,capture_output=True)
   case['commands'].append({'command':cmd,'exit':r.returncode,'stderr':r.stderr.decode(errors='replace'),'restored_sha256':hashlib.sha256(restored.read_bytes()).hexdigest() if restored.exists() else None});assert r.returncode==0 and restored.read_bytes()==source.read_bytes()
 a=(work/(name+'.parent.cix')).read_bytes();b=(work/(name+'.candidate.cix')).read_bytes();assert a==b
 case['archive_sha256']=hashlib.sha256(b).hexdigest();case['archive_bytes']=len(b)
 bad=work/(name+'.truncated.cix');bad.write_bytes(b[:-1]);cmd=[str(candidate/'uncix'),'--memory','128MiB','-c',str(bad)];r=subprocess.run(cmd,capture_output=True);case['commands'].append({'command':cmd,'exit':r.returncode,'stderr':r.stderr.decode(errors='replace'),'stdout_bytes':len(r.stdout)});assert r.returncode==2
 records.append(case)
result={'purpose':'root decoder helper compatibility, not throughput measurement','affinity':sorted(os.sched_getaffinity(0)),'cgroup_readback':{f:(Path('/sys/fs/cgroup') / Path(Path('/proc/self/cgroup').read_text().split(':',2)[2].strip()).relative_to('/') / f).read_text().strip() for f in ['memory.max','memory.swap.max','cpuset.cpus.effective']},'input_bytes':source.stat().st_size,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_main_sha256':hashlib.sha256((root/'rust/cix-native/src/main.rs').read_bytes()).hexdigest(),'binary_sha256':{str(d/name):hashlib.sha256((d/name).read_bytes()).hexdigest() for d in [base,candidate] for name in ['cix','uncix']},'cases':records}
(root/'benchmark-work/rust-performance-audit/root-decode-matrix.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'cases':len(records),'status':'PASS','work':str(work)}))
