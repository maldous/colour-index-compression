import pytest

from benchmarks.domain_database_csv import decode, encode, inspect
from benchmarks.domain_database_prepare import first_nonblank_records


def test_csv_adapter_preserves_quotes_commas_and_crlf_exactly():
    data = b'country,value,note\r\nUS,1,"a,b"\r\nCA,1,"a,b"\r\n'
    frame = encode(data, "dictionary_remaining")
    assert decode(frame) == data
    assert decode(encode(data, "literal")) == data
    profile = inspect(data)
    assert profile["eligible"] and profile["packing"]["alignment_padding_bytes"] == 0


def test_csv_adapter_falls_back_to_literal_for_multiline_quoted_field():
    # Physical-line parsing must never reinterpret an RFC4180 multiline field.
    data = b'key,note\n1,"first line\nsecond line"\n'
    frame = encode(data, "dictionary_remaining")
    assert frame[6] == 0
    assert decode(frame) == data
    assert inspect(data)["eligible"] is False


def test_csv_adapter_rejects_unknown_variant_and_corrupt_frame():
    with pytest.raises(ValueError, match="unknown database CSV variant"):
        encode(b"a,b\n", "rank")
    with pytest.raises(ValueError):
        decode(b"not a frame")


def test_first_nonblank_records_preserves_original_line_bytes_and_order():
    data = b"\nA, one\r\n\t\nB, two\nC, three\r\n"
    assert first_nonblank_records(data, 2) == b"A, one\r\nB, two\n"
    with pytest.raises(ValueError):
        first_nonblank_records(data, 4)
