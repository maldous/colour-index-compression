import json
from pathlib import Path
import pytest
from benchmarks import competitive_ecoff as profile
from tests.test_ecoff_got import archive


def test_uncached_choices_and_fresh_cache_qualification(tmp_path):
    data = archive(); candidates = profile.additions(data)
    assert len(candidates) == 7
    assert profile.additions(b'plain bytes') == []
    for frame, _, _ in candidates:
        assert profile.decode(frame) == data
    mode = 3; frame, stats = profile.framed.encode(data, mode, 'brotli', '-4')
    sha = profile.sha; row = dict(stats, round_trip=True, complete_silesia_member=False,
        input_sha256=sha(data), restored_sha256=sha(data), physical_bytes=len(frame), frame_sha256=sha(frame),
        source_hashes={str(Path(profile.got.__file__)): sha(Path(profile.got.__file__).read_bytes())},
        backend='brotli', brotli_version=profile.brotli.__version__, decode_seconds=0.01)
    (tmp_path/'complete.json').write_text(json.dumps(row)); (tmp_path/'stream.cixb').write_bytes(frame)
    with pytest.raises(ValueError, match='evidence mismatch'):
        profile.qualify(data, tmp_path)
    qualified, proof = profile.qualify(data, tmp_path, require_complete=False)
    assert qualified == frame and proof['fresh_full_decode']
    with pytest.raises(ValueError, match='evidence mismatch'):
        profile.qualify(data + b'wrong input', tmp_path, require_complete=False)
    (tmp_path/'stream.cixb').write_bytes(frame[:-1] + bytes([frame[-1] ^ 1]))
    with pytest.raises(ValueError, match='artifact mismatch'):
        profile.qualify(data, tmp_path, require_complete=False)
