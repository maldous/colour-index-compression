"""Build an isolated causal GP-load feedback model without changing references.

The added context consumes only completed decoded instruction displacements.
Mode zero leaves its mixer inputs at zero and must match ordinary PAQ exactly.
Model selection is carried in the outer experimental frame, never uncounted.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def patched(source):
    edits = [
        ('#include "../IndirectMap.hpp"', '#include "../IndirectMap.hpp"\n#include <cstdlib>\n#include <stdexcept>'),
        ('0x440183,', '0x440383,'),
        ('maps4[6]', 'maps4[7]'),
        ('  uint8_t lastRc;', '''  uint8_t lastRc;
  const unsigned cixMode = []() {
    const char* value = std::getenv("CIX_GP_FEEDBACK");
    if (!value) return 0u;
    if (value[0] < '0' || value[0] > '3' || value[1])
      throw std::runtime_error("invalid CIX GP feedback mode");
    return unsigned(value[0] - '0');
  }();
  uint32_t cixLast = 65536, cixPrevious = 65536, cixRegister[32]{};
  bool cixActive() const { return cixMode && op.Opcode == 0x29 && op.Rb == 29; }
  void cixSet() {
    uint64_t context = cixMode == 1 ? hash(count, op.Displacement, cixLast) :
      cixMode == 2 ? hash(count, op.Displacement, op.Ra, cixLast, cixPrevious) :
      hash(count, op.Displacement, op.Ra, cixRegister[op.Ra]);
    maps4[map_state(3, State::Mem_Displacement)].set(context);
  }'''),
        ('    maps4{\n', '    maps4{\n'),
        ('      {sh, 16, 5, 256, 255}, // Mem_Rb\n      {sh, 16, 5, 256, 255}, // Opr_Ra',
         '      {sh, 16, 5, 256, 255}, // Mem_Rb\n      {sh, 18, 4, 256, 255}, // CIX causal GP displacement feedback\n      {sh, 16, 5, 256, 255}, // Opr_Ra'),
        ('      cache.fill(op = { 0 });', '''      cache.fill(op = { 0 });
      cixLast = cixPrevious = 65536;
      for (auto& value : cixRegister) value = 65536;'''),
        ('            maps3[map_state(2, State::Mem_Displacement)].set(hash(op.Opcode, op.Rb, cache(1).Literal));',
         '            maps3[map_state(2, State::Mem_Displacement)].set(hash(op.Opcode, op.Rb, cache(1).Literal));\n            if (cixActive()) cixSet();'),
        ('              maps3[map_state(2, State::Mem_Displacement)].set(hash(count, op.Opcode, op.Rb, cache(1).Literal, op.Displacement));',
         '              maps3[map_state(2, State::Mem_Displacement)].set(hash(count, op.Opcode, op.Rb, cache(1).Literal, op.Displacement));\n              if (cixActive()) cixSet();'),
        ('''        case State::Mem_Displacement: {''', '''        case State::Mem_Displacement: {'''),
        ('''            else {
              state = State::OpCode;
              count = 0;
            }
          }
          break;
        }
        case State::Mfc_Function:''', '''            else {
              if (op.Opcode == 0x29 && op.Rb == 29) {
                cixPrevious = cixLast; cixLast = op.Displacement;
                cixRegister[op.Ra] = op.Displacement;
              }
              state = State::OpCode;
              count = 0;
            }
          }
          break;
        }
        case State::Mfc_Function:'''),
        ('      if (((maps_mask[i] >> state) & 1) != 0)\n        maps[i][map_state(i, state)].mix(m);',
         '      if (((maps_mask[i] >> state) & 1) != 0 && !(i == 3 && state == State::Mem_Displacement && !cixActive()))\n        maps[i][map_state(i, state)].mix(m);'),
    ]
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError('upstream model insertion changed: '+old[:80])
        source = source.replace(old, new)
    return source


def main():
    original = ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root = ROOT/'benchmark-work/references/paq8px-cix-gp-feedback'; target = root/'source'; build = root/'build-local'
    if target.exists(): raise ValueError('preserve existing GP feedback build')
    shutil.copytree(original, target, ignore=shutil.ignore_patterns('.github', '.git', 'build-local'))
    relative = Path('src/model/DecAlphaModel.hpp')
    (target/relative).write_text(patched((original/relative).read_text(encoding='utf-8-sig')))
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),
                  upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
                  builder_sha256=sha(Path(__file__)),model_sha256=sha(target/relative),
                  original_model_sha256=sha(original/relative),mode_environment='CIX_GP_FEEDBACK',
                  modes={'0':'disabled exact control','1':'last completed GP load','2':'last two completed GP loads and destination register','3':'last GP load to the same register'},
                  metadata='one outer-frame mode byte; no external prediction or lookup input',
                  revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__ == '__main__':main()
