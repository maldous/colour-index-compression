import json, os, subprocess
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE") == "1"
job=Path(__file__).resolve().parent
root=job.parents[4]
source=root/"benchmark-work/native-rc-check-v1/execution-portable-loader-policy-v2"
cargo="/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo"
commands={"format":[cargo,"fmt","--manifest-path",str(source/"Cargo.toml"),"--check"],"clippy":[cargo,"clippy","--manifest-path",str(source/"Cargo.toml"),"--all-targets","--locked","--offline","--","-D","warnings"]}
results={}
for label,command in commands.items():
 with (job/(label+".stdout.log")).open("w") as out,(job/(label+".stderr.log")).open("w") as err:
  p=subprocess.run(command,stdout=out,stderr=err,check=False)
 results[label]={"argv":command,"returncode":p.returncode}
(job/"receipt.json").write_text(json.dumps(results,indent=2)+"\n")
raise SystemExit(any(x["returncode"] for x in results.values()))
