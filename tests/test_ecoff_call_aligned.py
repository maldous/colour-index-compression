import struct
from benchmarks import ecoff_call_aligned as codec
from tests.test_ecoff_calls import object_file


def test_alignment_preserves_arbitrary_targets_and_exceptions():
    data=object_file();raw,stats=codec.transform(data,1)
    assert codec.inverse(raw)==data
    size=int.from_bytes(raw[-13:-5],'little')
    transformed=codec.parent.inverse(raw[:-13-size])
    for functions,calls in codec.groups(data):
        for where,word,pc in calls:
            a=struct.unpack_from('<I',data,where)[0];b=struct.unpack_from('<I',transformed,where)[0]
            displacement=a&codec.MASK
            signed=displacement-(1<<21) if displacement&(1<<20) else displacement
            target=pc+signed*4
            if target in functions:
                aligned=((b&codec.MASK)+word)&codec.MASK
                assert aligned%4==3 and aligned//4==functions.index(target)
            else:
                assert a==b
    assert stats['targets_in_candidates']==3
