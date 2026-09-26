import os

from cix.ppm import decode_ppm,encode_ppm


def test_ppm_round_trip_repetitive_and_random():
    for data in (
        b"the quick brown fox jumps over the lazy dog. "*100,
        b'{"id":1,"name":"alice","active":true}\n'*100,
        os.urandom(1500),
    ):
        for order in (2,4):
            payload=encode_ppm(data,max_order=order)
            assert decode_ppm(payload,source_length=len(data))==data


def test_ppm_compresses_repeated_language_like_data():
    data=(b"compression models learn recurring contexts and recurring words. "*150)
    payload=encode_ppm(data,max_order=4)
    assert len(payload)<len(data)//3
