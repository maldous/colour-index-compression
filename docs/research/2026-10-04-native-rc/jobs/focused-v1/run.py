import subprocess,sys
from pathlib import Path
root=Path('/home/user/src/colour-index-compression')
cargo='/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo'
manifest='/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/native-focused-v1/Cargo.toml'
common=['--locked','--offline','--manifest-path',manifest]
commands=[[cargo,'check',*common,'--all-targets'],[cargo,'test',*common,'--lib','full_engine::','--','--test-threads=4'],[cargo,'test',*common,'--test','native_context','--test','parallel_pipeline','--test','paq_bridge_contract','--','--test-threads=4'],[sys.executable,'-m','unittest','discover','-s',str(root/'tools/sonar-cxx'),'-p','test_*.py','-v']]
for command in commands:
 print('CHECK',command,flush=True)
 result=subprocess.run(command,cwd=root,check=False)
 if result.returncode: raise SystemExit(result.returncode)
