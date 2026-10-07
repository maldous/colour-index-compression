import pytest
from benchmarks.ecoff_call_trace_analysis import constrained_loss, shuffled_code


def test_forced_branch_cost_uses_actual_predictions():
    records=[(1 << 30) | (((5 >> bit) & 1) << 31) for bit in range(20,-1,-1)]
    row=constrained_loss(records,[4,5,12],5)
    assert row['paq_bits']==21
    assert row['forced_bits']==19
    assert row['forced_paq_bits']==19
    assert row['remaining_paq_bits']==2
    with pytest.raises(ValueError): constrained_loss(records,[1],5)


def test_bsr_target_filter_is_big_endian_and_absolute():
    inst=(0x34 << 26)|(26 << 21)|5
    assert shuffled_code(bytes(4)+inst.to_bytes(4,'little'))==bytes(4)+(inst+1).to_bytes(4,'big')
