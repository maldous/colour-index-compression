import json
from pathlib import Path
import pytest
from benchmarks import competitive_constraint_refresh as codec


@pytest.mark.parametrize('kind,member,folder', [
    ('geometry', 'nci', 'sdf-geometry-paq64k/2-1'),
    ('database', 'osdb', 'mysql-record-paq-prefix64k/0-3-1'),
])
def test_uncached_encoder_matches_qualified_physical_trial(kind, member, folder):
    root = Path('results/leaderboard')/folder
    if not root.exists(): pytest.skip('local probe unavailable')
    data = Path('benchmark-work/silesia', member).read_bytes()[:65536]
    frame = codec.encode_geometry(data, '-4') if kind == 'geometry' else codec.records.encode(data, 3, 1, '-4')[0]
    assert codec.decode(frame) == data
    cached, proof = codec.qualify(data, root, kind, '-4', require_complete=False)
    assert cached == frame and proof['structural_stage_recomputed_and_inverted']
    with pytest.raises(ValueError): codec.qualify(data, root, kind, '-4')


def test_missing_restoration_evidence_is_rejected(tmp_path):
    (tmp_path/'complete.json').write_text(json.dumps({'round_trip': False}))
    with pytest.raises(ValueError): codec.qualify(b'source', tmp_path, 'database')
