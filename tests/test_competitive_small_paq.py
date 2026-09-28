import json
from pathlib import Path
import pytest
from benchmarks import competitive_small_paq as codec
from benchmarks.competitive_codec import unwrap_paq


def test_complete_paq_archive_is_exactly_preserved():
    root=Path('results/leaderboard/paq-v216-level8')
    if not (root/'xml/result.json').exists():pytest.skip('completed local PAQ reference unavailable')
    data=Path('benchmark-work/silesia/xml').read_bytes();frame,proof=codec.qualify(data,root)
    assert codec.eligible(data)
    assert unwrap_paq(frame)==('v216',(root/'xml/stream.paq8px216').read_bytes())
    assert proof['measurement']['round_trip']
    assert proof['archive_payload_unchanged']
    assert not codec.eligible(bytes(codec.MAX_BYTES+1))


def test_unfinished_or_wrong_input_cache_is_rejected(tmp_path):
    with pytest.raises(ValueError):codec.qualify(b'anything',tmp_path)
    root=Path('results/leaderboard/paq-v216-level8/xml/result.json')
    if not root.exists():pytest.skip('completed local PAQ reference unavailable')
    row=json.loads(root.read_text());row['round_trip']=False
    sub=tmp_path/'xml';sub.mkdir();(sub/'result.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):codec.qualify(Path('benchmark-work/silesia/xml').read_bytes(),tmp_path)
