import json
from pathlib import Path
import shutil

import pytest

from benchmarks import qualified_structural_paq as qualified
from benchmarks import competitive_native_fields, competitive_native_got
from tests.test_paq_memory_feedback import memory_fixture


REGION = Path('results/leaderboard/ecoff-fields-paq-objects/4274176-1')
SOURCE = Path('benchmark-work/silesia/mozilla')


@pytest.fixture
def regional_proof(tmp_path):
    if not (REGION / 'complete.json').exists() or not SOURCE.exists():
        pytest.skip('local verified regional evidence required')
    for name in ('complete.json', 'stream.cixb'):
        shutil.copyfile(REGION / name, tmp_path / name)
    data = SOURCE.read_bytes()[4274176:4274176 + 73728]
    return data, tmp_path


def test_partial_result_cannot_enter_full_score(regional_proof):
    data, folder = regional_proof
    with pytest.raises(ValueError, match='complete restoration'):
        qualified.qualify(data, folder, 'fields', 1, options='-4')
    frame, proof = qualified.qualify(data, folder, 'fields', 1,
                                     require_complete=False, options='-4')
    assert frame == (folder / 'stream.cixb').read_bytes()
    assert proof['fresh_full_decode'] is False
    assert proof['measurement']['complete_silesia_member'] is False


@pytest.mark.parametrize('damage', ['frame', 'source', 'backend', 'mode', 'input'])
def test_qualification_rejects_changed_evidence(regional_proof, damage):
    data, folder = regional_proof
    record = folder / 'complete.json'
    row = json.loads(record.read_text())
    if damage == 'frame':
        frame = bytearray((folder / 'stream.cixb').read_bytes())
        frame[-1] ^= 1
        (folder / 'stream.cixb').write_bytes(frame)
    elif damage == 'source':
        row['source_hashes'].pop(str(qualified.fields.codec.__file__))
    elif damage == 'backend':
        row['backend_sha256'] = '0' * 64
    elif damage == 'mode':
        row['mode'] = 2
    else:
        row['input_sha256'] = '0' * 64
    record.write_text(json.dumps(row))
    with pytest.raises(ValueError):
        qualified.qualify(data, folder, 'fields', 1,
                          require_complete=False, options='-4')


def test_regional_field_stream_independently_restores(regional_proof):
    data, folder = regional_proof
    assert competitive_native_fields.decode((folder / 'stream.cixb').read_bytes()) == data


def test_shared_symbol_native_stream_restores():
    data = memory_fixture()
    frame, _ = qualified.got.encode(data, 3, 'paq', '-4')
    assert competitive_native_got.decode(frame) == data
    raw = qualified.raw_transform(data, 'got', 3)
    assert qualified.got.codec.inverse(raw) == data
