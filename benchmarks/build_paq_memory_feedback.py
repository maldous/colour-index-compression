"""Causal memory-access predictions normalized relative to predicted prefixes.

This isolated fork extends one unused displacement mixer pair. It predicts from
the last access through the same base register, the same opcode/base pair, or
the previous access stride. All state comes from completed decoded fields.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from benchmarks import build_paq_gp_feedback as base

ROOT=Path(__file__).resolve().parents[1]


def patched(source):
    source=base.patched(source).replace('CIX_GP_FEEDBACK','CIX_MEMORY_FEEDBACK')
    old='''  uint32_t cixLast = 65536, cixPrevious = 65536, cixRegister[32]{};
  bool cixActive() const { return cixMode && op.Opcode == 0x29 && op.Rb == 29; }
  void cixSet() {
    uint64_t context = cixMode == 1 ? hash(count, op.Displacement, cixLast) :
      cixMode == 2 ? hash(count, op.Displacement, op.Ra, cixLast, cixPrevious) :
      hash(count, op.Displacement, op.Ra, cixRegister[op.Ra]);
    maps4[map_state(3, State::Mem_Displacement)].set(context);
  }'''
    new='''  uint32_t cixLastBase[32]{}, cixLastOp[64][32]{}, cixDelta[32]{};
  bool cixActive() const { return cixMode && op.Format==DECAlpha::Mem; }
  void cixSet() {
    uint32_t last=cixMode==2 ? cixLastOp[op.Opcode][op.Rb] : cixLastBase[op.Rb];
    bool known=last!=65536;
    uint32_t prediction=known ? (cixMode==3 ? (last+cixDelta[op.Rb])&65535 : last) : 0;
    assert(count<=12 && (count&3)==0);
    uint32_t prefixDifference=op.Displacement^(prediction>>(16-count));
    uint32_t predictedNibble=(prediction>>(12-count))&15;
    maps4[map_state(3, State::Mem_Displacement)].set(
      hash(count,op.Opcode,op.Rb,prefixDifference,predictedNibble,known));
  }'''
    reset_old='''      cixLast = cixPrevious = 65536;
      for (auto& value : cixRegister) value = 65536;'''
    reset_new='''      for(auto& value:cixLastBase) value=65536;
      for(auto& row:cixLastOp) for(auto& value:row) value=65536;
      for(auto& value:cixDelta) value=0;'''
    update_old='''              if (op.Opcode == 0x29 && op.Rb == 29) {
                cixPrevious = cixLast; cixLast = op.Displacement;
                cixRegister[op.Ra] = op.Displacement;
              }'''
    update_new='''              if(cixMode) {
                uint32_t previous=cixLastBase[op.Rb];
                cixDelta[op.Rb]=previous==65536 ? 0 : (op.Displacement-previous)&65535;
                cixLastBase[op.Rb]=op.Displacement;
                cixLastOp[op.Opcode][op.Rb]=op.Displacement;
              }'''
    for before,after in [(old,new),(reset_old,reset_new),(update_old,update_new)]:
        if source.count(before)!=1:raise ValueError('memory feedback insertion changed')
        source=source.replace(before,after)
    return source


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    root=ROOT/'benchmark-work/references/paq8px-cix-memory-feedback';target=root/'source';build=root/'build-local'
    if target.exists():raise ValueError('preserve existing memory feedback build')
    shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    model=Path('src/model/DecAlphaModel.hpp');(target/model).write_text(patched((original/model).read_text(encoding='utf-8-sig')))
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','2'],check=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(binary=str(build/'paq8px'),binary_sha256=sha(build/'paq8px'),builder_sha256=sha(Path(__file__)),
        base_builder_sha256=sha(Path(base.__file__)),model_sha256=sha(target/model),original_model_sha256=sha(original/model),
        upstream_source=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        mode_environment='CIX_MEMORY_FEEDBACK',modes={'0':'disabled exact control','1':'last base-register access','2':'last opcode/base access','3':'base-register stride'},
        causality='Only previously completed decoded fields; state reset per block; current prefix normalized against predicted displacement',
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (root/'provenance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':main()
