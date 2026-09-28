import collections
import datetime
import random
import pytest
from benchmarks import mysql_record_constraints as codec


@pytest.mark.parametrize('mode',range(1,5))
def test_order_constraints_and_large_alphabets(mode):
    rng=random.Random(17)
    for ids in ([],[0]*20,[rng.randrange(9) for _ in range(200)],rng.sample(range(5000),5000)):
        counts=[ids.count(i) for i in range(max(ids,default=-1)+1)]
        frame=codec.order_encode(ids,counts,mode)
        assert codec.order_decode(frame,counts)==ids


@pytest.mark.parametrize('mode',range(5))
def test_complete_records_and_literal_exceptions(mode):
    data=b''
    for i in range(22):
        row=[x.to_bytes(4,'little') for x in [i,23-i,100,0x80000000]]
        row+=[bytes(4)+b'\x0510.00',datetime.date(1900+i,3,1).toordinal().to_bytes(4,'little'),b'0123456789',b'x'*20,b'a'*(80 if i%2 else i)]
        data+=codec.wrap(codec.join_fields(row))
    data+=codec.wrap(b'noncanonical')+b'truncated tail'
    transformed,_=codec.transform(data,mode);assert codec.inverse(transformed)==data
    frame,_=codec.encode(data,mode);assert codec.decode(frame)==data
    damaged=bytearray(frame);damaged[8]^=1
    with pytest.raises(Exception):codec.decode(bytes(damaged))
