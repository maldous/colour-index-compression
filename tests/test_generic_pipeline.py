import hashlib
import random
from pathlib import Path

import pytest

from cix.pipeline import (FRAME, HEADER, EFFORTS, ROUTES, _bwt, _cix, _uncix,
                          _count_range, accounting, decode_file, encode_file,
                          profile, route_decode, route_encode, shortlist, trial)


@pytest.mark.parametrize("route", [r for r in ROUTES.values() if r not in ("ppm", "mixture")])
@pytest.mark.parametrize("kind", ["noise", "repeated", "numeric", "small-alphabet"])
def test_routes_exact(route, kind):
    rng = random.Random(106)
    data = {"noise": rng.randbytes(1203), "repeated": (b"abcd000000xyz"*93)[:1203],
            "numeric": b"".join(i.to_bytes(4,"little") for i in range(301)),
            "small-alphabet": bytes(rng.randrange(4) for _ in range(1203))}[kind]
    for backend in ("cix", "deflate", "count-range"):
        blob = route_encode(route, data, backend)
        assert route_decode(route, blob, len(data)) == data
        record = accounting(route, blob, len(data))
        assert sum(record[k] for k in ("framing_bytes","structural_bytes","stream_descriptor_bytes",
                                       "count_table_bytes","coded_payload_bytes")) == len(blob)+FRAME.size


def test_paid_same_count_ordering():
    data = bytes(random.Random(14).choices(range(11), k=2345))
    assert _uncix(_cix(data),len(data)) == data
    assert _uncix(_count_range(data),len(data)) == data


def test_lz_decoded_history():
    prefix = random.Random(99).randbytes(4096)
    data = prefix[-2048:]+b"suffix"
    blob = route_encode("lz",data,"cix",prefix)
    assert route_decode("lz",blob,len(data),prefix) == data


def test_high_entropy_repetition_not_bypassed():
    phrase = random.Random(7).randbytes(1024)
    data = phrase*32
    features = profile(data,8192)
    assert features["entropy"] > 7.5
    assert "lz" in shortlist(features,"fast")
    blob = route_encode("lz",data,"hybrid")
    assert len(blob) < len(data)//4
    assert route_decode("lz",blob,len(data)) == data


@pytest.mark.parametrize("data", [b"", b"a", random.Random(38).randbytes(65537), b"A"*70000])
def test_archive_bound_and_corruption(tmp_path, data):
    src = tmp_path/"in"; arc = tmp_path/"out.cix"; restored=tmp_path/"restored"
    src.write_bytes(data)
    encode_file(src,arc,effort="fast")
    assert arc.stat().st_size <= len(data)+HEADER.size+FRAME.size*(1+(len(data)+32767)//32768)
    decode_file(arc,restored)
    assert restored.read_bytes() == data
    corrupt = bytearray(arc.read_bytes()); corrupt[-1] ^= 1; arc.write_bytes(corrupt)
    with pytest.raises(ValueError): decode_file(arc,restored)


def test_worker_budget():
    result = trial("bwt",random.Random(1).randbytes(65536),"cix",b"",0.00001,256)
    assert result[0] is None
    assert result[3] == "TIME_BUDGET"


def test_malformed_streams():
    from cix.pipeline import unstreams, STREAM
    with pytest.raises(ValueError): unstreams(b"\x01"+STREAM.pack(0,2**32-1,0),1024)
    with pytest.raises(ValueError): route_decode("runs",b"A\x00",1)
    with pytest.raises(ValueError): route_decode("lz",b"\x00",5)


def test_bwt_matches_legacy_convention():
    from cix.bwt import _bwt_transform_python
    for data in (b"banana",b"abracadabra",b"A"*99,random.Random(4).randbytes(99)):
        assert _bwt(data) == _bwt_transform_python(data)


@pytest.mark.parametrize("route", ["ppm", "mixture"])
def test_escalated_generic_models(route):
    data = b"causal byte contexts and generic history; "*4
    blob = route_encode(route,data,"hybrid")
    assert route_decode(route,blob,len(data)) == data
