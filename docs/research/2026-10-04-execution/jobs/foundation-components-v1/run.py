import subprocess,shutil
from pathlib import Path
commands=[['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/Cargo.toml', '--lib', 'jxl_bridge::', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/Cargo.toml', '--lib', 'paq_supervisor::', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/Cargo.toml', '--lib', 'c_api::', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/Cargo.toml', '--test', 'native_context', '--test', 'c_api_contract', '--test', 'native_port_vectors', '--test', 'cli_smoke', '--test', 'streaming_pipe', '--', '--test-threads=2']]
for command in commands:
 print("CHECK",command,flush=True)
 result=subprocess.run(command,check=False)
 if result.returncode: raise SystemExit(result.returncode)
stage=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/c-api-stage-foundation-components-v1')
(stage/"lib").mkdir(parents=True)
(stage/"include").mkdir()
shutil.copy2('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/include/cix.h',stage/"include/cix.h")
shutil.copy2('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/target/debug/libcix_native.so',stage/"lib/libcix_native.so")
subprocess.run(["sh",'/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-foundation-v9/tests/c_api_installed_consumer.sh',str(stage),str(stage/"consumer")],check=True)
