import subprocess
commands=[['cmake', '-S', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-v215-build-v1-bridge', '-B', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-v215-build-v1-output', '-DCMAKE_BUILD_TYPE=Release', '-DCIX_PAQ_SOURCE_ROOT=/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-v215-build-v1-vendor', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'], ['cmake', '--build', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/paq-v215-build-v1-output', '--parallel', '4']]
for command in commands:
 print("STEP",command,flush=True)
 subprocess.run(command,check=True)
