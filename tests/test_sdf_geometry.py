import random
import pytest
from benchmarks import sdf_geometry as codec


def molecule(values):
    atoms=b''.join(b''.join(codec.fixed(v) for v in vector)+b' C   0  0  0  0  0  0  0  0  0  0  0  0\n' for vector in values)
    n=len(values);bonds=b''.join(f'{i:3d}{i+1:3d}  1  0  0  0  0\n'.encode() for i in range(1,n))
    return b'test\nmetadata\n \n'+f'{n:3d}{n-1:3d}  0  0  0  0  0  0  0  0  1 V2000\n'.encode()+atoms+bonds+b'M  END\n$$$$\n'


@pytest.mark.parametrize('mode',(0,1,2))
def test_geometric_round_trip_and_unsupported_records(mode):
    rng=random.Random(732)
    source=b''.join(molecule([tuple(rng.randrange(-999999,999999) for _ in range(3)) for _ in range(4)]) for _ in range(8))
    source+=molecule([(0,0,0),(10000,0,0)]).replace(b'    0.0000',b'   -0.0000',1)
    source+=b'not a complete molecule\n'
    for representation in range(3):
        blob,stats=codec.encode(source,mode,representation,palette_size=8)
        assert stats['parsed_records']==8
        assert codec.decode(blob)==source
        with pytest.raises((ValueError,IndexError)):codec.decode(blob+b'\x80')


def test_palette_escape_and_large_type_classes():
    source=molecule([(0,0,0),(8660,5000,0),(17321,10000,0)])*1500
    blob,stats=codec.encode(source,2,2,palette_size=1)
    assert stats['atoms']==4500
    assert codec.decode(blob)==source
