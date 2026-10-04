import subprocess
commands = [['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'check', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-window-v1/Cargo.toml', '--all-targets'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-window-v1/Cargo.toml', '--lib', 'full_engine::window_stream', '--', '--test-threads=2'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-window-v1/Cargo.toml', '--test', 'window_cli', '--test', 'window_transport', '--test', 'full_engine_constraints', '--test', 'cli_full_engine', '--', '--test-threads=2']]
for command in commands:
 print('CHECK', command, flush=True)
 result = subprocess.run(command, check=False)
 if result.returncode: raise SystemExit(result.returncode)
