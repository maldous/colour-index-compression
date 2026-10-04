import subprocess,json
from pathlib import Path
results=[]
for command in [['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v13/Cargo.toml', '--lib', 'cli::', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v13/Cargo.toml', '--lib', 'paq_bridge::', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v13/Cargo.toml', '--lib', 'paq_worker::', '--', '--test-threads=2']]:
 print("CHECK",command,flush=True)
 result=subprocess.run(command)
 results.append({"command":command,"exit_code":result.returncode})
Path(__file__).with_name("checks.json").write_text(json.dumps(results,indent=2)+"\n")
raise SystemExit(1 if any(x["exit_code"] for x in results) else 0)
