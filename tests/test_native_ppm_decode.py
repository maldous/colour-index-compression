import random
from pathlib import Path
import pytest
from cix.ppm import encode_ppm,decode_ppm
from benchmarks.native_ppm_decode import load

pytestmark=pytest.mark.skipif(not Path('results/leaderboard/native_ppm_decode.so').exists(),reason='native decoder not built')


@pytest.mark.parametrize('order',[0,1,4,8])
@pytest.mark.parametrize('method',range(4))
@pytest.mark.parametrize('exclusion',[False,True])
def test_fixed_matches_independent_python(order,method,exclusion):
    data=random.Random(29).randbytes(128)+b'abacabacadabra'*12+bytes(range(256))
    history=b'dabra\x00'*100
    blob=encode_ppm(data,max_order=order,escape_method=method,update_exclusion=exclusion,secondary_escape=False,prefix_history=history)
    assert load()(blob,source_length=len(data),prefix_history=history)==decode_ppm(blob,source_length=len(data),prefix_history=history)==data


@pytest.mark.parametrize('order',[0,1,4,8])
@pytest.mark.parametrize('exclusion',[False,True])
def test_see_warmup_and_rescale(order,exclusion):
    data=b'\0'*16500+random.Random(41).randbytes(300)
    history=(b'0123456789abcdef'*5000)+b'\0'*17000
    blob=encode_ppm(data,max_order=order,update_exclusion=exclusion,secondary_escape=True,prefix_history=history)
    assert load()(blob,source_length=len(data),prefix_history=history)==decode_ppm(blob,source_length=len(data),prefix_history=history)==data


def test_empty_and_bad_header():
    dec=load();blob=encode_ppm(b'',max_order=0)
    assert dec(blob,source_length=0)==b''
    for invalid in (b'',blob[:2],blob+b'\0',bytes([5,9,0,0]),bytes([5,1,2,0])):
        with pytest.raises(ValueError):dec(invalid,source_length=0)
