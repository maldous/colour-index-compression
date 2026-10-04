import collections,hashlib,json,os,resource,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=Path(__file__).resolve().parents[5];out=r/"benchmark-work/native-rc-check-v1/cppcheck-header-canary-v1";out.mkdir()
tools=r.parent/"cix-sonar-cxx-tools";runtime=tools/"cppcheck-runtime-v2";manifest=json.loads((runtime/"manifest.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for row in [manifest["binary"],*manifest["dependencies"]]:assert sha(runtime/row["staged"])==row["sha256"]
assert sha(runtime/"usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2")==manifest["elf_loader"]["sha256"]
db=r/"docs/research/2026-10-04-execution/sonar-preparation/prepared-v4/compile_commands.host.json"
selected=[x for x in json.loads(db.read_text()) if "/adapters/gio/" in x["file"] or "/adapters/7zip/" in x["file"]]
assert len(selected)>=2
(out/"compile_commands.json").write_text(json.dumps(selected,indent=2)+"\n")
arguments=["bwrap","--die-with-parent","--ro-bind","/","/","--dir","/cix-private","--ro-bind",str(runtime/"usr/bin/cppcheck"),"/cix-private/cppcheck","--ro-bind",str(runtime/"usr/lib/x86_64-linux-gnu"),"/cix-private/lib","--ro-bind",str(runtime/"usr/lib/x86_64-linux-gnu/cppcheck/cfg"),"/usr/lib/x86_64-linux-gnu/cppcheck/cfg","--","/cix-private/lib/ld-linux-x86-64.so.2","--library-path","/cix-private/lib","/cix-private/cppcheck","--xml","--xml-version=2","--enable=warning,style,performance,portability,information","--platform=unix64","--max-configs=12","-j","2","--library=/usr/lib/x86_64-linux-gnu/cppcheck/cfg/std.cfg","--library=/usr/lib/x86_64-linux-gnu/cppcheck/cfg/posix.cfg","--project="+str(out/"compile_commands.json")]
# Only the inherited stdout/stderr descriptors are writable inside bubblewrap.
# Each is hard-capped to 2MiB by RLIMIT_FSIZE; source and all other mounts are read-only.
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
with (out/"stdout.log").open("wb") as stdout,(out/"report.xml").open("wb") as stderr:
 result=subprocess.run(arguments,cwd=r,stdout=stdout,stderr=stderr,preexec_fn=limits,timeout=120)
errors=list(ET.parse(out/"report.xml").iter("error")) if result.returncode==0 else []
receipt={"argv":arguments,"returncode":result.returncode,"selected_sources":{x["file"]:sha(Path(x["file"])) for x in selected},"input_compilation_database_sha256":sha(db),"runtime_manifest_sha256":sha(runtime/"manifest.json"),"diagnostics":dict(collections.Counter(x.get("id") for x in errors)),"fatal_configuration":[ET.tostring(x,encoding="unicode") for x in errors if x.get("id") in {"syntaxError","unknownMacro","preprocessorErrorDirective"}],"per_output_hard_cap_bytes":2*1024**2}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
raise SystemExit(result.returncode or bool(receipt["fatal_configuration"]))
