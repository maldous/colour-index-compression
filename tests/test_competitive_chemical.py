import json
from pathlib import Path
import pytest
from benchmarks import competitive_chemical as codec


def test_uncached_stream_matches_completed_trial_and_decodes():
    root=Path('results/leaderboard/sdf-geometry-paq64k/2-2')
    if not root.exists():pytest.skip('local qualified probe unavailable')
    data=Path('benchmark-work/silesia/nci').read_bytes()[:65536]
    assert codec.recognizes(data)
    assert not codec.recognizes(b'ordinary input')
    frame=codec.encode_frame(data,'-4')
    assert frame==(root/'stream.cixg').read_bytes()
    assert codec.decode(frame)==data
    reused,proof=codec.qualify(data,root,'-4',require_complete=False)
    assert reused==frame and proof['structural_stage_recomputed_and_inverted']
    with pytest.raises(ValueError):codec.qualify(data,root,'-4')


def test_reject_changed_or_unverified_cache(tmp_path):
    root=Path('results/leaderboard/sdf-geometry-paq64k/2-2')
    if not root.exists():pytest.skip('local qualified probe unavailable')
    row=json.loads((root/'complete.json').read_text());row['round_trip']=False
    (tmp_path/'complete.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):codec.qualify(b'wrong',tmp_path)
    row['round_trip']=True;row['complete_silesia_member']=True
    (tmp_path/'complete.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):codec.qualify(b'wrong',tmp_path,'-4')
