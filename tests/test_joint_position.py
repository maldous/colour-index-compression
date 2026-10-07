import hashlib
import json
import pytest
from benchmarks.joint_position import report


def test_candidate_rank_requires_complete_matching_physical_cohort(tmp_path):
    corpus = tmp_path / 'corpus'
    results = tmp_path / 'results'
    corpus.mkdir()
    results.mkdir()
    specs = []
    for i in range(12):
        name = str(i)
        data = bytes([i])
        (corpus / name).write_bytes(data)
        specs.append(dict(name=name, size=1, md5=hashlib.md5(data).hexdigest()))
        (results / ('silesia-' + name + '.cixt')).write_bytes(data)
        row = dict(identity=dict(input_sha256=hashlib.sha256(data).hexdigest(), policy={'fixed': True}),
                   original=1, size=1, file=name, corpus='silesia', round_trip=True,
                   frame_sha256=hashlib.sha256(data).hexdigest())
        (results / ('silesia-' + name + '.json')).write_text(json.dumps(row))
    published = tmp_path / 'published.json'
    published.write_text(json.dumps(dict(verified_corpus=specs, source_url='example',
        snapshot_sha256='snapshot', entries=[dict(total_bytes=10, compressor='a'),
                                            dict(total_bytes=20, compressor='b')])))
    assert report(published, results, corpus)['position']['equivalent_position'] == 2
    blob = results / 'silesia-0.cixt'
    blob.write_bytes(b'x')
    with pytest.raises(ValueError, match='hash mismatch'):
        report(published, results, corpus)
    blob.write_bytes(b'\x00')
    path = results / 'silesia-0.json'
    row = json.loads(path.read_text())
    row['identity']['policy'] = {'different': True}
    path.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='mixed policies'):
        report(published, results, corpus)
    path.unlink()
    with pytest.raises(ValueError, match='incomplete cohort'):
        report(published, results, corpus)
