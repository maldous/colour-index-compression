"""Generated reference-only palette fixtures; no evaluation data is accessed."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
reference = Path('/home/user/src/cix-integrated-source-candidate/runtime')
sys.path.insert(0, str(reference))
from cix_runtime.legacy import sdf_geometry

area = Path(__file__).resolve().parent
fixtures = area / 'palette-vectors'
fixtures.mkdir(exist_ok=False)
atoms = [(b'C', (10000, 20000, 0)), (b'H', (10000, 20000, 0)),
         (b'N', (-5000, 5000, 0)), (b'O', (10000, 20000, 0)),
         (b'Xe', (-5000, 5000, 0)), (b'C', (30000, -10000, 100))]
record = b'generated palette record\nnative parity\n\n  6  3  0  0  0  0            999 V2000\n'
for element, vector in atoms:
    record += b''.join(sdf_geometry.fixed(value) for value in vector)
    record += b' ' + element.ljust(3) + b' 0  0  0\n'
record += b'  1  3  1  0  0  0\n  2  4  1  0  0  0\n  1  6  1  0  0  0\nM  END\n'
source = record + b'$$$$\nliteral retained\n$$$$\n' + record
(fixtures / 'palette.input').write_bytes(source)
for mode in range(3):
    for size in [1, 2, 64]:
        archive, stats = sdf_geometry.encode(source, mode, 2, size)
        assert stats['atoms'] == 12
        assert sdf_geometry.decode(archive) == source
        (fixtures / f'palette-{mode}-{size}.frame').write_bytes(archive)
manifest = {'scope': 'generated palette, group and escape compatibility fixtures',
    'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(fixtures.iterdir())},
    'references': {name: hashlib.sha256((reference / 'cix_runtime/legacy' / name).read_bytes()).hexdigest()
                   for name in ['sdf_geometry.py', 'multinomial.py']}}
(area / 'palette-vectors.json').write_text(json.dumps(manifest, indent=2) + '\n')
print({'files': len(manifest['files']), 'input_bytes': len(source)})
