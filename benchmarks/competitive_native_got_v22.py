"""Prospective shared-symbol extension preserving qualified portfolio 21."""
import sys
from benchmarks import competitive_native_fields_v21 as parent
from benchmarks import qualified_structural_paq as native
from benchmarks import competitive_successor as successor

NAME = 'CIX competitive complete-size PAQ and shared-symbol portfolio 22'
SOURCES = [__file__, successor.__file__, *native.SOURCES]


def additions(data, cache=None):
    return native.addition(data, cache, 'got', 3)


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame, selection['selected'] = candidate, row['name']
    return frame, selection


def decode(frame):
    if frame[:5] == native.got.MAGIC:
        return native.got.decode(frame)
    return parent.decode(frame)


if __name__ == '__main__':
    successor.main(sys.modules[__name__])
