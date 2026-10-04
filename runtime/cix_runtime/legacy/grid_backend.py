"""Matched physical grid/feedback/rank/arithmetic controls with PAQ or Brotli.

This separate frame leaves qualified and running codecs frozen. Modes two,
three and four receive identical bounded coordinate information; only their
integer representation differs. Full dictionary/framing/checksum costs count.
"""
import hashlib
import zlib

import brotli
from . import multinomial
from .. import backends as paq
from . import grid_interval as bounded
from . import grid_feedback as feedback
from . import record_float_grid as grid

MAGIC = b'CIXB\x1e'
def _brotli_decode(payload, cap):
    """Incremental decode with a paid intermediate cap.

    The binding has no max-output argument.  Chunking limits retained Python
    output and rejects as soon as its declared allocation cap is exceeded;
    callers still apply RLIMIT_AS/cgroup for native decoder workspace.
    """
    if cap <= 0 or len(payload) > cap: raise ValueError('invalid Brotli intermediate bound')
    dec=brotli.Decompressor(); chunks=[]; total=0
    for at in range(0,len(payload),4096):
        part=dec.process(payload[at:at+4096]); total+=len(part)
        if total>cap:raise ValueError('Brotli intermediate exceeds limit')
        chunks.append(part)
    if not dec.is_finished():raise ValueError('truncated Brotli payload')
    return b''.join(chunks)


def transform(data, mode):
    if mode == 0:
        return data, {'control': 'untransformed source'}
    if mode == 1:
        return feedback.transform(data, 1, 1)
    if mode in (2, 3, 4):
        return bounded.transform(data, {2: 2, 3: 3, 4: 1}[mode], 4096)
    raise ValueError('invalid grid mode')


def inverse(raw, mode):
    if mode == 0:
        return raw
    if mode == 1:
        return feedback.inverse(raw)
    if mode in (2, 3, 4):
        return bounded.inverse(raw)
    raise ValueError('invalid grid mode')


def encode(data, mode, backend, options='-4'):
    raw, stats = transform(data, mode)
    if inverse(raw, mode) != data:
        raise ValueError('transform inversion failed')
    if backend == 0:
        payload = brotli.compress(raw, quality=11)
    elif backend == 1:
        payload = paq.encode_paq(raw, 'v215', options)
    else:
        raise ValueError('invalid backend')
    frame = (MAGIC + bytes([mode, backend]) + multinomial.vencode(len(data))
             + zlib.crc32(data).to_bytes(4, 'big') + payload)
    return frame, {**stats, 'transformed_bytes': len(raw), 'transformed_sha256': hashlib.sha256(raw).hexdigest()}


def decode(frame, max_output_bytes=None, memory_bytes=None):
    if frame[:5] != MAGIC or len(frame) < 8:
        raise ValueError('invalid grid backend frame')
    mode, backend = frame[5:7]
    n, pos = multinomial.vdecode(frame, 7)
    if max_output_bytes is not None and n > max_output_bytes:
        raise ValueError('grid output exceeds limit')
    cap = memory_bytes if memory_bytes is not None else (4 << 30)
    crc = int.from_bytes(frame[pos:pos+4], 'big')
    payload = frame[pos+4:]
    if backend == 0:
        raw = _brotli_decode(payload, cap)
    elif backend == 1:
        # Grid transforms can expand before inverse(); ``n`` bounds only the
        # restored source, so the intermediate is bounded by caller policy.
        raw = paq.decode_paq(payload, max_output_bytes=cap, memory_bytes=cap)
    else:
        raise ValueError('invalid backend')
    data = inverse(raw, mode)
    if len(data) != n or zlib.crc32(data) != crc:
        raise ValueError('grid backend restoration mismatch')
    return data
