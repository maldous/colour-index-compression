import os, random
import pytest
from benchmarks.hutter_wikipedia_projections import DEPENDENCIES, MAGIC, project, restore


@pytest.mark.parametrize('recipe',['p1','p2','p3'])
@pytest.mark.parametrize('data',[b'',b'a',b'abcde',bytes(range(256)),b'\x00'*31+b'xyz'*19,bytes(range(255,-1,-1))])
def test_fixed_projection_round_trip(recipe,data):
    frame=project(data,recipe)
    assert restore(frame)==data
    assert frame.startswith(MAGIC)


@pytest.mark.parametrize('recipe',['p1','p2','p3'])
def test_random_repetition_and_non_byte_aligned_lengths(recipe):
    rng=random.Random(77)
    for length in (1,7,9,15,17,63,65,257):
        data=bytes(rng.randrange(256) if index%5 else 12 for index in range(length))
        assert restore(project(data,recipe))==data


def test_p2_has_no_encoder_state_and_restarts_every_input():
    data=b'abcabcxyzabc'+bytes(range(32))
    assert project(data,'p2')==project(data,'p2')
    assert restore(project(data,'p2'))==data


@pytest.mark.parametrize('recipe',['p1','p2','p3'])
def test_malformed_frames_rejected(recipe):
    frame=project(b'non-byte-aligned payload 123 [[x]]','p2' if recipe=='p2' else recipe)
    with pytest.raises(ValueError):restore(frame[:-1])
    bad=bytearray(frame);bad[len(MAGIC)]=99
    with pytest.raises(ValueError):restore(bytes(bad))


def test_dependency_spec_records_no_backend_compression():
    assert 'pydivsufsort' in DEPENDENCIES['bwt']
    assert 'packed planes' in DEPENDENCIES['p2']
