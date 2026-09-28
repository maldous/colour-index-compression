import random
import pytest
from benchmarks import ecoff_filtered_columns as codec
from benchmarks.ecoff_call_trace_analysis import shuffled_code
from tests.test_paq_gp_feedback import instruction_fixture


def test_vectorized_shuffle_matches_paq_trace_mapping():
    data=random.Random(527).randbytes(40000)
    assert codec.shuffled(data)==shuffled_code(data)


@pytest.mark.parametrize('mode',[1,2,3])
def test_columns_bijection_and_partial_bitplane_groups(mode):
    for n in [0,1,7,8,9,31,32,257]:
        data=random.Random(n).randbytes(n*4)
        assert codec.columns(codec.columns(data,mode),mode,True)==data
    raw=b'header'+bytes(range(256))*3+b'trailer'
    encoded=codec.transform(raw,[(6,256),(266,256)],mode)
    assert codec.inverse(encoded,mode)==raw
    with pytest.raises(ValueError):codec.transform(raw,[(6,16),(7,16)],mode)
    with pytest.raises(ValueError):codec.inverse(encoded[:-1],mode)


@pytest.mark.parametrize('mode',range(4))
def test_complete_native_filtered_frames_restore(mode):
    source=instruction_fixture();frame,stats=codec.encode(source,mode)
    assert codec.decode(frame)==source
    if mode:assert stats['regions']==1 and stats['region_bytes']>1024
