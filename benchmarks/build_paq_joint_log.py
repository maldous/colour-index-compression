"""Isolated memory feedback plus deterministic adaptive register prior."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from benchmarks import build_paq_memory_feedback as memory, build_paq_register_prior as register
from benchmarks.build_paq_register_log import HEADERS

ROOT = Path(__file__).resolve().parents[1]


def main():
    original = ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root = ROOT/'benchmark-work/references/paq8px-cix-joint-log'; target = root/'source'; build = root/'build-local'
    if target.exists(): raise ValueError('preserve existing joint log fork')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    model = Path('src/model/DecAlphaModel.hpp')
    source = memory.patched((original/model).read_text(encoding='utf-8-sig'))
    source = register.replace_once(source,'CIX_MEMORY_FEEDBACK','CIX_JOINT_LOG')
    source = register.replace_once(source,"    return unsigned(value[0] - '0');","    return value[0] == '1' || value[0] == '3' ? 2u : 0u;")
    (target/model).write_text(source)
    edits = [Path('src/Encoder.hpp'),Path('src/Encoder.cpp')]
    for path,text in zip(edits,register.patches(*[(original/p).read_text(encoding='utf-8-sig') for p in edits])):
        (target/path).write_text(text)
    for name in HEADERS:
        source = (ROOT/'benchmarks/native'/name).read_text()
        if name == 'CixLogRegisterPrior.hpp':
            source = register.replace_once(source,'CIX_REGISTER_LOG','CIX_JOINT_LOG')
            source = register.replace_once(source,"      mode = v[0] - '0';","      mode = v[0] == '2' || v[0] == '3' ? 1u : 0u;")
            name = 'CixRegisterPrior.hpp'
        (target/'src'/name).write_text(source)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    paths = [Path(__file__),Path(memory.__file__),Path(memory.base.__file__),Path(register.__file__),
        ROOT/'benchmarks/build_paq_register_log.py',*[ROOT/'benchmarks/native'/n for n in HEADERS],
        *[target/p for p in [model,*edits,Path('src/CixRegisterPrior.hpp'),Path('src/CixLogMath.hpp'),Path('src/CixLogTables.hpp')]]]
    result = dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),source_hashes={str(p):sha(p) for p in paths},
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        mode_environment='CIX_JOINT_LOG',modes={'0':'disabled','1':'opcode/base memory feedback alone','2':'adaptive register prior alone','3':'both'},
        invariant='Memory feedback adds PAQ contexts. Register prior changes coding probabilities but retains original PAQ updates. Integer tables only.',
        metadata='one paid outer mode byte; causal state reset per Alpha block',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)


if __name__ == '__main__': main()
