import struct
import pytest
from benchmarks import ecoff_call_entries as codec
from tests.test_ecoff_calls import object_file


@pytest.mark.parametrize('mode', range(6))
def test_expanded_entry_set_and_literal_branches(mode):
    data = bytearray(object_file()); start, _ = codec.parent.parent.base.sections(data)[b'.text']
    # Word 2 calls address text+24: the text+8 symbol's +16 entry.
    struct.pack_into('<I', data, start + 8, (codec.CALL << 21) | 3)
    raw, stats = codec.transform(bytes(data), mode)
    assert codec.inverse(raw) == data
    assert stats['targets_in_candidates'] == 4 and stats['calls'] == 6
    if mode == 4:
        assert stats['choice_model_bits'] == pytest.approx(stats['candidate_combinatorial_bits'])
