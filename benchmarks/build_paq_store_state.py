"""Isolate PAQ v216's level-zero decoder-state fix; keep references immutable.

DecodeBlockHeader and recursive filter decoding use predictorMain->shared even
when arithmetic coding is disabled. Supply only that state, with a fail-fast
probability method. Nonzero compression paths are unchanged.
"""
import json
from pathlib import Path
import shutil
import subprocess
from benchmarks.competitive_codec import sha

ROOT = Path(__file__).resolve().parents[1]


def patch(text):
    old = '    Encoder en(predictorBlock.get(), predictorMain.get(), doEncoding, mode, &archive);'
    new = '''    if (!doEncoding) {
      struct StoredState final : Predictor {
        explicit StoredState(Shared* sh) : Predictor(sh) {}
        uint32_t p() override {
          quit("Unexpected probability request in stored mode.");
          return 0;
        }
      };
      predictorMain = std::make_unique<StoredState>(&shared);
    }
    Encoder en(predictorBlock.get(), predictorMain.get(), doEncoding, mode, &archive);'''
    if text.count(old) != 1: raise ValueError('upstream construction changed')
    return text.replace(old, new)


def main():
    original=ROOT/'benchmark-work/references/paq8px-v216/paq8px-216'
    root=ROOT/'benchmark-work/references/paq8px-cix-store-state'; target=root/'source'; build=root/'build-local'
    if target.exists(): raise ValueError('preserve existing store-state build')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.git','.github','build-local'))
    unit=Path('src/paq8px.cpp'); (target/unit).write_text(patch((original/unit).read_text(encoding='utf-8-sig')))
    with (root/'build.log').open('w') as log:
        subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['cmake','--build',str(build),'--parallel','2'],stdout=log,stderr=subprocess.STDOUT,check=True)
    report=dict(binary=str(build/'paq8px'),binary_sha256=sha((build/'paq8px').read_bytes()),
                original_unit_sha256=sha((original/unit).read_bytes()),patched_unit_sha256=sha((target/unit).read_bytes()),
                builder_sha256=sha(Path(__file__).read_bytes()),upstream_source=json.loads((ROOT/'benchmark-work/references/v216-source.json').read_text()),
                scope='Level zero retains Shared state without allocating a probability model; reference binaries and higher-level code paths untouched.',
                revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report),flush=True)


if __name__=='__main__': main()
