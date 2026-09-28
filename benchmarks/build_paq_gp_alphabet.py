"""Isolated PAQ experiment feeding causal CIX alphabet state into the mixer.

Observed symbol multiplicities and alphabet occupancy define two distributions
over 16-bit GP-load displacements. Each retains uniform escape mass over the
entire alphabet; unseen symbols are never declared impossible. This is a test
of structural feedback, not a claim that rank coding beats arithmetic coding.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HEADER = r'''#pragma once
#include <array>
#include <cassert>
#include <cstdint>
class CixGpAlphabet {
  std::array<uint32_t, 131072> frequency{};
  std::array<uint32_t, 131072> occupancy{};
public:
  void reset() { frequency.fill(0); occupancy.fill(0); }
  void observe(uint32_t value) {
    assert(value < 65536);
    // Bound arithmetic for arbitrarily long blocks without losing occupancy.
    if (frequency[1] >= (1u << 20)) {
      for (uint32_t i=65536; i<131072; ++i) frequency[i]=(frequency[i]+1)/2;
      for (uint32_t i=65535; i>0; --i) frequency[i]=frequency[2*i]+frequency[2*i+1];
    }
    uint32_t node=65536+value;
    const bool fresh=frequency[node]==0;
    while(node) { ++frequency[node]; occupancy[node]+=fresh; node>>=1; }
  }
  int probability(uint32_t prefix, uint32_t depth, bool unique) const {
    assert(depth<16 && prefix<(1u<<depth));
    const auto& tree=unique ? occupancy : frequency;
    uint32_t node=(1u<<depth)+prefix;
    // Dirichlet mass 16 spread uniformly over all 65,536 possible values.
    uint64_t span=1u<<(16-depth);
    uint64_t numerator=uint64_t(tree[2*node+1])*65536+8*span;
    uint64_t denominator=uint64_t(tree[node])*65536+16*span;
    int p=int((4096*numerator+denominator/2)/denominator);
    return p<1 ? 1 : p>4095 ? 4095 : p;
  }
};
'''


def patched(source):
    edits=[
        ('#include "../IndirectMap.hpp"', '#include "../IndirectMap.hpp"\n#include "../Stretch.hpp"\n#include "CixGpAlphabet.hpp"\n#include <cstdlib>\n#include <stdexcept>'),
        ('  uint8_t lastRc;', '''  uint8_t lastRc;
  CixGpAlphabet cixAlphabet;
  const unsigned cixMode = []() {
    const char* value=std::getenv("CIX_GP_ALPHABET");
    if (!value) return 0u;
    if (value[0]<'0' || value[0]>'3' || value[1])
      throw std::runtime_error("invalid CIX alphabet feedback mode");
    return unsigned(value[0]-'0');
  }();
  bool cixActive() const { return cixMode && op.Opcode==0x29 && op.Rb==29; }
  void cixMix(Mixer& m, bool unique) {
    const int p=cixAlphabet.probability(op.Displacement,count,unique);
    m.add(stretch(p)); m.add((p-2048)>>1);
  }'''),
        ('      cache.fill(op = { 0 });', '      cache.fill(op = { 0 });\n      if(cixMode) cixAlphabet.reset();'),
        ('''            else {
              state = State::OpCode;
              count = 0;
            }
          }
          break;
        }
        case State::Mfc_Function:''', '''            else {
              if(cixActive()) cixAlphabet.observe(op.Displacement);
              state = State::OpCode;
              count = 0;
            }
          }
          break;
        }
        case State::Mfc_Function:'''),
        ('''      if (((maps_mask[i] >> state) & 1) != 0)
        maps[i][map_state(i, state)].mix(m);''', '''      if (state==State::Mem_Displacement && cixActive() &&
          ((i==3 && (cixMode==1 || cixMode==3)) ||
           (i==4 && (cixMode==2 || cixMode==3))))
        cixMix(m,i==4);
      else if (((maps_mask[i] >> state) & 1) != 0)
        maps[i][map_state(i, state)].mix(m);''')]
    for old,new in edits:
        if source.count(old)!=1: raise ValueError('alphabet insertion changed: '+old[:80])
        source=source.replace(old,new)
    return source


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root=ROOT/'benchmark-work/references/paq8px-cix-gp-alphabet'; target=root/'source'; build=root/'build-local'
    if target.exists(): raise ValueError('preserve earlier alphabet build')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    model=Path('src/model/DecAlphaModel.hpp'); header=Path('src/model/CixGpAlphabet.hpp')
    (target/model).write_text(patched((original/model).read_text(encoding='utf-8-sig')))
    (target/header).write_text(HEADER)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),builder_sha256=sha(Path(__file__)),
        model_sha256=sha(target/model),header_sha256=sha(target/header),original_model_sha256=sha(original/model),
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        mode_environment='CIX_GP_ALPHABET',modes={'0':'disabled exact control','1':'multiplicity','2':'alphabet occupancy','3':'both'},
        prediction='past completed GP loads only; per-block reset; uniform escape over every 16-bit value',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
