from benchmarks import competitive_large_paq as profile
from benchmarks import competitive_intermediate_paq as parent
from pathlib import Path
import pytest


def test_next_extension_begins_after_intermediate_ceiling():
    assert profile.MIN_BYTES == parent.MAX_BYTES == 48 << 20
    assert not profile.eligible(bytes(1024))


def test_unfinished_large_artifact_is_rejected(tmp_path):
    source=Path('benchmark-work/silesia/mozilla')
    if not source.exists():pytest.skip('local corpus unavailable')
    data=source.read_bytes();assert profile.eligible(data)
    with pytest.raises(ValueError,match='one complete'):profile.additions(data,tmp_path)
