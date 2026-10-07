"""Cross-implementation and framing gates for the experimental native path."""
import random
import pytest
from benchmarks.relational_mixer import Native,encode,decode
from benchmarks.relational_portfolio import encode as portfolio,decode as restore
from benchmarks.mixer_ppm_large import encode as old_encode

@pytest.mark.parametrize('mode',range(4))
def test_native_agrees_with_reference_on_switching_relations(mode):
    r=random.Random(12671)
    data=bytes(range(256))+bytes(r.randrange(4) for _ in range(256))+b'abacadax'*32
    native=Native();blob=native.encode(data,2,mode)
    assert blob==encode(data,2,mode)
    assert native.decode(blob)==decode(blob)==data
    for bad in (blob[:-1],blob+b'\0',blob[:10]):
        with pytest.raises((ValueError,IndexError)):
            native.decode(bad)


def test_exact_incumbent_retention_and_container_verification():
    data=random.Random(16583).randbytes(1024)
    old=old_encode(data)
    blob=portfolio(data,incumbent=old)
    assert len(blob)<=len(old)
    assert restore(blob)==data
    with pytest.raises(ValueError):restore(blob+b'\0')
