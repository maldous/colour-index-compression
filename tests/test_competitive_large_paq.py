from pathlib import Path
import pytest
from benchmarks import competitive_large_paq as profile
from benchmarks.competitive_codec import unwrap_paq


def test_real_large_member_qualification_and_pending_rejection(tmp_path):
    data=Path('benchmark-work/silesia/nci')
    if not data.exists(): pytest.skip('local corpus unavailable')
    data=data.read_bytes()
    assert profile.eligible(data)
    with pytest.raises(ValueError,match='one complete'):
        profile.additions(data,tmp_path)
    cache=Path('results/leaderboard/paq-v216-level8')
    if not (cache/'nci/result.json').exists(): pytest.skip('local completed PAQ unavailable')
    [(frame,row,proof)]=profile.additions(data,cache)
    assert unwrap_paq(frame)==('v216',(cache/'nci/stream.paq8px216').read_bytes())
    assert proof['measurement']['round_trip'] and row['size']==len(frame)
    assert not profile.eligible(bytes(profile.MIN_BYTES))
