import zlib
import pytest
from benchmarks import qualified_prediction_paq as q
from benchmarks import competitive_prediction_v24 as profile
from benchmarks import competitive_grid_feedback_paq_v23
from cix.multinomial import vencode


def frame(data, family='grouped', version='v215'):
    prefix = q.grouped.MAGIC if family == 'grouped' else q.pointer.MAGIC + b'\x01'
    return prefix + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + q.paq.wrap_paq(b'paq8px1234', version)


def test_parent_alignment():
    assert profile.parent is competitive_grid_feedback_paq_v23


@pytest.mark.parametrize('family', ['grouped', 'pointer'])
def test_frame_header(family):
    q.validate_header(frame(b'abc', family), b'abc', family)
    for altered, data in [(frame(b'abc', family, 'v216'), b'abc'),
                          (frame(b'abc', family), b'abd'),
                          (frame(b'abc', family), b'ab'),
                          (b'wrong' + frame(b'abc', family)[5:], b'abc')]:
        with pytest.raises(ValueError): q.validate_header(altered, data, family)


@pytest.mark.parametrize('candidate', [b'a', b'base', b'longer'])
def test_exact_size_selection(monkeypatch, candidate):
    monkeypatch.setattr(profile.parent, 'encode', lambda data, **kw: (b'base', dict(selected='parent', trials=[])))
    monkeypatch.setattr(profile, 'additions', lambda data: [(candidate, dict(name='new', size=len(candidate)), None)])
    result, _ = profile.encode(b'input')
    assert result == (candidate if len(candidate) < 4 else b'base')


def test_decode_routing(monkeypatch):
    monkeypatch.setattr(q.grouped, 'decode', lambda frame: b'grouped')
    monkeypatch.setattr(profile.structural.got, 'decode', lambda frame: b'got')
    monkeypatch.setattr(profile.parent, 'decode', lambda frame: b'parent')
    assert profile.decode(q.grouped.MAGIC) == b'grouped'
    assert profile.decode(profile.structural.got.MAGIC) == b'got'
    assert profile.decode(b'anything') == b'parent'
