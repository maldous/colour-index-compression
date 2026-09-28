"""Prospective portfolio 16: extend bounded PAQ to 48 MiB.

The complete score may be refreshed only after every eligible cached reference
has independently restored. Pending archives are rejected, never projected.
"""
import sys
import time
from benchmarks import competitive_symbol_loads as parent
from benchmarks import competitive_small_paq as reference
from benchmarks import competitive_database_portfolio as database
from benchmarks.competitive_codec import encode_paq

NAME = 'CIX competitive 48MiB PAQ/structural portfolio 16'
SOURCES = [__file__]
MIN_BYTES = 2 * reference.MAX_BYTES
MAX_BYTES = 48 << 20


def eligible(data):
    return MIN_BYTES < len(data) <= MAX_BYTES and not database.recognizes(data)


def additions(data, cache=None):
    if not eligible(data):
        return []
    started = time.perf_counter(); proof = None
    if cache:
        frame, proof = reference.qualify(data, cache)
    else:
        frame = encode_paq(data, 'v216', '-8')
    return [(frame, dict(name='paq-v216-8-24-to-48MiB-nondatabase', size=len(frame),
                         encode_seconds=time.perf_counter()-started), proof)]


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame = candidate; selection['selected'] = row['name']
    return frame, selection


def decode(frame):
    return parent.decode(frame)


if __name__ == '__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
