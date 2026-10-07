import subprocess
commands=[['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'check', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/native-focused-v4/Cargo.toml', '--all-targets'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/native-focused-v4/Cargo.toml', '--lib', 'full_engine::', '--', '--test-threads=4']]
for command in commands:
 print("CHECK",command,flush=True)
 result=subprocess.run(command,check=False)
 if result.returncode: raise SystemExit(result.returncode)
