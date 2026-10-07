import pytest
from benchmarks import ecoff_symbol_text as codec
from tests.test_ecoff_got import archive


@pytest.mark.parametrize('mode',[0,1,2])
def test_symbol_permutations_and_dependent_tables_restore(mode):
    data=archive();raw,stats=codec.transform(data,mode)
    assert stats['symbol_bytes']>0 and codec.inverse(raw)==data
    table=codec.permutation(mode)
    assert bytes(range(256)).translate(table).translate(table)==bytes(range(256))
    assert codec.inverse(codec.transform(b'unsupported\x00\n_ data',mode)[0])==b'unsupported\x00\n_ data'
