import hashlib,json,pathlib,subprocess,signal,time,os
source=pathlib.Path("/tmp/cix-encode-qual/sig-input");out=pathlib.Path("/tmp/cix-encode-qual/root-sig-output")
assert not out.exists()
binary=pathlib.Path("/tmp/cix-encode-candidate-target/release/cix")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(source);command=[str(binary),"--best","--stream","--memory","128MiB","-o",str(out),str(source)]
p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
 start=time.monotonic();temporary=None
 while time.monotonic()-start<5:
  names=list(out.parent.glob("."+out.name+".cix-tmp-*"))
  if names and names[0].stat().st_size>0:temporary=str(names[0]);break
  if p.poll() is not None:raise RuntimeError("encoder ended before observed partial output")
  time.sleep(.001)
 assert temporary is not None
 p.send_signal(signal.SIGINT);stdout,stderr=p.communicate(timeout=10)
 cg=next(x.split(":",2)[2] for x in pathlib.Path("/proc/self/cgroup").read_text().splitlines() if x.startswith("0::"));base=pathlib.Path("/sys/fs/cgroup"+cg)
 r={"command":command,"binary_sha256":sha(binary),"input_bytes":source.stat().st_size,"source_before":before,"source_after":sha(source),"signal":"SIGINT after observing nonempty atomic temporary output","temporary_observed":temporary,"exit_code":p.returncode,"stdout_bytes":len(stdout),"stderr":stderr.decode(),"output_exists":out.exists(),"temporary_remaining":[str(x) for x in out.parent.glob("."+out.name+".cix-tmp-*")],"cgroup":{"memory.max":(base/"memory.max").read_text().strip(),"memory.swap.max":(base/"memory.swap.max").read_text().strip(),"affinity":sorted(os.sched_getaffinity(0))}}
 pathlib.Path("/tmp/cix-encode-qual/root-signal.json").write_text(json.dumps(r,indent=2)+"\n")
 assert p.returncode==2 and not out.exists() and not r["temporary_remaining"] and before==r["source_after"],r
finally:
 if p.poll() is None:p.kill();p.wait()
