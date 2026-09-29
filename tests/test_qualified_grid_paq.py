import zlib
import pytest
from benchmarks import qualified_grid_paq as q
from benchmarks import competitive_grid_paq_v22 as profile
from benchmarks import competitive_native_fields_v21


def frame(data, mode=2, backend=1, version=215):
    native = q.paq.wrap_paq(b'paq8px' + bytes([1, 2, 3, 4]), f'v{version}')
    return (q.framed.MAGIC + bytes([mode, backend])
            + q.framed.multinomial.vencode(len(data))
            + zlib.crc32(data).to_bytes(4, 'big') + native)


def test_matches_the_scored_parent():
    assert profile.parent is competitive_native_fields_v21


def test_correct_header_accepted():
    q.validate_frame_header(frame(b'abc'), b'abc', 2)


@pytest.mark.parametrize('candidate,data', [
    (frame(b'abc', mode=1), b'abc'),
    (frame(b'abc', backend=0), b'abc'),
    (frame(b'abc', version=216), b'abc'),
    (frame(b'abc'), b'ab'),
    (frame(b'abc'), b'abd'),
])
def test_incompatible_header_rejected(candidate, data):
    with pytest.raises(ValueError):
        q.validate_frame_header(candidate, data, 2)


@pytest.mark.parametrize('candidate', [b'a', b'base', b'longer'])
def test_complete_size_selection_retains_incumbent(monkeypatch, candidate):
    monkeypatch.setattr(profile.parent, 'encode', lambda data, **kw:
                        (b'base', dict(selected='parent', trials=[])))
    monkeypatch.setattr(profile, 'additions', lambda data:
                        [(candidate, dict(name='grid', size=len(candidate)), None)])
    result, _ = profile.encode(b'input')
    assert result == (candidate if len(candidate) < 4 else b'base')
