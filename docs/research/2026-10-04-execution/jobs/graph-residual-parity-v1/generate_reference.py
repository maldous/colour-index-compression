#!/usr/bin/env python3
import sys,os,resource,json,hashlib
from pathlib import Path
os.sched_setaffinity(0,{8})
resource.setrlimit(resource.RLIMIT_AS,(500_000_000,500_000_000))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
resource.setrlimit(resource.RLIMIT_FSIZE,(1_000_000,1_000_000))
sys.dont_write_bytecode=True
root=Path('/home/user/src/colour-index-compression')
job=Path(__file__).resolve().parent
for name,digest in json.loads((job/'read-only-inputs.json').read_text()).items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
sys.path.insert(0,str(root/'runtime'))
from cix_runtime.legacy import sdf_hydrogen
fx=root/'rust/cix-native/tests/fixtures/graph_residual_parity'
data=(fx/'hydrogen.input').read_bytes()
results=[]
for model in range(3):
    for representation in range(4):
        frame,info=sdf_hydrogen.encode(data,model=model,representation=representation,radius=6200)
        assert sdf_hydrogen.decode(frame)==data
        assert len(frame)<1_000_000
        name=f'hydrogen-{model}-{representation}.frame'
        (fx/name).write_bytes(frame)
        results.append(dict(name=name,bytes=len(frame),sha256=hashlib.sha256(frame).hexdigest(),info=info))
(job/'reference-generation.json').write_text(json.dumps(dict(interpreter=sys.version,executable=sys.executable,frames=results),indent=2)+'\n')
from cix_runtime.legacy import sdf_geometry
from collections import Counter
preserved=[]
for mode in range(3):
    for representation in range(2):
        name=f'graph-{mode}-{representation}.frame'
        inp=(fx/'graph.input').read_bytes()
        expected=(fx/name).read_bytes()
        assert sdf_geometry.encode(inp,mode=mode,representation=representation)[0]==expected
        assert sdf_geometry.decode(expected)==inp
        preserved.append(name)
    for palette in [1,2,64]:
        name=f'palette-{mode}-{palette}.frame'
        inp=(fx/'palette.input').read_bytes()
        expected=(fx/name).read_bytes()
        assert sdf_geometry.encode(inp,mode=mode,representation=2,palette_size=palette)[0]==expected
        assert sdf_geometry.decode(expected)==inp
        preserved.append(name)
records,skel,flags,vectors,groups,parsed=sdf_geometry._extract_records((fx/'palette.input').read_bytes(),2)
counts=Counter(vectors)
boundary=b'palette boundary\nnative parity\ngenerated source\n 65  0  0  0  0  0            999 V2000\n'
for i in range(65):
    boundary += (f'{i:5d}.0000    0.0000    0.0000 C   0  0  0\n').encode()
boundary += b'M  END\n'
_,_,_,bv,bg,bp=sdf_geometry._extract_records(boundary,0)
assert bp==1 and len(set(bv))==65 and all(c==1 for c in Counter(bv).values())
bframe,_=sdf_geometry.encode(boundary,mode=0,representation=2,palette_size=64)
assert sdf_geometry.decode(bframe)==boundary
(fx/'palette-boundary.input').write_bytes(boundary)
(fx/'palette-boundary-0-64.frame').write_bytes(bframe)
(job/'preserved-reference-audit.json').write_text(json.dumps(dict(frames=preserved,palette_unique_vectors=len(counts),palette_counts=list(counts.values()),parsed_records=parsed,boundary_unique_vectors=65,boundary_frequency_ties=True,boundary_palette_size=64),indent=2)+'\n')
print('Generated/reference-decoded 12 hydrogen frames; 15 preserved graph/palette frames match current reference; native checks unrun.')
