"""Prospective portfolio 12: remove the remaining PAQ size ceiling.

The complete score may be refreshed only after every eligible cached reference
has independently restored. Pending archives are rejected, never projected.
"""
import sys
import time
from benchmarks import competitive_ecoff as parent
from benchmarks import competitive_small_paq as reference
from benchmarks import competitive_database_portfolio as database
from benchmarks.competitive_codec import encode_paq

NAME = 'CIX competitive complete-size PAQ/structural portfolio 12'
SOURCES = [__file__]
MIN_BYTES = 2 * reference.MAX_BYTES


def eligible(data):
    return len(data) > MIN_BYTES and not database.recognizes(data)


def additions(data, cache=None):
    if not eligible(data):
        return []
    started = time.perf_counter(); proof = None
    if cache:
        frame, proof = reference.qualify(data, cache)
    else:
        frame = encode_paq(data, 'v216', '-8')
    return [(frame, dict(name='paq-v216-8-above-24MiB-nondatabase', size=len(frame),
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
