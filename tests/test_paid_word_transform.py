import pytest
from benchmarks import paid_word_transform as codec


@pytest.mark.parametrize('mode',[0,1])
@pytest.mark.parametrize('data',[
    b'', bytes(range(256))*4,
    b'Words words WORDS &quot; Words words\x80\xff\x0c\x07\x06\x08\x40\n'*100,
    b'The dictionary is transmitted. The dictionary is decoded exactly.\n'*100,
])
def test_paid_dictionary_and_arbitrary_exceptions_restore(data,mode):
    frame,stats=codec.encode(data,mode)
    assert codec.decode(frame)==data
    assert stats['physical_bytes']==len(frame)
    if mode: assert stats['dictionary_bytes']==len(codec.dictionary(data))
