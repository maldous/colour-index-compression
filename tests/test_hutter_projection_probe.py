import hashlib
import json
from pathlib import Path
import random

import numpy as np
import pytest

from benchmarks import hutter_projection_probe as probe
from benchmarks import volume_image_codec as volume


@pytest.mark.parametrize('recipe', ['p1', 'p2', 'p3'])
@pytest.mark.parametrize('raw', [b'', b'\x00', bytes(range(256)) + b'x'])
def test_full_adapter_restores_boundary_bytes(tmp_path, recipe, raw):
    runtime = tmp_path / 'runtime.json'
    runtime.write_text(json.dumps({'packages': {}, 'files': []}))
    source, archive, restored = (tmp_path / x for x in ('input', 'archive', 'restored'))
    source.write_bytes(raw)
    record = probe.encode(source, archive, recipe, runtime)
    source.unlink()
    probe.decode(archive, restored, runtime)
    assert restored.read_bytes() == raw
    assert record['total_bytes'] == sum(record[k] for k in ('outer_framing_bytes', 'outer_metadata_bytes', 'inner_framing_bytes', 'inner_metadata_bytes', 'jxl_payload_bytes'))
    assert not record['paq_fallback']


def test_runtime_hash_mismatch_fails(tmp_path):
    runtime = tmp_path / 'runtime.json'
    dependency = tmp_path / 'dependency'; dependency.write_bytes(b'changed')
    runtime.write_text(json.dumps({'packages': {}, 'files': [{'path': str(dependency), 'sha256': hashlib.sha256(b'original').hexdigest()}]}))
    with pytest.raises(ValueError, match='runtime file mismatch'):
        probe.check_runtime(runtime)


def test_one_locality_confirmation(tmp_path):
    # Fixed equal-count permutation; no tuning and no PAQ superiority claim.
    grid = ((np.arange(64)[:, None] + np.arange(256)[None, :]) % 256).astype('<u2')
    values = grid.reshape(-1).tolist()
    random.Random(665577).shuffle(values)
    shuffled = np.array(values, dtype='<u2')
    assert sorted(grid.reshape(-1).tolist()) == sorted(values)
    region = {'offset': 0, 'length': grid.nbytes, 'slice_height': 64, 'width': 256}
    archives = [volume.encode(a.tobytes(), region, mode=5, effort=9) for a in (grid, shuffled)]
    assert volume.decode(archives[0]) == grid.tobytes()
    assert volume.decode(archives[1]) == shuffled.tobytes()
    assert len(archives[0]) < len(archives[1])
    print(json.dumps({'locality_gradient_bytes': len(archives[0]), 'equal_counts_permutation_bytes': len(archives[1]), 'seed': 665577}))
