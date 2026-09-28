"""Add exact ECOFF constraints and shared-symbol alphabets with Brotli 11."""
import json
from pathlib import Path
import sys
import time
import brotli
import _brotli
from benchmarks import competitive_medium_paq as parent
from benchmarks import ecoff_got_probe as framed, ecoff_got as got
from benchmarks.competitive_codec import sha

NAME = 'CIX competitive executable-constraint portfolio 11'
MODES = (-2, -1, 0, 1, 2, 3, 4)
SOURCES = [__file__, framed.__file__, got.__file__, got.parent.__file__, got.parent.base.__file__]


def eligible(data):
    return bool(got.parent.base.objects(data))


def qualify(data, folder, require_complete=True):
    folder = Path(folder); record = folder / 'complete.json'; row = json.loads(record.read_text())
    digest = sha(data)
    if (not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member'))
            or row['input_sha256'] != digest or row['restored_sha256'] != digest or row['original_bytes'] != len(data)):
        raise ValueError('ECOFF input/restoration evidence mismatch')
    if row['backend'] != 'brotli' or row['brotli_version'] != brotli.__version__ or row['mode'] not in MODES:
        raise ValueError('ECOFF cache policy mismatch')
    for path, value in row['source_hashes'].items():
        if sha(Path(path).read_bytes()) != value:
            raise ValueError('ECOFF source changed')
    frame = (folder / 'stream.cixb').read_bytes()
    if len(frame) != row['physical_bytes'] or sha(frame) != row['frame_sha256']:
        raise ValueError('ECOFF artifact mismatch')
    if frame[:5] != framed.MAGIC or frame[5:7] != bytes([row['mode'] + 2, 0]):
        raise ValueError('ECOFF frame policy mismatch')
    if row['mode'] == -2:
        raw, _ = got.parent.transform(data, 1)
    elif row['mode'] == -1:
        raw = data
    else:
        raw, _ = got.transform(data, min(row['mode'], 3), row['mode'] != 4)
    if sha(raw) != row['transformed_sha256']:
        raise ValueError('ECOFF transform reproduction mismatch')
    # The original probe records Brotli's version. This additional fresh decode
    # qualifies the current native backend directly and records its binary hash.
    binary = Path(_brotli.__file__); binary_hash = sha(binary.read_bytes())
    start = time.perf_counter(); restored = framed.decode(frame); elapsed = time.perf_counter() - start
    if restored != data or sha(binary.read_bytes()) != binary_hash:
        raise ValueError('fresh ECOFF restoration/backend mismatch')
    measurement = dict(row, original_decode_seconds=row['decode_seconds'], decode_seconds=elapsed)
    proof = dict(kind='source-qualified artifact; transform recomputed and full standalone decode repeated',
                 measurement=measurement, measurement_path=str(record.resolve()), measurement_sha256=sha(record.read_bytes()),
                 frame_sha256=sha(frame), input_sha256=digest, transformed_sha256=sha(raw),
                 current_brotli_binary_sha256=binary_hash, current_brotli_version=brotli.__version__,
                 fresh_full_decode=True)
    return frame, proof


def additions(data, cache=None):
    if not eligible(data):
        return []
    found = {}
    if cache:
        for record in Path(cache).glob('*/complete.json'):
            row = json.loads(record.read_text())
            if row.get('input_sha256') == sha(data) and row.get('mode') in MODES:
                if row['mode'] in found:
                    raise ValueError('duplicate ECOFF cache candidate')
                found[row['mode']] = record.parent
        if set(found) != set(MODES):
            raise ValueError('all seven complete ECOFF candidates required')
    out = []
    for mode in MODES:
        start = time.perf_counter(); proof = None
        if cache:
            frame, proof = qualify(data, found[mode])
        else:
            frame, _ = framed.encode(data, mode, 'brotli', '-4')
        out.append((frame, dict(name=f'ecoff-constraints-brotli11-mode{mode}', size=len(frame),
                                encode_seconds=time.perf_counter() - start), proof))
    return out


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame = candidate; selection['selected'] = row['name']
    return frame, selection


def decode(frame):
    return framed.decode(frame) if frame[:5] == framed.MAGIC else parent.decode(frame)


if __name__ == '__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
