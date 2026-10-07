"""PAQ source/segmentation diagnostics, explicitly separate from scored results.

Upstream -0 decoding failed locally. These encode-only traces are used to inspect
detected paths, never as evidence of lossless compression or leaderboard sizes.
"""
import concurrent.futures
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'benchmark-work/references/paq8px-v215/paq8px-215'
OUT=ROOT/'results/leaderboard/paq-v215-paths'


def member(item):
    source=ROOT/item['path'];name=source.name;prior=ROOT/'results/leaderboard/paq-v215-segmentation'/name/'encode.log'
    if source.stat().st_size!=item['size'] or hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('source identity mismatch')
    if prior.exists():log=prior.read_bytes();origin='previous encode-only trace; decoding failed'
    elif (OUT/(name+'.log')).exists():log=(OUT/(name+'.log')).read_bytes();origin='reused encode-only trace; no decoding attempted'
    else:
        path=OUT/(name+'.log');archive=OUT/(name+'.diagnostic.paq8px215')
        with path.open('wb') as output:
            subprocess.run([str(ROOT/'benchmark-work/references/paq8px-v215/build-local/paq8px'),'-0',str(source),str(archive)],stdout=output,stderr=subprocess.STDOUT,check=True)
        log=path.read_bytes();origin='new encode-only trace; no decoding attempted'
        archive.unlink()  # An unverified diagnostic archive is never retained as a benchmark artifact.
    (OUT/(name+'.log')).write_bytes(log)
    text=log.decode(errors='replace')
    # stdout block descriptions and stderr progress can interleave mid-word.
    text=re.sub(r'(?:Compressing\.\.\.\s*)?\d{1,3}\.\d{2}%\x08*','',text).replace('\x08','')
    known_types={re.sub(r'\s+','',name):name for name in ('default','text','text - eol','tar','tar header','dec-alpha','zlib','x86/64','jpeg','png','image 8-bit','image 24-bit','base64','base85','gif','audio','dbf')}
    blocks=[dict(id=m[0],type=known_types.get(re.sub(r'\s+','',m[1]),m[1].strip()),size=int(m[2]),start=int(m[3]),end=int(m[4]))
            for m in re.findall(r'(\d+(?:-\d+)*)\s*\|\s*([^|\n]+)\s*\|\s*(\d+)\s+bytes\s*\[(\d+)\s*-\s*(\d+)\]',text)]
    counts=Counter(b['type'] for b in blocks)
    return dict(file=name,original=item['size'],input_sha256=item['sha256'],origin=origin,
                encode_only=True,round_trip=False,scored=False,log_sha256=hashlib.sha256(log).hexdigest(),
                detected_types=dict(counts),blocks=blocks,
                note='Nested transformed ranges may overlap or expand. Do not sum these as original-byte coverage.')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    items=json.loads((ROOT/'results/silesia-manifest.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(4) as pool:rows=list(pool.map(member,items))
    contexts=[]
    for p in sorted((SOURCE/'src/model').glob('ContextModel*.cpp')):
        text=p.read_text(encoding='utf-8-sig')
        contexts.append(dict(source=str(p.relative_to(SOURCE)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            models=sorted(set(re.findall(r'(\w+)\s*&\s*\w+\s*=\s*models->',text)))))
    result=dict(reference='paq8px v215',binary_sha256=hashlib.sha256((ROOT/'benchmark-work/references/paq8px-v215/build-local/paq8px').read_bytes()).hexdigest(),
        options='-0',purpose='Source-path diagnostics only; not a compression benchmark',members=rows,context_model_membership=contexts,
        marginal_savings_status='Not measured. A detector path or model comment does not establish causal byte savings; controlled compression ablations remain required.')
    (OUT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    for row in rows:print(row['file'],row['detected_types'],flush=True)


if __name__=='__main__':main()
