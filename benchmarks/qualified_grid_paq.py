"""Qualify complete grid/PAQ physical frames against their frozen decode proof."""
import json
from pathlib import Path
import time
import zlib

from benchmarks import grid_backend_probe as framed

paq = framed.paq
SOURCES = [__file__, *framed.SOURCES, paq.paq_binary('v215')]


def validate_frame_header(frame, data, mode):
    if frame[:7] != framed.MAGIC + bytes([mode, 1]):
        raise ValueError('grid frame family/mode/backend mismatch')
    n, pos = framed.multinomial.vdecode(frame, 7)
    if n != len(data) or int.from_bytes(frame[pos:pos+4], 'big') != zlib.crc32(data):
        raise ValueError('grid source length/checksum mismatch')
    version, _ = paq.unwrap_paq(frame[pos+4:])
    if version != 'v215':
        raise ValueError('grid native version mismatch')


def qualify(data, folder, mode):
    folder = Path(folder)
    record = folder/'complete.json'
    row = json.loads(record.read_text())
    digest = paq.sha(data)
    if (not row.get('round_trip') or not row.get('complete_silesia_member')
            or row['offset'] != 0 or row['original_bytes'] != len(data)
            or row['input_sha256'] != digest or row['restored_sha256'] != digest):
        raise ValueError('grid complete restoration proof mismatch')
    if (row['mode'] != mode or row['backend'] != 1 or row['options'] != '-8'
            or row['numpy_version'] != framed.numpy.__version__
            or row['brotli_version'] != framed.brotli.__version__):
        raise ValueError('grid experiment policy/environment mismatch')
    hashes = {str(Path(p).resolve()): h for p, h in row['source_hashes'].items()}
    required = [*framed.SOURCES, paq.paq_binary('v215')]
    if any(str(Path(p).resolve()) not in hashes for p in required):
        raise ValueError('missing grid dependency evidence')
    if any(paq.sha(Path(p).read_bytes()) != h for p, h in hashes.items()):
        raise ValueError('grid source/backend changed')
    frame = (folder/'stream.cixb').read_bytes()
    if len(frame) != row['physical_bytes'] or paq.sha(frame) != row['frame_sha256']:
        raise ValueError('grid physical stream changed')
    validate_frame_header(frame, data, mode)
    raw, _ = framed.transform(data, mode)
    if paq.sha(raw) != row['transformed_sha256'] or framed.inverse(raw, mode) != data:
        raise ValueError('grid transform reproduction/inversion mismatch')
    return frame, dict(kind='Exact complete independently restored grid/PAQ frame; current input/frame/source/backend identities checked and transform recomputed/inverted',
        measurement=row, measurement_path=str(record.resolve()),
        measurement_sha256=paq.sha(record.read_bytes()), frame_sha256=paq.sha(frame),
        input_sha256=digest, transformed_sha256=paq.sha(raw), fresh_full_decode=False)


def addition(data, cache, mode):
    if not paq.has_fixed_star_records(data):
        return []
    start = time.perf_counter()
    if cache:
        frame, proof = qualify(data, cache, mode)
    else:
        frame, _ = framed.encode(data, mode, 1, '-8')
        proof = None
    row = dict(name=f'grid-mode{mode}-paq-v215-8', size=len(frame),
               encode_seconds=time.perf_counter()-start)
    return [(frame, row, proof)]
