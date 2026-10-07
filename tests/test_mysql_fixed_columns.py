import random
import datetime
import pytest
from benchmarks import mysql_fixed_columns as codec
from benchmarks import mysql_record_constraints as base


@pytest.mark.parametrize('mode',[1,2,3,4])
def test_fixed_columns_preserve_all_bytes(mode):
    rng=random.Random(421);data=b''
    for i in range(25):
        row=[i.to_bytes(4,'little')]*4+[bytes(4)+b'\x031.0',datetime.date(2000,1,1).toordinal().to_bytes(4,'little'),rng.randbytes(10),b'n'*20,b'address']
        data+=base.wrap(base.join_fields(row))
    data+=b'tail'
    frame,_=codec.encode(data,mode);assert codec.decode(frame)==data


def test_alphabet_edge_widths():
    for alphabet in (1,2,3,64,256):
        ids=[i%alphabet for i in range(1003)];width=(alphabet-1).bit_length()
        assert codec.unpack_ids(codec.pack_ids(ids,width),len(ids),width)==ids
