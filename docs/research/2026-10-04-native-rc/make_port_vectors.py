"""Generate tiny golden vectors from the preserved reference, never runtime code."""
from pathlib import Path
import hashlib,io,json,struct,sys,tarfile
REF=Path('/home/user/src/cix-integrated-source-candidate/runtime')
sys.dont_write_bytecode=True
sys.path.insert(0,str(REF))
from cix_runtime.legacy import sdf_geometry,ecoff_pointer_deltas
area=Path(__file__).resolve().parent
fixtures=area/'port-vectors'
fixtures.mkdir(exist_ok=False)
# Canonical grammar fixture built from fields, with both a recognised record and
# literal regions; no corpus file is read by this generator.
record=b'coordinate fixture\nnative\n\n  1  0  0  0  0  0            999 V2000\n    1.0000   -2.0000    0.5000 C   0  0  0\nM  END\n'
graph=record+b'$$$$\nordinary literal bytes\n$$$$\n'
(fixtures/'graph.input').write_bytes(graph)
for mode in range(3):
 for representation in range(2):
  encoded,_=sdf_geometry.encode(graph,mode,representation)
  assert sdf_geometry.decode(encoded)==graph
  (fixtures/f'graph-{mode}-{representation}.frame').write_bytes(encoded)
# Valid Alpha ECOFF with two actual relocated pointers, embedded in a TAR.
names=b'\0alpha\0beta\0';virtual=0x120002000
symbols=b''.join(struct.pack('<IIQIBBH',off,0,value,0,0x12,0,0xff01) for off,value in zip((0,1,7),(0,99,42)))
relocations=b''.join(struct.pack('<QII',virtual+8*i,(symbol<<8)|2,0) for i,symbol in enumerate((1,2)))
parts=((b'.dynstr',0,names),(b'.dynsym',0,symbols),(b'.hash',0,struct.pack('<7I',2,3,0,0,0,0,0)),(b'.rdata',virtual,struct.pack('<2Q',99,42)),(b'.rel.dyn',0,relocations))
obj=bytearray(104+64*len(parts));struct.pack_into('<HHIQIHH',obj,0,0x183,len(parts),0,0,0,80,0x2007)
for i,(name,address,raw) in enumerate(parts):
 offset=len(obj);obj.extend(raw);struct.pack_into('<8sQQQQQQHHI',obj,104+64*i,name,address,address,len(raw),offset,0,0,0,0,0)
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as archive:
 info=tarfile.TarInfo('nested-object');info.size=len(obj);archive.addfile(info,io.BytesIO(obj))
source=stream.getvalue()+b'ordinary trailing bytes';(fixtures/'pointer.input').write_bytes(source)
for mode in range(6):
 encoded,stats=ecoff_pointer_deltas.transform(source,mode);assert stats['mapped_pointers']==2;assert ecoff_pointer_deltas.inverse(encoded)==source
 (fixtures/f'pointer-{mode}.frame').write_bytes(encoded)
files={str(p.relative_to(fixtures)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(fixtures.iterdir())}
sources={str(p.relative_to(REF)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((REF/'cix_runtime/legacy').glob('*.py'))}
(area/'port-vectors.json').write_text(json.dumps({'scope':'generated focused reference fixtures; not evaluation corpus','files':files,'reference_sources':sources,'pointer_fields':2},indent=2)+'\n')
print(json.dumps({'fixture_files':len(files),'total_bytes':sum(p.stat().st_size for p in fixtures.iterdir())}))
