from cix.record import encode_record_block,decode_record_block

def test_record_conditioned_multinomial_round_trip():
    rows=[]
    for i in range(1000):
        rows.append(i.to_bytes(4,"little")+b"ACTIVE  "+(i%7).to_bytes(2,"little")+b"\x00"*18)
    data=b"".join(rows)
    payload,name=encode_record_block(data,beam=8)
    assert decode_record_block(payload,source_length=len(data))==data
    assert len(payload)<len(data)//4
    assert name.startswith("record-multinomial-w")
