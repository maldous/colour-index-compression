import random
import pytest
from benchmarks import sdf_hydrogen as codec
from benchmarks.sdf_geometry import fixed


def record(coords,types,bonds):
    n=len(coords);m=len(bonds)
    header=b'test\nmetadata\n \n'+f'{n:3d}{m:3d}  0  0  0  0  0  0  0  0  1 V2000\n'.encode()
    atoms=b''.join(b''.join(fixed(v) for v in vector)+b' '+kind.ljust(3)+b' 0  0  0  0  0  0  0  0  0  0  0  0\n' for vector,kind in zip(coords,types))
    links=b''.join(f'{a+1:3d}{b+1:3d}  1  0  0  0  0\n'.encode() for a,b in bonds)
    return header+atoms+links+b'M  END\n$$$$\n'


def test_integer_directions_and_rounding():
    for vector,phase in (((1,0),0),((0,1),1<<30),((-1,0),1<<31),((0,-1),3<<30)):
        delta=(codec.angle(*vector)-phase+(1<<31))%(1<<32)-(1<<31)
        assert abs(delta)<=4
        assert codec.direction(phase,6200)==(vector[0]*6200,vector[1]*6200,0)
    assert codec.rounded(-3,2)==-2 and codec.rounded(3,2)==2


@pytest.mark.parametrize('model',(0,1,2))
def test_exact_coordinates_including_negative_zero_and_exceptions(model):
    coords=[(0,0,0),(10000,0,0),(0,6200,0),(-6200,0,0),(0,-6200,0)]
    source=record(coords,[b'C',b'C',b'H',b'H',b'H'],[(0,1),(0,2),(0,3),(0,4)])
    source=source.replace(b'    0.0000',b'   -0.0000',1)*70+b'partial record\n'
    for rep in (0,1,2,3):
        frame,stats=codec.encode(source,model,rep)
        assert codec.decode(frame)==source
        assert stats['parsed_records']==70
        if model==2:
            assert stats['predicted_atoms']==210
            assert stats['within_two_units']==210
            assert stats['candidate_order_combinatorial_bits']<stats['candidate_independent_bits']
            if rep==2:assert abs(stats['choice_arithmetic_prediction_bits']-stats['candidate_order_combinatorial_bits'])<1e-8
        with pytest.raises((ValueError,IndexError)):codec.decode(frame+b'X')


def test_arbitrary_layouts_remain_lossless():
    rng=random.Random(91);source=b''
    for _ in range(40):
        coords=[tuple(rng.randrange(-100000,100000) for _ in range(3)) for _ in range(5)]
        source+=record(coords,[b'C',b'C',b'H',b'H',b'H'],[(0,1),(0,2),(0,3),(0,4)])
    for model in (1,2):
        for rep in (0,1,2,3):assert codec.decode(codec.encode(source,model,rep)[0])==source
