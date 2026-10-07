import hashlib,json,os,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[4]
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
x=json.loads((OUT/"inputs.json").read_text())
def verify():return all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in x.items())
assert verify()
env={**os.environ,"CIX_NODE_ADDON":str(ROOT/"benchmark-work/native-rc-check-v1/node-unwrap-v2/build/cix_node.node"),"LD_LIBRARY_PATH":str(ROOT/"benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8/lib")}
r=subprocess.run(["/usr/bin/node",str(ROOT/"rust/cix-native/bindings/node/test/contract.js")],env=env,capture_output=True,text=True,timeout=60)
(OUT/"stdout.log").write_text(r.stdout);(OUT/"stderr.log").write_text(r.stderr)
unchanged=verify();passed=r.returncode==0 and unchanged
(OUT/"receipt.json").write_text(json.dumps({"status":"pass" if passed else "fail","returncode":r.returncode,"inputs_unchanged":unchanged,"source_and_artifact_sha256":x,"scope":"same optimized v2 Node addon and retained SDK; corrected lifecycle fixture expected messages; bad receivers reject without a specific engine/CIX wording claim; null native-wrapper branch not explicitly reached"},indent=2)+"\n")
if not passed:raise RuntimeError("Node contract failed")
