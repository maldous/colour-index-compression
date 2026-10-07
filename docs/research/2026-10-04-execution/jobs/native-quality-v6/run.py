import json,subprocess
from pathlib import Path
job=Path(__file__).resolve().parent
commands={'format': ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'fmt', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-native-quality-v6/Cargo.toml', '--check'], 'clippy': ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'clippy', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-native-quality-v6/Cargo.toml', '--all-targets', '--locked', '--offline', '--', '-D', 'warnings']}
results={}
for label,command in commands.items():
 with (job/(label+".stdout.log")).open("w") as out,(job/(label+".stderr.log")).open("w") as err:
  r=subprocess.run(command,stdout=out,stderr=err)
 results[label]={"argv":command,"returncode":r.returncode}
(job/"receipt.json").write_text(json.dumps(results,indent=2)+"\n")
raise SystemExit(any(x["returncode"] for x in results.values()))
