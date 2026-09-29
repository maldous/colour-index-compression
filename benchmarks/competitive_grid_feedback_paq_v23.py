"""Retain bounded grids and add the smaller complete feedback/PAQ alternative."""
import sys
from benchmarks import competitive_grid_paq_v22 as parent
from benchmarks import qualified_grid_paq as native
from benchmarks import competitive_successor as successor

NAME = 'CIX competitive complete-size PAQ and grid-feedback portfolio 23'
SOURCES = [__file__, successor.__file__, *native.SOURCES]


def additions(data, cache=None):
    return native.addition(data, cache, 1)


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
    successor.main(sys.modules[__name__])
