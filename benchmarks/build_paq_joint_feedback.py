"""Isolated memory/register interaction with explicit individual ablations.

Mode0 disables both; mode1 uses opcode/base memory feedback; mode2 uses the
qualified register prior; mode3 combines them. No existing fork is modified.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from benchmarks import build_paq_memory_feedback as memory, build_paq_register_prior as register

ROOT=Path(__file__).resolve().parents[1]


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root=ROOT/'benchmark-work/references/paq8px-cix-joint-feedback';target=root/'source';build=root/'build-local'
    if target.exists():raise ValueError('preserve existing joint feedback fork')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    model=Path('src/model/DecAlphaModel.hpp')
    source=memory.patched((original/model).read_text(encoding='utf-8-sig'))
    source=register.replace_once(source,'CIX_MEMORY_FEEDBACK','CIX_JOINT_FEEDBACK')
    source=register.replace_once(source,"    return unsigned(value[0] - '0');","    return value[0] == '1' || value[0] == '3' ? 2u : 0u;")
    (target/model).write_text(source)
    headers=[Path('src/Encoder.hpp'),Path('src/Encoder.cpp')]
    for path,text in zip(headers,register.patches(*[(original/p).read_text(encoding='utf-8-sig') for p in headers])):
        (target/path).write_text(text)
    source=register.HEADER.read_text()
    source=register.replace_once(source,'CIX_REGISTER_PRIOR','CIX_JOINT_FEEDBACK')
    source=register.replace_once(source,"      mode = v[0] - '0';","      mode = v[0] == '2' || v[0] == '3' ? 1u : 0u;")
    (target/'src/CixRegisterPrior.hpp').write_text(source)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    paths=[Path(__file__),Path(memory.__file__),Path(memory.base.__file__),Path(register.__file__),register.HEADER,
           *[target/p for p in [model,*headers,Path('src/CixRegisterPrior.hpp')]]]
    result=dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),
        source_hashes={str(p):sha(p) for p in paths},
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        mode_environment='CIX_JOINT_FEEDBACK',
        modes={'0':'disabled exact control','1':'memory opcode/base feedback alone',
               '2':'register recency 1/8 ambiguous alone','3':'memory and register feedback together'},
        metadata='single outer-frame mode byte; all state causal and reset per block',
        invariant='Register mixture does not change probabilities fed to PAQ model updates; memory mode intentionally adds mixer context.',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
