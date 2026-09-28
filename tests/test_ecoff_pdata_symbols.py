import struct
import pytest
from benchmarks import ecoff_pdata_symbols as codec
from tests.test_ecoff_section_pointers import object_file


@pytest.mark.parametrize('mode', (0, 1))
def test_all_parent_layers_and_arbitrary_word_wraparound(mode):
    source = bytearray(object_file()); where, n = codec.procedure.tables(source)[0]
    for i, value in enumerate([0xffffffff, 0, 0xdeadbeef][:n]):
        struct.pack_into('<I', source, where + i * 8, value)
    frame, _ = codec.transform(bytes(source), mode)
    assert codec.inverse(frame) == source
    frame, _ = codec.transform(b'literal unsupported\x00\xff', mode)
    assert codec.inverse(frame) == b'literal unsupported\x00\xff'


def test_unknown_combination_rejected():
    frame, _ = codec.transform(object_file())
    with pytest.raises(ValueError): codec.inverse(frame[:-6] + b'\x02' + frame[-5:])
