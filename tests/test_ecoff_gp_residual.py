import itertools
import random
import struct
import pytest
from benchmarks import ecoff_gp_residual as codec
from tests.test_paq_gp_feedback import instruction_fixture


@pytest.mark.parametrize('method',[0,1])
def test_same_count_information_type_classes_restore(method):
    cases=[b'',bytes(range(256))*2,b'\0'*800,random.Random(42).randbytes(515)]
    cases.extend(bytes(p) for p in itertools.product(range(3),repeat=4))
    for data in cases:
        blob,bits=codec.composition_encode(data,method);restored,pos=codec.composition_decode(blob,0,len(data),method)
        assert restored==data and pos==len(blob) and bits>=0


@pytest.mark.parametrize('mode',range(1,6))
def test_gp_exception_values_wraparound_and_register_contexts(mode):
    words=[(0x29<<26)|((i%32)<<21)|(29<<16)|v for i,v in enumerate([65535,0,1,65534,60000,10]*60)]
    words.insert(5,0x47ff041f);data=b'abc'+struct.pack('>'+'I'*len(words),*words)+b'end'
    raw,stats=codec.transform(data,[(3,len(words)*4)],mode)
    assert codec.inverse(raw,mode)==data and stats['loads']==360


@pytest.mark.parametrize('mode',range(6))
def test_gp_residual_native_frames(mode):
    data=instruction_fixture();frame,stats=codec.encode(data,mode)
    assert codec.decode(frame)==data
    if mode:assert stats['loads']==768
