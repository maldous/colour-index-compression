import collections,hashlib,json,os,resource,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=Path(__file__).resolve().parents[5];out=r/"benchmark-work/native-rc-check-v1/cppcheck-header-canary-v4";out.mkdir()
tools=r.parent/"cix-sonar-cxx-tools";runtime=tools/"cppcheck-runtime-v2";manifest=json.loads((runtime/"manifest.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for row in [manifest["binary"],*manifest["dependencies"]]:assert sha(runtime/row["staged"])==row["sha256"]
assert sha(runtime/"usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2")==manifest["elf_loader"]["sha256"]
db=r/"docs/research/2026-10-04-execution/sonar-preparation/prepared-v4/compile_commands.host.json"
selected=[x for x in json.loads(db.read_text()) if "/adapters/gio/" in x["file"] or "/adapters/sevenzip/" in x["file"]]
assert len(selected)>=5
(out/"compile_commands.json").write_text(json.dumps(selected,indent=2)+"\n")
lib=runtime/"usr/lib/x86_64-linux-gnu";cfg=lib/"cppcheck/cfg"
arch=Path("/usr/lib/x86_64-linux-gnu");overlay=out/"arch-overlay";overlay.mkdir();alias=Path("/mnt");assert alias.is_dir()
for child in arch.iterdir():(overlay/child.name).symlink_to(alias/child.name)
assert not (overlay/"cppcheck").exists()
(overlay/"cppcheck").symlink_to(lib/"cppcheck")
mounts=["bwrap","--die-with-parent","--ro-bind","/","/","--ro-bind",str(arch),str(alias),"--ro-bind",str(overlay),str(arch),"--"]
visible=arch/"glib-2.0/include/glibconfig.h"
check=subprocess.run([*mounts,"/usr/bin/sha256sum",str(visible)],capture_output=True,text=True)
assert check.returncode==0,check.stderr
assert check.stdout.split()[0]==sha(visible)
arguments=[*mounts,str(lib/"ld-linux-x86-64.so.2"),"--library-path",str(lib),str(runtime/"usr/bin/cppcheck"),"--xml","--xml-version=2","--enable=warning,style,performance,portability,information","--platform=unix64","--max-configs=12","-j","2","--library="+str(cfg/"std.cfg"),"--library="+str(cfg/"posix.cfg"),"--project="+str(out/"compile_commands.json")]
# Only the inherited stdout/stderr descriptors are writable inside bubblewrap.
# Each is hard-capped to 2MiB by RLIMIT_FSIZE; source and all other mounts are read-only.
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
with (out/"stdout.log").open("wb") as stdout,(out/"report.xml").open("wb") as stderr:
 result=subprocess.run(arguments,cwd=r,stdout=stdout,stderr=stderr,preexec_fn=limits,timeout=120)
errors=list(ET.parse(out/"report.xml").iter("error")) if result.returncode==0 else []
receipt={"argv":arguments,"returncode":result.returncode,"selected_sources":{x["file"]:sha(Path(x["file"])) for x in selected},"input_compilation_database_sha256":sha(db),"runtime_manifest_sha256":sha(runtime/"manifest.json"),"diagnostics":dict(collections.Counter(x.get("id") for x in errors)),"fatal_configuration":[ET.tostring(x,encoding="unicode") for x in errors if x.get("id") in {"syntaxError","unknownMacro","preprocessorErrorDirective"}],"per_output_hard_cap_bytes":2*1024**2,"host_glibconfig_sha256_visible_inside_sandbox":check.stdout.split()[0],"arch_overlay":{"host_alias":str(alias),"entries":len(list(arch.iterdir())),"host_children_unchanged":True,"only_added_leaf":"cppcheck","all_mounts_readonly":True}}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
raise SystemExit(result.returncode or bool(receipt["fatal_configuration"]))
