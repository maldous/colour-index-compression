"""Prospective field-prediction extension preserving the qualified portfolio20."""
import sys
from benchmarks import competitive_large_paq as parent
from benchmarks import qualified_structural_paq as native
from benchmarks import competitive_successor as successor

NAME = 'CIX competitive complete-size PAQ and field-prediction portfolio 21'
SOURCES = [__file__, successor.__file__, *native.SOURCES]


def additions(data, cache=None):
    return native.addition(data, cache, 'fields', 1)


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame, selection['selected'] = candidate, row['name']
    return frame, selection


def decode(frame):
    if frame[:5] == native.fields.MAGIC:
        return native.fields.decode(frame)
    return parent.decode(frame)


if __name__ == '__main__':
    successor.main(sys.modules[__name__])
