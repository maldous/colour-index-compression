import json
import os
from pathlib import Path
import subprocess

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
root = Path(__file__).resolve().parents[5]
w = root / 'benchmark-work/native-rc-check-v1'
src = w / 'squashfs-source-v1'
out = w / 'squashfs-host-v2'
out.mkdir(exist_ok=False)
rows = []

def run(args, cwd=None, env=None):
    result = subprocess.run(list(map(str, args)), cwd=cwd or out,
                            env={**os.environ, **(env or {})}, capture_output=True, text=True)
    rows.append(dict(argv=list(map(str, args)), cwd=str(cwd or out), env_extra=env or {},
                     returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    (out / 'receipt.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(list(map(str, args)), result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:] or result.stdout[-6000:])

profile = src / 'profile'
run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
     '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + str(profile / 'include'),
     profile / 'src/cix_squashfs_profile.c', profile / 'tests/profile_contract.c',
     '-o', out / 'profile-sanitized'])
run([out / 'profile-sanitized'], env={'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                                    'UBSAN_OPTIONS': 'halt_on_error=1'})
run(['cmake', '-S', profile, '-B', out / 'profile-build', '-DCMAKE_BUILD_TYPE=Release'])
run(['cmake', '--build', out / 'profile-build', '-j4'])
run([out / 'profile-build/cix_squashfs_profile_contract'])
project = out / 'differential'
(project / 'src').mkdir(parents=True)
(project / 'Cargo.toml').write_text('[package]\nname="cix-squashfs-differential"\nversion="0.0.0"\nedition="2021"\n[dependencies]\ncix-portable={path="' + str(w / 'portable-source-v1/cix-portable') + '"}\n')
(project / 'build.rs').write_text('fn main(){println!("cargo:rustc-link-search=native=' + str(out / 'profile-build') + '");println!("cargo:rustc-link-lib=static=cix_squashfs_profile");}\n')
(project / 'src/main.rs').write_text('#[path="' + str(profile / 'tests/native_differential.rs') + '"] mod differential;\n' + '''
fn main() {
    let mut cases = 0;
    for size in (0usize..=512).chain([8192, 131072]) {
        for mode in 0..3 {
            let input: Vec<u8> = (0..size).map(|i| match mode {
                0 => 65, 1 => ((i / 7 + i / 31) % 5) as u8,
                _ => ((i * 12345 + (i * i >> 3)) & 255) as u8,
            }).collect();
            differential::compare_one(&input, false);
            if size <= 8192 { differential::compare_one(&input, true); }
            cases += 1;
        }
    }
    println!("native adaptive/profile exact-choice cases={cases}");
}
''')
run(['cargo', 'run', '--offline', '--manifest-path', project / 'Cargo.toml'])
upstream = w / 'squashfs-tools-source-v1/squashfs-tools'
build = out / 'tools-build'
build.mkdir()
run(['make', '-I', upstream, '-f', src / 'tools/cix-tools.mk', '-j4', 'cix-tools',
     'UPSTREAM=' + str(upstream), 'PROFILE=' + str(profile),
     'GZIP_SUPPORT=1', 'XZ_SUPPORT=0', 'LZO_SUPPORT=0', 'LZ4_SUPPORT=0', 'ZSTD_SUPPORT=0',
     'XATTR_SUPPORT=1'], cwd=build)
run(['sh', src / 'tools/qualify.sh'], env={
    'CIX_MKSQUASHFS': str(build / 'cix-mksquashfs'),
    'CIX_UNSQUASHFS': str(build / 'cix-unsquashfs'), 'TMPDIR': str(out)})
