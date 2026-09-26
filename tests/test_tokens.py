from cix.tokens import encode_token_block,decode_token_block

def test_token_model_round_trip_text_code_json():
    samples=[
        (b"the quick brown fox jumps over the lazy dog. "*100),
        (b'{"id":1,"student":"alice","active":true}\n'*100),
        (b"int value = value + offset;\n"*120),
    ]
    for data in samples:
        payload,_=encode_token_block(data)
        assert decode_token_block(payload,source_length=len(data))==data
        assert len(payload)<len(data)
