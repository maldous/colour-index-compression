from pathlib import Path
import hashlib
import pytest
from benchmarks import domain_molecular as molecular


ASSET=Path('docs/research/2026-09-30-domain-transfer/assets/pubchem-cid-2519-caffeine-3d.sdf')
BATCH=Path('docs/research/2026-09-30-domain-transfer/assets/pubchem-3d-batch/pubchem-3d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf')
BATCH_2D=Path('docs/research/2026-09-30-domain-transfer/assets/pubchem-2d-batch/pubchem-2d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf')

def test_pubchem_caffeine_adapter_round_trip_and_accounting():
    data=ASSET.read_bytes();frame=molecular.encode(data,molecular.VARIANT)
    assert molecular.decode(frame)==data
    stats=molecular.inspect(data)
    assert stats['parsed_records']==1 and stats['records']==2
    assert stats['accounting']['physical_bytes']==len(frame)==stats['accounting']['component_sum_bytes']
    assert stats['accounting']['literal_records']==1
    assert hashlib.sha256(data).hexdigest()=='ce51a07a9d3197bb7e1a82b38a5ff4b598eb2b6f21bcbfc3a0e89d17f932dc92'

def test_unknown_variant_and_bad_frame_rejected():
    with pytest.raises(ValueError):molecular.encode(b'x','other')
    with pytest.raises(ValueError):molecular.decode(b'not a molecular frame')

def test_predeclared_pubchem_batch_has_no_omitted_response_and_round_trips():
    data=BATCH.read_bytes();frame=molecular.encode(data);stats=molecular.inspect(data)
    assert molecular.decode(frame)==data
    assert hashlib.sha256(data).hexdigest()=='3573383c76595b726b49f3e8fec1a87ba8f248f606c3ac1240af37c22ebc3ce3'
    assert stats['parsed_records']==8 and stats['candidate_order_choices']==3

def test_predeclared_2d_batch_is_separate_and_round_trips_without_generated_atoms():
    data=BATCH_2D.read_bytes();frame=molecular.encode(data);stats=molecular.inspect(data)
    assert molecular.decode(frame)==data
    assert hashlib.sha256(data).hexdigest()=='a337dc43a915618cb2e57ef7e419eb9466ed292deccb3ec875e9049f07c50d1e'
    assert stats['parsed_records']==8 and stats['candidate_order_choices']==27
