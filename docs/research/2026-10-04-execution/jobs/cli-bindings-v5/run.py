import subprocess
commands = [['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'check', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-cli-bindings-v5/Cargo.toml', '--all-targets'], ['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'test', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-cli-bindings-v5/Cargo.toml', '--test', 'cli_smoke', '--test', 'implicit_stdin_cli', '--test', 'standard_formats_cli', '--test', 'selection_overrides', '--test', 'auto_best_portfolio', '--', '--test-threads=1']]
for command in commands:
 print('CHECK', command, flush=True)
 result = subprocess.run(command, check=False)
 if result.returncode: raise SystemExit(result.returncode)

subprocess.run(['/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo', 'build', '--locked', '--offline', '--manifest-path', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-cli-bindings-v5/Cargo.toml', '--lib', '--bin', 'cix'],check=True)
subprocess.run(['python3', '/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/cli-bindings-v5/check_optional_bindings.py', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-cli-bindings-v5', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1', '/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/cli-bindings-v5', 'cli-bindings-v5'],check=True)
