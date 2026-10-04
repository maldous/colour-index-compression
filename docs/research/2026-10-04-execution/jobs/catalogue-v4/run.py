import subprocess,json
from pathlib import Path
commands=[['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'check', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-catalogue-v4/Cargo.toml', '--all-targets'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'build', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-catalogue-v4/Cargo.toml', '--lib', '--bin', 'cix'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-catalogue-v4/Cargo.toml', '--lib', 'full_engine::', '--', '--test-threads=1'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-catalogue-v4/Cargo.toml', '--lib', 'raw_payload', '--', '--test-threads=1'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-catalogue-v4/Cargo.toml', '--test', 'c_stream_contract', '--', '--test-threads=1']]
results=[]
for command in commands:
 print('CHECK',command,flush=True)
 result=subprocess.run(command,check=False)
 results.append({'command':command,'exit_code':result.returncode})
 if result.returncode and command[1] in ('check','build'):break
Path(__file__).with_name('checks.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(1 if any(x['exit_code'] for x in results) else 0)
