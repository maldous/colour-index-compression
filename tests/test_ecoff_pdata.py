import struct
import pytest
from benchmarks import ecoff_pdata as codec
from tests.test_ecoff_section_pointers import object_file


@pytest.mark.parametrize('mode', range(4))
def test_full_parent_round_trip_and_address_flags(mode):
    original = bytearray(object_file())
    where, count = codec.tables(original)[0]
    for i in range(count):
        value = struct.unpack_from('<I', original, where + i * 8)[0]
        struct.pack_into('<I', original, where + i * 8, value | i % 4)
    frame, stats = codec.transform(bytes(original), mode)
    assert codec.inverse(frame) == original
    if mode >= 2: assert stats['constrained_addresses'] == count
    assert codec.inverse(codec.transform(b'unsupported literal\0\xff', mode)[0]) == b'unsupported literal\0\xff'


def test_nonmonotone_procedure_table_remains_literal():
    original = bytearray(object_file()); where, _ = codec.tables(original)[0]
    original[where + 8:where + 12] = original[where:where + 4]
    for mode in (2, 3):
        frame, stats = codec.transform(bytes(original), mode)
        assert stats['selected_tables'] == 0 and codec.inverse(frame) == original


def test_invalid_outer_metadata_is_rejected():
    frame, _ = codec.transform(object_file(), 2)
    size = int.from_bytes(frame[-13:-5], 'little'); start = len(frame) - 13 - size
    corrupt = bytearray(frame); corrupt[start + 1] = 2
    with pytest.raises(ValueError, match='selector'): codec.inverse(bytes(corrupt))
