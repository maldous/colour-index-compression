"""Create an isolated source-only research bundle and rebuild its dependencies.

No network, GitHub, workflows, corpus bytes, cached streams or existing binaries
are copied. Upstream PAQ source and its notices are preserved. Existing build
outputs are never overwritten. Use --build-only inside an extracted bundle.
"""
import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LIBRARIES=('native_ppm','native_mixer_rounding','native_ppm_decode','native_legacy_mixer')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage(destination):
    if destination.exists():raise ValueError('use a new destination; existing source/build directories are preserved')
    destination.mkdir(parents=True)
    tracked=subprocess.check_output(['git','ls-files','cix','benchmarks','tests'],cwd=ROOT,text=True).splitlines()
    selected=[p for p in tracked if Path(p).suffix in ('.py','.cpp','.h','.hpp')]
    selected+=['docs/research/competitive-reproduction.md']
    for name in selected:
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    for version in ('v215','v216'):
        base=Path('benchmark-work/references')/('paq8px-'+version)
        source=base/('paq8px-'+version[1:])
        shutil.copytree(ROOT/source,destination/source,ignore=shutil.ignore_patterns('.git','.github','__pycache__','build-local'))
        provenance=Path('benchmark-work/references')/(version+'-source.json')
        shutil.copy2(ROOT/provenance,destination/provenance)
    fix=Path('benchmark-work/references/v216-build-fix.json');shutil.copy2(ROOT/fix,destination/fix)
    (destination/'requirements-research.txt').write_text('numpy==2.5.3\nimagecodecs==2026.8.16\nbrotli==1.2.0\nzstandard==0.25.0\n')
    (destination/'REPRODUCE.md').write_text('''# CIX experimental source reproduction

This is a local source-release candidate, not an official leaderboard entry.
Python 3.12, a C++17 compiler, CMake and an AVX2-capable Linux x86-64 system were
used for qualification. Install requirements-research.txt into a virtual
environment, then run from this directory:

    python -m benchmarks.reproduce_build --build-only --jobs 3
    python -m benchmarks.competitive_cli encode input.bin output.cix
    python -m benchmarks.competitive_cli decode output.cix restored.bin
    cmp input.bin restored.bin

The build script performs no network or CI operations. Input/output paths must
be distinct, and the codec refuses existing destinations. Encoding may be slow:
it tries the whole portfolio and independently verifies its selected stream.

PAQ8px v215/v216 source, original copyright/license notices, upstream revision
and archive hashes are included. The documented v216 include-case correction
is applied. Bundled zlib retains its own notices. NumPy, imagecodecs (including
JPEG XL/JPEG-LS/JPEG 2000), Brotli and Zstandard remain external dependencies;
their licenses and notices apply. CIX is research source; no new license grant
or official submission is implied by this staging operation.

SOURCE-MANIFEST.json records every staged file hash and the CIX source revision.
BUILD-RESULT.json records local rebuilt binary hashes. Benchmark corpora and
saved compressed outputs are deliberately absent. See
docs/research/competitive-reproduction.md for measurement and cache discipline.
''')
    files={str(p.relative_to(destination)):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()}
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    (destination/'SOURCE-MANIFEST.json').write_text(json.dumps(dict(source_revision=revision,files=files),indent=2)+'\n')
    return files


def run_logged(command,root,log):
    with log.open('wb') as out:subprocess.run(command,cwd=root,stdout=out,stderr=subprocess.STDOUT,check=True)


def build(root,jobs):
    paths=[root/'results/leaderboard'/(name+'.so') for name in LIBRARIES]
    paths += [root/'benchmark-work/references'/('paq8px-'+v)/'build-local/paq8px' for v in ('v215','v216')]
    if any(p.exists() for p in paths):raise ValueError('existing binary preserved; rebuild in a fresh extracted source directory')
    manifest=json.loads((root/'SOURCE-MANIFEST.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(root/name)!=digest:raise ValueError('staged source changed: '+name)
    logs=root/'build-logs';logs.mkdir(exist_ok=True);(root/'results/leaderboard').mkdir(parents=True,exist_ok=True)
    def native(name):
        run_logged(['g++','-std=c++17','-O3','-ffp-contract=off','-fPIC','-shared',
            'benchmarks/'+name+'.cpp','-o','results/leaderboard/'+name+'.so'],root,logs/(name+'.log'))
        print('built '+name,flush=True)
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool:list(pool.map(native,LIBRARIES))
    for version in ('v215','v216'):
        base=root/'benchmark-work/references'/('paq8px-'+version)
        source=base/('paq8px-'+version[1:]);out=base/'build-local'
        run_logged(['cmake','-S',str(source),'-B',str(out),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],root,logs/(version+'-configure.log'))
        run_logged(['cmake','--build',str(out),'--parallel',str(jobs)],root,logs/(version+'-build.log'))
        print('built paq8px '+version,flush=True)
    for name,digest in manifest['files'].items():
        if sha(root/name)!=digest:raise ValueError('source mutated while building: '+name)
    result=dict(source_revision=manifest['source_revision'],binaries={str(p.relative_to(root)):sha(p) for p in paths},
        compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],github_actions_used=False)
    (root/'BUILD-RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destination',type=Path);p.add_argument('--archive',type=Path)
    p.add_argument('--jobs',type=int,default=3);p.add_argument('--build-only',action='store_true');args=p.parse_args()
    if not 1<=args.jobs<=16:p.error('jobs must be between 1 and 16')
    if args.build_only:
        if args.destination or args.archive:p.error('build-only takes neither destination nor archive')
        build(ROOT,args.jobs);return
    if args.destination is None:p.error('destination is required for staging')
    root=args.destination.resolve();files=stage(root)
    if args.archive:
        with tarfile.open(args.archive,'x:gz') as archive:
            for name in [*files,'SOURCE-MANIFEST.json']:archive.add(root/name,arcname=name,recursive=False)
        print('source archive: '+str(args.archive),flush=True)
    build(root,args.jobs)


if __name__=='__main__':main()
