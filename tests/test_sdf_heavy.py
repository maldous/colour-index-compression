import random
import pytest
from benchmarks import sdf_heavy as codec
from benchmarks.sdf_geometry import fixed


def record(coords,types,bonds):
    header=b'test\nmetadata\n \n'+f'{len(coords):3d}{len(bonds):3d}  0  0  0  0  0  0  0  0  1 V2000\n'.encode()
    atoms=b''.join(b''.join(fixed(v) for v in xyz)+b' '+kind.ljust(3)+b' 0  0  0  0  0  0 0 0 0\n' for xyz,kind in zip(coords,types))
    links=b''.join(f'{a+1:3d}{b+1:3d}  1  0  0  0  0\n'.encode() for a,b in bonds)
    return header+atoms+links+b'M  END\n$$$$\n'


@pytest.mark.parametrize('model',range(4))
def test_exact_residuals_arbitrary_coordinates_signs_and_fragments(model):
    rng=random.Random(813)
    coords=[(0,0,0),(10000,0,0),(5000,8660,0),(5000,14860,0)]
    source=record(coords,[b'C',b'C',b'C',b'H'],[(0,1),(0,2),(1,2),(2,3)])
    source=source.replace(b'    0.0000',b'   -0.0000',1)*20
    for _ in range(6):
        coords=[tuple(rng.randrange(-100000,100000) for _ in range(3)) for _ in range(4)]
        source+=record(coords,[b'C',b'C',b'C',b'H'],[(0,1),(0,2),(1,2),(2,3)])
    source+=b'partial last record\n'
    for rep in range(4):
        raw,stats=codec.encode(source,model,rep)
        assert codec.decode(raw)==source
        if rep==2:assert abs(stats['heavy_model_bits']-stats['heavy_combinatorial_bits'])<1e-8
        if model:assert stats['heavy_predictions']>=40
        with pytest.raises((ValueError,IndexError)):codec.decode(raw+b'X')


def test_circle_candidates_use_only_decoded_neighbours():
    coords=[(0,0,0),(10000,0,0)]
    options,_=codec.heavy_options(2,coords,[-1,0,0],[[1,2],[0,2],[0,1]], [b'C']*3,3,10000,coords[0])
    assert (5000,8660,0) in options and (5000,-8660,0) in options
    assert codec.learn_radius(record([(0,0,0),(12300,0,0)],[b'C']*2,[(0,1)]))==12300
