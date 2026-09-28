import pytest
from benchmarks import paq_joint_log_probe as codec, paq_memory_feedback_probe as memory, paq_register_log_probe as register
from tests.test_paq_memory_feedback import memory_fixture


@pytest.fixture(scope='module')
def streams():
    if not codec.FORK.exists():pytest.skip('isolated joint feedback build required')
    data=memory_fixture()
    return data,{m:codec.encode(data,m,'-4') for m in (4,0,1,2,3)}


@pytest.mark.parametrize('mode',(4,0,1,2,3))
def test_every_joint_ablation_restores_original(streams,mode):
    data,frames=streams
    assert codec.decode(frames[mode][0])==data


def test_joint_controls_match_individual_forks_exactly(streams):
    data,frames=streams
    assert frames[4][1]['paq_sha256']==frames[0][1]['paq_sha256']
    _,mem=memory.encode(data,2,'-4')
    raw,_=codec.transform.transform(data,4)
    _,reg=register.encode(raw,1,'-4')
    assert frames[1][1]['paq_sha256']==mem['paq_sha256']
    assert frames[2][1]['paq_sha256']==reg['paq_sha256']
    assert frames[3][1]['paq_sha256'] not in (mem['paq_sha256'],reg['paq_sha256'])
