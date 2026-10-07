import json

import pytest

from benchmarks import competitive_native_fields_v21 as profile
from benchmarks import competitive_large_paq, competitive_filtered
from benchmarks.competitive_successor import validate_parent


def test_parent_is_the_current_complete_size_encoder():
    assert profile.parent is competitive_large_paq


@pytest.mark.parametrize('complete,members,name', [
    (False, 12, competitive_large_paq.NAME),
    (True, 11, competitive_large_paq.NAME),
    (True, 12, competitive_filtered.NAME),
])
def test_partial_or_previous_policy_is_rejected(tmp_path, complete, members, name):
    (tmp_path / 'complete.json').write_text(json.dumps(
        dict(complete=complete, members=members, policy=dict(name=name))))
    with pytest.raises(ValueError):
        validate_parent(profile, tmp_path)


def test_matching_complete_policy_reaches_physical_qualification(tmp_path):
    expected = dict(complete=True, members=12,
                    policy=dict(name=competitive_large_paq.NAME))
    (tmp_path / 'complete.json').write_text(json.dumps(expected))
    assert validate_parent(profile, tmp_path) == expected


@pytest.mark.parametrize('candidate', [b'x', b'base', b'much larger'])
def test_physical_selection_never_discards_smaller_parent(monkeypatch, candidate):
    parent = b'base'
    monkeypatch.setattr(profile.parent, 'encode', lambda data, **kw:
                        (parent, dict(selected='parent', trials=[])))
    monkeypatch.setattr(profile, 'additions', lambda data:
                        [(candidate, dict(name='fields', size=len(candidate)), None)])
    frame, selection = profile.encode(b'unrelated input')
    assert frame == (candidate if len(candidate) < len(parent) else parent)
    assert selection['selected'] == ('fields' if len(candidate) < len(parent) else 'parent')
