"""Build isolated deterministic causal log-domain register prediction."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from benchmarks import build_paq_register_prior as base

ROOT=Path(__file__).resolve().parents[1]
HEADERS=['CixLogRegisterPrior.hpp','CixLogMath.hpp','CixLogTables.hpp']


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root=ROOT/'benchmark-work/references/paq8px-cix-register-log';target=root/'source';build=root/'build-local'
    if target.exists():raise ValueError('preserve existing native log-prior fork')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    edits=[Path('src/Encoder.hpp'),Path('src/Encoder.cpp')]
    for path,text in zip(edits,base.patches(*[(original/p).read_text(encoding='utf-8-sig') for p in edits])):
        (target/path).write_text(text)
    for name in HEADERS:
        destination='CixRegisterPrior.hpp' if name=='CixLogRegisterPrior.hpp' else name
        shutil.copyfile(ROOT/'benchmarks/native'/name,target/'src'/destination)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=[Path(__file__),Path(base.__file__),*[ROOT/'benchmarks/native'/n for n in HEADERS],*[target/p for p in edits]]
    result=dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),
        source_hashes={str(p):sha(p) for p in paths},
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        mode_environment='CIX_REGISTER_LOG',modes={'0':'disabled exact control','1':'opcode/field log mixture',
        '2':'opcode/field log mixture with native prior bias8','3':'previous fixed gated1/8 control'},
        invariant='All codec probability calculations use pinned integer tables. Original PAQ p updates remain unchanged.',
        metadata='one paid outer-frame mode byte; no source, prediction trace or future field table used by decoder',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
