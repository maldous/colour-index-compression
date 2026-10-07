"""Add independently restored geometric candidate-slot prediction."""
import json
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode, vdecode
from benchmarks import competitive_constraint_refresh as parent
from benchmarks import competitive_chemical as chemical
from benchmarks import sdf_hydrogen as hydrogen, sdf_hydrogen_probe as framed
from benchmarks.competitive_codec import sha, paq_binary

NAME = 'CIX competitive PAQ/structural constraint portfolio 9'
SOURCES = [__file__, hydrogen.__file__, framed.__file__]


def encode_frame(data, options='-8'):
    raw, _ = hydrogen.encode(data, 2, 0)
    with tempfile.TemporaryDirectory(prefix='cix-slots-') as folder:
        source = Path(folder)/'input.sdfh'
        archive = Path(folder)/'stream.paq8px215'
        source.write_bytes(raw)
        subprocess.run([paq_binary('v215'), options, '-simd', 'AVX2', str(source), str(archive)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return framed.MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+archive.read_bytes()


def qualify(data, folder, options='-8', require_complete=True):
    folder = Path(folder)
    record = folder/'complete.json'
    row = json.loads(record.read_text())
    if not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member')):
        raise ValueError('incomplete hydrogen trial')
    if (row['model'],row['representation'],row['options'],row['offset']) != (2,0,options,0):
        raise ValueError('hydrogen policy mismatch')
    if len(data) != row['original_bytes'] or sha(data) != row['input_sha256']:
        raise ValueError('hydrogen input mismatch')
    if sha(Path(hydrogen.__file__).read_bytes()) != row['codec_source_sha256'] or sha(Path(paq_binary('v215')).read_bytes()) != row['backend_sha256']:
        raise ValueError('hydrogen implementation changed')
    frame = (folder/'stream.cixq').read_bytes()
    if len(frame) != row['physical_bytes'] or sha(frame) != row['frame_sha256'] or frame[:5] != framed.MAGIC:
        raise ValueError('hydrogen physical stream changed')
    n, pos = vdecode(frame, 5)
    if n != len(data) or int.from_bytes(frame[pos:pos+4],'big') != zlib.crc32(data) or frame[pos+4:] != (folder/'stream.paq8px215').read_bytes():
        raise ValueError('hydrogen frame/archive mismatch')
    raw, _ = hydrogen.encode(data, 2, 0)
    if sha(raw) != row['transformed_sha256'] or raw != (folder/'input.sdfh').read_bytes() or hydrogen.decode(raw) != data:
        raise ValueError('hydrogen structural mismatch')
    return frame, dict(kind='completed independent full-frame decode reused', measurement=row,
        measurement_path=str(record.resolve()), measurement_sha256=sha(record.read_bytes()),
        decoder_source_sha256=sha(Path(framed.__file__).read_bytes()),
        structural_stage_recomputed_and_inverted=True, frame_sha256=sha(frame), input_sha256=sha(data))


def additions(data, cache=None):
    if not chemical.recognizes(data): return []
    t = time.perf_counter()
    proof = None
    if cache: frame, proof = qualify(data, cache)
    else: frame = encode_frame(data)
    return [(frame, dict(name='geometry-hydrogen-slots-paq-v215-8',size=len(frame),encode_seconds=time.perf_counter()-t), proof)]


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame = candidate
            selection['selected'] = row['name']
    return frame, selection


def decode(frame): return parent.decode(frame)


if __name__ == '__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
