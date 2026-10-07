"""Build an isolated coder-only causal register prior, preserving native PAQ state."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT/'benchmarks/native/CixRegisterPrior.hpp'


def replace_once(source, old, new):
    if source.count(old) != 1: raise ValueError('upstream register insertion changed: '+old[:80])
    return source.replace(old, new)


def patches(hpp, cpp):
    hpp = replace_once(hpp, '#include "PredictorBlock.hpp"', '#include "PredictorBlock.hpp"\n#include "CixRegisterPrior.hpp"')
    hpp = replace_once(hpp, '  ArithmeticEncoder ari;', '  ArithmeticEncoder ari;\n  CixRegisterPrior cixRegister;')
    prediction = '''      uint32_t codedP = p;
      if (predictor == predictorMain) {
        const auto& s = predictor->shared->State;
        codedP = cixRegister.mix(p, s.blockType == BlockType::DEC_ALPHA, s.blockPos, s.bitPosition);
      }
'''
    cpp = replace_once(cpp, '      ari.encodeBit(p, y);', prediction + '''      cixRegister.record(p, y);
      ari.encodeBit(codedP, y);
      if (predictor == predictorMain) cixRegister.observe(y);''')
    cpp = replace_once(cpp, '      int y = ari.decodeBit(p);', prediction + '''      int y = ari.decodeBit(codedP);
      if (predictor == predictorMain) cixRegister.observe(y);''')
    return hpp, cpp


def main():
    original = ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root = ROOT/'benchmark-work/references/paq8px-cix-register-prior'; target = root/'source'; build = root/'build-local'
    if target.exists(): raise ValueError('preserve existing register prior build')
    shutil.copytree(original, target, ignore=shutil.ignore_patterns('.github', '.git', 'build-local'))
    relatives = [Path('src/Encoder.hpp'), Path('src/Encoder.cpp')]
    output = patches(*[(original/p).read_text(encoding='utf-8-sig') for p in relatives])
    for path, source in zip(relatives, output): (target/path).write_text(source)
    shutil.copyfile(HEADER, target/'src/CixRegisterPrior.hpp')
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        source_hashes={str(p):sha(p) for p in [Path(__file__),HEADER,*[target/p for p in relatives]]},
        original_hashes={str(p):sha(original/p) for p in relatives}, mode_environment='CIX_REGISTER_PRIOR',
        modes={'0':'disabled exact control','1':'shared register recency 1/8 on ambiguous bits',
               '2':'shared register recency 1/32 on ambiguous bits','3':'shared register recency 1/8 on all register bits'},
        metadata='one paid outer-frame mode byte; only completed register fields; no external lookup',
        invariant='PAQ updateModels receives original p; only arithmetic encoder/decoder receive mixed p',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result),flush=True)


if __name__ == '__main__': main()
