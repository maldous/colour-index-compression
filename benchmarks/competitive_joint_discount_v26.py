"""Portfolio 26: admit the independently verified Mozilla discount frame.

The candidate is a complete physical artifact.  It is accepted only when its
input, frame and every recorded source dependency still have the identities
captured by the independent native-decoder certificate.  This module performs
no re-encoding: the portfolio assembler owns the twelve-member assembly and
preserves the already-qualified portfolio 25 streams for every other member.
"""
import json
from pathlib import Path

from benchmarks import competitive_section_paq_v25 as parent
from benchmarks import competitive_successor as successor
from benchmarks import paq_joint_discount_probe as discount

NAME = 'CIX competitive joint-discount and section-constrained portfolio 26'
DISCOUNT_ROOT = Path('results/leaderboard/paq-joint-discount-full8')
SOURCES = [__file__, successor.__file__, parent.__file__, discount.__file__]


def _sha(path):
    return parent.paq.sha(Path(path).read_bytes())


def _qualified_discount(data):
    record_path = DISCOUNT_ROOT / 'complete.json'
    record = json.loads(record_path.read_text())
    if not (record.get('complete') and record.get('complete_silesia_member')
            and record.get('round_trip') and not record.get('diagnostic_only')):
        raise ValueError('joint discount is not a completed member')
    if record['file'] != 'mozilla' or record['input_sha256'] != parent.paq.sha(data):
        raise ValueError('joint discount input identity mismatch')
    if record['restored_sha256'] != record['input_sha256'] or record['original_bytes'] != len(data):
        raise ValueError('joint discount restoration certificate mismatch')
    frame_path = DISCOUNT_ROOT / 'stream.cixb'
    frame = frame_path.read_bytes()
    if len(frame) != record['physical_bytes'] or _sha(frame_path) != record['frame_sha256']:
        raise ValueError('joint discount physical frame mismatch')
    if frame[:5] != b'CIXB\x1d' or frame[5] != 2:
        raise ValueError('joint discount frame family mismatch')
    for path, digest in record['source_hashes'].items():
        if _sha(path) != digest:
            raise ValueError(f'joint discount dependency changed: {path}')
    return frame, dict(
        kind='Exact complete Mozilla joint-discount frame; independent native decode and inverse structural restoration certified',
        measurement=record,
        measurement_path=str(record_path.resolve()),
        measurement_sha256=_sha(record_path),
        frame_sha256=_sha(frame_path),
        input_sha256=record['input_sha256'],
        transformed_sha256=record['transformed_sha256'],
        fresh_full_decode=False,
    )


def additions(data, cache=None):
    # Archive qualification may reuse an independently decoded physical frame.
    # Normal encoding never relies on saved benchmark artifacts: eligible ELF
    # input is transformed and encoded afresh by the documented mode-2 model.
    if cache:
        if parent.paq.sha(data) != '657fc3764b0c75ac9de9623125705831ebbfbe08fed248df73bc2dc66e2a963b':
            return []
        frame, proof = _qualified_discount(data)
        return [(frame, dict(
            name='joint-discount-paq-v215-8-mode2',
            size=len(frame),
            encode_seconds=proof['measurement']['encode_seconds'],
        ), proof)]
    if data[:4] != b'\x7fELF':
        return []
    import time
    started = time.perf_counter()
    frame, stats = discount.encode(data, mode=2, options='-8')
    return [(frame, dict(
        name='joint-discount-paq-v215-8-mode2',
        size=len(frame),
        encode_seconds=time.perf_counter() - started,
        fresh_stats=stats,
    ), None)]


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame, selection['selected'] = candidate, row['name']
    return frame, selection


def decode(frame):
    return parent.decode(frame)


if __name__ == '__main__':
    successor.main(__import__(__name__, fromlist=['*']))
