"""Build an isolated PAQ v215 trace/reconstruction bridge; never touch references."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    original=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
    target=ROOT/'benchmark-work/references/paq8px-cix-bridge/source'
    build=target.parent/'build-local'
    if not target.exists():shutil.copytree(original,target,ignore=shutil.ignore_patterns('.github','.git','build-local'))
    header=ROOT/'benchmarks/CixPredictionBridge.hpp';shutil.copyfile(header,target/'src/CixPredictionBridge.hpp')
    source=(original/'src/Encoder.cpp').read_text(encoding='utf-8-sig')
    substitutions=[
        ('#include "Encoder.hpp"','#include "Encoder.hpp"\n#include "CixPredictionBridge.hpp"'),
        ('if( doEncoding && mode == DECOMPRESS ) { // x = first 4 bytes of archive','if( doEncoding && mode == DECOMPRESS && !cix_bridge_enabled()) { // original arithmetic path'),
        ('      ari.encodeBit(p, y);','      cix_bridge().record(p,y);\n      ari.encodeBit(p, y);'),
        ('      int y = ari.decodeBit(p);','      int y = cix_bridge_enabled()?cix_bridge().decode(p):ari.decodeBit(p);'),
    ]
    for old,new in substitutions:
        if source.count(old)!=1:raise ValueError('upstream bridge insertion changed')
        source=source.replace(old,new)
    (target/'src/Encoder.cpp').write_text(source)
    main_source=(original/'src/paq8px.cpp').read_text(encoding='utf-8-sig')
    # Flush/check at normal program exit through an explicit main-path check.
    main_source='#include "CixPredictionBridge.hpp"\n'+main_source
    old='return processCommandLine(argc, argv);'
    if main_source.count(old)!=1:raise ValueError('missing Linux main path')
    main_source=main_source.replace(old,'int result=processCommandLine(argc, argv);\n  if(cix_bridge_enabled())cix_bridge().finish();\n  return result;')
    main_source=main_source.replace('int retval=processCommandLine(argc_utf8, argv_utf8);','int retval=processCommandLine(argc_utf8, argv_utf8);\n    if(cix_bridge_enabled())cix_bridge().finish();')
    (target/'src/paq8px.cpp').write_text(main_source)
    subprocess.run(['cmake','-S',str(target),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DNATIVECPU=OFF','-DDISABLE_ZLIB=OFF'],check=True)
    subprocess.run(['cmake','--build',str(build),'--parallel','6'],check=True)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(upstream=json.loads((ROOT/'benchmark-work/references/v215-source.json').read_text()),
        binary=str(build/'paq8px'),binary_sha256=digest(build/'paq8px'),bridge_sha256=digest(header),
        encoder_sha256=digest(target/'src/Encoder.cpp'),main_sha256=digest(target/'src/paq8px.cpp'),
        changes='Record original predictions; optionally feed independently decoded residual errors to the unchanged predictor. No model or probability changes.')
    (target.parent/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
