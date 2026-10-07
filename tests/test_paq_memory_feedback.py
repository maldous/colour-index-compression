import struct
import pytest
from benchmarks import paq_memory_feedback_probe as codec
from tests.test_paq_gp_feedback import instruction_fixture
from benchmarks import ecoff_constraints as layout


def memory_fixture():
    data=bytearray(instruction_fixture());start,n=layout.sections(data)[b'.text']
    for i in range(n//4):
        op=[0x08,0x29,0x2d][i%3];base=[30,27,29][i%3];reg=i%31
        displacement=(([0,8,16,24][i%4])*8+(i//32)*8)&65535
        struct.pack_into('<I',data,start+4*i,(op<<26)|(reg<<21)|(base<<16)|displacement)
    return bytes(data)


@pytest.mark.skipif(not codec.FORK.exists(),reason='isolated memory-feedback build required')
def test_native_disabled_identity_and_all_causal_modes():
    data=memory_fixture();payloads={}
    for mode in (4,0,1,2,3):
        frame,stats=codec.encode(data,mode,'-4');assert codec.decode(frame)==data
        payloads[mode]=stats['paq_sha256']
    assert payloads[0]==payloads[4]
    assert all(payloads[m]!=payloads[0] for m in (1,2,3))
