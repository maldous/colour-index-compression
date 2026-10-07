"""Qualify frozen whole-frame grouped-grid, pointer and native LSTM evidence."""
import json
from pathlib import Path
import zlib

from benchmarks import grid_conditional_paq_probe as grouped
from benchmarks import ecoff_pointer_delta_probe as pointer
from benchmarks import competitive_codec as paq
from benchmarks import paq_reference_run as reference
from cix.multinomial import vdecode

POINTER_SOURCES = [pointer.__file__, pointer.codec.__file__, pointer.codec.locator.__file__,
    pointer.codec.parent.__file__, pointer.codec.parent.parent.__file__,
    pointer.codec.parent.parent.base.__file__, paq.__file__, reference.ROOT/'cix/multinomial.py']
SOURCES = [__file__, *grouped.SOURCES, *POINTER_SOURCES, reference.__file__, paq.paq_binary('v215')]


def validate_header(frame, data, family):
    prefix = grouped.MAGIC if family == 'grouped' else pointer.MAGIC + b'\x01'
    if not frame.startswith(prefix):
        raise ValueError('prediction frame family/backend mismatch')
    n, pos = vdecode(frame, len(prefix))
    if n != len(data) or int.from_bytes(frame[pos:pos+4], 'big') != zlib.crc32(data):
        raise ValueError('prediction length/checksum mismatch')
    if paq.unwrap_paq(frame[pos+4:])[0] != 'v215':
        raise ValueError('prediction native version mismatch')


def qualify(data, folder, family):
    if family not in ('grouped', 'pointer'):
        raise ValueError('unsupported prediction family')
    folder = Path(folder); record = folder/'complete.json'
    row = json.loads(record.read_text()); digest = paq.sha(data)
    if (not row.get('round_trip') or not row.get('complete_silesia_member')
        or row['original_bytes'] != len(data) or row['input_sha256'] != digest
        or row['restored_sha256'] != digest or row['options'] != '-8'):
        raise ValueError('complete prediction restoration/policy mismatch')
    if family == 'grouped':
        if (row['context'], row['coding'], row['offset']) != (3, 0, 0):
            raise ValueError('grouped representation mismatch')
        required = grouped.SOURCES
    else:
        if (row['mode'], row['backend']) != (5, 'paq'):
            raise ValueError('pointer representation mismatch')
        required = POINTER_SOURCES
    hashes = {str(Path(p).resolve()): h for p,h in row['source_hashes'].items()}
    if any(str(Path(p).resolve()) not in hashes for p in [*required, paq.paq_binary('v215')]):
        raise ValueError('missing prediction dependency proof')
    if any(paq.sha(Path(p).read_bytes()) != h for p,h in hashes.items()):
        raise ValueError('prediction source/backend changed')
    frame = (folder/'stream.cixb').read_bytes()
    if len(frame) != row['physical_bytes'] or paq.sha(frame) != row['frame_sha256']:
        raise ValueError('prediction physical frame changed')
    validate_header(frame, data, family)
    module = grouped if family == 'grouped' else pointer
    raw, _ = module.codec.transform(data, 3, 0) if family == 'grouped' else module.codec.transform(data, 5)
    if paq.sha(raw) != row['transformed_sha256'] or module.codec.inverse(raw) != data:
        raise ValueError('prediction transform reproduction/inversion failed')
    return frame, dict(kind='Frozen complete independent extraction retained; all input/frame/source/backend identities checked and structural transform recomputed and inverted',
        measurement=row, measurement_path=str(record.resolve()), measurement_sha256=paq.sha(record.read_bytes()),
        input_sha256=digest, frame_sha256=paq.sha(frame), transformed_sha256=paq.sha(raw), fresh_full_decode=False)


def qualify_lstm(data, folder):
    folder = Path(folder); record = folder/'result.json'; row = json.loads(record.read_text())
    digest = paq.sha(data); policy = row['identity']['policy']
    if (policy['version'], policy['options'], policy['simd']) != ('v215', '-9L', 'AVX2'):
        raise ValueError('LSTM native policy mismatch')
    if (not row['round_trip'] or row['restored_sha256'] != digest
        or row['identity']['input_sha256'] != digest or row['original'] != len(data)
        or row['identity']['original'] != len(data)):
        raise ValueError('LSTM complete extraction mismatch')
    if (paq.sha(Path(paq.paq_binary('v215')).read_bytes()) != policy['binary_sha256']
        or paq.sha(Path(reference.__file__).read_bytes()) != policy['runner_sha256']):
        raise ValueError('LSTM backend/verifier changed')
    archive = (folder/'stream.paq8px215').read_bytes()
    if len(archive) != row['size'] or paq.sha(archive) != row['archive_sha256']:
        raise ValueError('LSTM archive changed')
    frame = paq.wrap_paq(archive, 'v215')
    if paq.unwrap_paq(frame) != ('v215', archive) or len(frame) != len(archive):
        raise ValueError('LSTM header substitution mismatch')
    return frame, dict(kind='Complete native extraction retained with exactly invertible equal-size six-byte wrapper',
        measurement=dict(row, decode_seconds=row['decode']['wall_seconds'], encode_seconds=row['encode']['wall_seconds']),
        measurement_path=str(record.resolve()), measurement_sha256=paq.sha(record.read_bytes()),
        input_sha256=digest, frame_sha256=paq.sha(frame), archive_payload_unchanged=True, fresh_full_decode=False)
