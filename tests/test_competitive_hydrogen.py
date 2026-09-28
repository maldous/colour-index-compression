from pathlib import Path
import pytest
from benchmarks import competitive_hydrogen as codec


def test_uncached_hydrogen_stream_matches_previous_independent_trial():
    folder = Path('results/leaderboard/sdf-hydrogen64k/0-2-0')
    if not folder.exists(): pytest.skip('local hydrogen probe unavailable')
    data = Path('benchmark-work/silesia/nci').read_bytes()[:65536]
    frame = codec.encode_frame(data, '-4')
    assert codec.decode(frame) == data
    assert frame == (folder/'stream.cixq').read_bytes()
    # This earlier probe predates the additional arithmetic controls. Even when
    # its bytes reproduce, its stale source certificate must not be accepted.
    with pytest.raises(ValueError, match='implementation changed'):
        codec.qualify(data, folder, '-4', require_complete=False)
    with pytest.raises(ValueError): codec.qualify(data, folder, '-4')


def test_completed_current_full_trial_qualifies():
    folder = Path('results/leaderboard/sdf-hydrogen-full8/0-2-0')
    if not (folder/'complete.json').exists(): pytest.skip('full local trial unavailable')
    data = Path('benchmark-work/silesia/nci').read_bytes()
    frame, proof = codec.qualify(data, folder)
    assert frame == (folder/'stream.cixq').read_bytes()
    assert proof['structural_stage_recomputed_and_inverted']
