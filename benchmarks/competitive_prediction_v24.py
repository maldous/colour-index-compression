"""Add verified structural residuals and a native LSTM tier to portfolio 23.

The ordinary encoder computes every eligible candidate, without benchmark paths,
filenames or hashes. A separate cache map accelerates qualification only.
"""
import json
from pathlib import Path
import sys
import time
from benchmarks import competitive_grid_feedback_paq_v23 as parent
from benchmarks import competitive_successor as successor
from benchmarks import qualified_prediction_paq as native
from benchmarks import qualified_structural_paq as structural
from benchmarks import competitive_database_portfolio as database
from benchmarks import competitive_chemical as chemical

NAME = 'CIX competitive prediction and online-LSTM portfolio 24'
SOURCES = [__file__, successor.__file__, *native.SOURCES, *structural.SOURCES]


def lstm_eligible(data):
    return 24 << 20 < len(data) <= 48 << 20 and not database.recognizes(data) and not chemical.recognizes(data)


def additions(data, cache=None):
    locations = json.loads(Path(cache).read_text()) if cache else {}
    out = []
    if structural.eligible(data):
        out.extend(structural.addition(data, locations.get('got') if cache else None, 'got', 3))
    specs = []
    if native.paq.has_fixed_star_records(data): specs.append('grouped')
    if native.pointer.codec.locator.candidates(data): specs.append('pointer')
    if lstm_eligible(data): specs.append('lstm')
    for kind in specs:
        started = time.perf_counter(); proof = None
        if cache:
            frame, proof = native.qualify_lstm(data, locations[kind]) if kind == 'lstm' else native.qualify(data, locations[kind], kind)
        elif kind == 'grouped': frame, _ = native.grouped.encode(data, 3, '-8')
        elif kind == 'pointer': frame, _ = native.pointer.encode(data, 5, 'paq', '-8')
        else: frame = native.paq.encode_paq(data, 'v215', '-9L')
        out.append((frame, dict(name=f'{kind}-prediction-paq-v215-'+('9L' if kind == 'lstm' else '8'),
            size=len(frame), encode_seconds=time.perf_counter()-started), proof))
    return out


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame, selection['selected'] = candidate, row['name']
    return frame, selection


def decode(frame):
    if frame[:5] == native.grouped.MAGIC: return native.grouped.decode(frame)
    if frame[:5] == structural.got.MAGIC: return structural.got.decode(frame)
    return parent.decode(frame)


if __name__ == '__main__': successor.main(sys.modules[__name__])
