import struct
import pytest
from benchmarks import ecoff_procedure_feedback as codec
from tests.test_ecoff_section_pointers import object_file


@pytest.mark.parametrize('mode', range(4))
def test_causal_history_with_wraparound_and_parent_constraints(mode):
    original = bytearray(object_file()); where, n = codec.parent.procedure.tables(original)[0]
    values = [0xffffffff, 0, 0x80000003]
    for i in range(n): struct.pack_into('<II', original, where + 8 * i, values[i], 777)
    frame, _ = codec.transform(bytes(original), mode)
    assert codec.inverse(frame) == original
    frame, _ = codec.transform(b'arbitrary unsupported\xff\0', mode)
    assert codec.inverse(frame) == b'arbitrary unsupported\xff\0'


def test_repeated_descriptor_predicts_only_previously_observed_lengths():
    original = bytearray(object_file()); where, n = codec.parent.procedure.tables(original)[0]
    for i in range(n): struct.pack_into('<II', original, where + 8 * i, 4 * (i + 1), 777)
    frame, stats = codec.transform(bytes(original), 1)
    assert stats['exact_predictions'] == 1
    assert codec.inverse(frame) == original
