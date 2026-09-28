import pytest
from benchmarks.paq_clean_inventory import parse


def test_clean_nested_leaf_inventory_does_not_double_count_parents():
    text=' 0 | tar | 100 bytes [0 - 99]\n 0-0 | text | 60 bytes [0 - 59]\n 0-1 | zlib | 40 bytes [60 - 99]\n 0-1-0 | text | 80 bytes [0 - 79]\n'
    row=parse(text)
    assert row['leaf_types']=={'text':2} and row['leaf_declared_bytes']=={'text':140}
    assert row['blocks']==4 and row['leaf_blocks']==2


def test_progress_contaminated_label_is_never_accepted():
    with pytest.raises(ValueError):parse(' 0 | teCompressing... 85.65%\x08xt | 10 bytes [0 - 9]\n')


def test_x86_label_and_no_silent_skips():
    valid=' 0 | x86/64 | 10 bytes [0 - 9]\n'
    assert parse(valid)['leaf_types']=={'x86/64':1}
    with pytest.raises(ValueError):parse(valid+' 1 | illegal\x08label | 5 bytes [10 - 14]\n')
