import datetime
from benchmarks import competitive_database_portfolio as codec
from benchmarks import mysql_record_constraints as records
from tests.test_competitive_codec import legacy_raw


def test_detect_select_and_restore_complete_records():
    row=[(1).to_bytes(4,'little')]*4+[bytes(4)+b'\x031.0',datetime.date(2000,1,1).toordinal().to_bytes(4,'little'),b'0'*10,b'n'*20,b'address']
    data=records.wrap(records.join_fields(row))*50
    assert codec.recognizes(data)
    frame,selection=codec.encode(data,legacy_cache=legacy_raw(data))
    assert len(frame)==min(r['size'] for r in selection['trials'])
    assert codec.decode(frame)==data
    assert not codec.recognizes(b'random record'*100)
