import random
import pytest
from benchmarks import markup_columns as codec


@pytest.mark.parametrize('mode',(1,2))
@pytest.mark.parametrize('repeat',(False,True))
def test_lexical_preservation_and_context_modes(mode,repeat):
    data=(b'header\0<?xml version="1.0"?><x><a q=">">one</a><a>one</a>'
          b'<b><![CDATA[<a>not tags</a>]]><!-- <x> -->two\0three</b>'
          b'<a>one</a><bad><a>three</a></x>tail<unfinished')
    frame,stats=codec.encode(data,mode,repeat)
    assert codec.decode(frame)==data
    assert stats['repeated_fields']==(2 if repeat else 0)
    with pytest.raises(ValueError):codec.decode(frame+b'X')
    with pytest.raises(ValueError):codec.decode(frame[:-1])


def test_arbitrary_bytes_and_literal_control_sequences():
    rng=random.Random(788)
    for _ in range(20):
        data=rng.randbytes(4096)+b'<x>\0\1\0\2</x><x>bytes</x>'
        assert codec.decode(codec.encode(data)[0])==data
        assert codec.decode(codec.encode(data,3)[0])==data
        assert codec.decode(codec.encode(data,4)[0])==data


@pytest.mark.parametrize('mode',(3,4))
def test_zero_cost_closing_name_predictions(mode):
    data=(b'<long_name x="a\0\1b">text<!-- </wrong>\0\1 -->'
          b'<![CDATA[</false>\0]]><x/>one</long_name><bad><child>two</bad>'
          b'<a q="<> </> </!>">three\0\1</a><odd>four</ odd>literal </> </!> </!!>')
    frame,stats=codec.encode(data,mode)
    assert stats['forced_closing_tags']==2
    assert codec.decode(frame)==data
