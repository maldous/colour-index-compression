import pathlib,os,json,runpy,sys
path=next(x.split(":",2)[2] for x in pathlib.Path("/proc/self/cgroup").read_text().splitlines() if x.startswith("0::"))
cg=pathlib.Path("/sys/fs/cgroup"+path)
value={"path":path,"memory.max":(cg/"memory.max").read_text().strip(),"memory.swap.max":(cg/"memory.swap.max").read_text().strip(),"affinity":sorted(os.sched_getaffinity(0))}
assert value["memory.max"]=="1073741824" and value["memory.swap.max"]=="0" and value["affinity"]==[16],value
print(json.dumps({"resource_guard":value}),flush=True)
script=sys.argv.pop(1);sys.argv[0]=script
runpy.run_path(script,run_name="__main__")
