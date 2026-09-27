import os

from cix.ppm import ESCAPE_LEARNED, decode_ppm, encode_ppm, estimate_ppm_bits


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


def test_ppm_estimator_prefers_predictive_context():
    data = bytes(range(64)) * 80
    order0 = estimate_ppm_bits(data, max_order=0)
    order1 = estimate_ppm_bits(data, max_order=1)
    assert order1 < order0


def test_ppm_recent_history_warmup_round_trip_and_gain():
    prefix=(b"shared recurring context sequence|"*300)
    data=(b"shared recurring context sequence|"*120)
    cold=encode_ppm(data,max_order=4)
    warm=encode_ppm(data,max_order=4,prefix_history=prefix)
    assert decode_ppm(
        warm,
        source_length=len(data),
        prefix_history=prefix,
    )==data
    assert len(warm)<len(cold)


def test_ppm_warmup_is_deterministic_from_decoder_history():
    prefix=bytes(range(64))*100
    data=bytes(range(64))*30
    first=encode_ppm(data,max_order=3,prefix_history=prefix)
    second=encode_ppm(data,max_order=3,prefix_history=prefix)
    assert first==second
    assert decode_ppm(
        first,
        source_length=len(data),
        prefix_history=prefix,
    )==data


def test_ppm_learned_escape_round_trip():
    data = (
        b"alpha=17|beta=23|gamma=41\n"
        b"alpha=18|beta=23|gamma=43\n"
        b"alpha=19|beta=29|gamma=47\n"
    ) * 80
    payload = encode_ppm(
        data,
        max_order=4,
        escape_method=ESCAPE_LEARNED,
    )
    assert decode_ppm(payload, source_length=len(data)) == data
