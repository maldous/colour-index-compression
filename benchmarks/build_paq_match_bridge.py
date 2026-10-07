"""Isolated PAQ match-elimination build; preserve all running references."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    target=ROOT/'benchmark-work/references/paq8px-cix-match/source';build=target.parent/'build-local'
    if not target.exists():shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    header=ROOT/'benchmarks/CixMatchBridge.hpp';shutil.copyfile(header,target/'src/CixMatchBridge.hpp')
    source=(original/'src/Encoder.cpp').read_text(encoding='utf-8-sig')
    replacements=[
        ('#include "Encoder.hpp"','#include "Encoder.hpp"\n#include "CixMatchBridge.hpp"'),
        ('      ari.encodeBit(p, y);','''      if(i==7)cix_match().start(predictor==predictorMain?predictor->shared->State.Match.expectedByte:256,
          predictor==predictorMain?predictor->shared->State.Match.mode3:0,c);
      cix_match().record(p,y);
      if(!cix_match().forced(7-i))ari.encodeBit(p,y);'''),
        ('      int y = ari.decodeBit(p);','''      if(i==0)cix_match().start(predictor==predictorMain?predictor->shared->State.Match.expectedByte:256,
          predictor==predictorMain?predictor->shared->State.Match.mode3:0);
      int y=cix_match().forced(i)?cix_match().value(i):ari.decodeBit(p);'''),
    ]
    for old,new in replacements:
        if source.count(old)!=1:raise ValueError('upstream insertion point changed')
        source=source.replace(old,new)
    (target/'src/Encoder.cpp').write_text(source)
    source='#include "CixMatchBridge.hpp"\n'+(original/'src/paq8px.cpp').read_text(encoding='utf-8-sig')
    source=source.replace('return processCommandLine(argc, argv);','int result=processCommandLine(argc, argv);\n  cix_match().finish();\n  return result;')
    source=source.replace('int retval=processCommandLine(argc_utf8, argv_utf8);','int retval=processCommandLine(argc_utf8, argv_utf8);\n    cix_match().finish();')
    (target/'src/paq8px.cpp').write_text(source)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF','-DDISABLE_ZLIB=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','6'],check=True)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(upstream=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),binary=str(build/'paq8px'),
                binary_sha256=sha(build/'paq8px'),bridge_sha256=sha(header),encoder_sha256=sha(target/'src/Encoder.cpp'),
                main_sha256=sha(target/'src/paq8px.cpp'),changes='Preserve predictions and updates. Code first mismatch against existing PAQ match candidate; force eliminated prefix and mismatch bits; arithmetic-code only unresolved suffix bits.')
    (target.parent/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
