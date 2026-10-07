import os

import pytest

from benchmarks.hutter_structure_columns import MAGIC, decode, encode, extract_columns


def test_d2_aligns_shared_page_slots_without_changing_bytes():
    page = (b'<page><title>%s</title><id>%06d</id><revision><id>%06d</id>'
            b'<text xml:space="preserve"> %s &amp; 007\n</text></revision></page>')
    data = b'head\n' + page % (b'One', 1, 11, b'A') + b'\n' + page % (b'Two', 2, 12, b'B') + b'\ntail'
    frame, accounting = encode(data)
    assert decode(bytes(frame)) == data
    assert accounting["pages"] == 2
    assert accounting["skeletoncount"] == 1
    assert accounting["slotcolumns"] > 1
    assert accounting["physical_bytes"] == sum(accounting[key] for key in ("descriptor_bytes", "dictionary_bytes", "literal_bytes", "column_stream_bytes", "framing_bytes"))


def test_d2_handles_empty_values_nuls_entities_and_truncated_pages_literally():
    complete = b'<page><!--\x00\x01--><title></title><text xml:space="preserve"> &lt; \n</text></page>'
    data = b'prefix' + complete + b'<page><title>truncated'
    frame, accounting = encode(data)
    assert decode(bytes(frame)) == data
    assert accounting["pages"] == 1
    assert accounting["literal_bytes"] == len(b'prefix') + len(b'<page><title>truncated')


def test_d2_column_profile_exposes_field_classes_raw_costs_and_never_marks_text_eligible():
    data = (b'<page><title>A</title><id>1</id><revision><id>10</id><timestamp>2026-01-01</timestamp>'
            b'<contributor><id>C1</id><username>U</username></contributor><text xml:space="preserve"> </text>'
            b'</revision></page><page><title>A</title><id>2</id><revision><id>11</id><timestamp>2026-01-02</timestamp>'
            b'<contributor><id>C2</id><username>U</username></contributor><text xml:space="preserve"></text></revision></page>')
    profile = extract_columns(data)
    classes = {column["field_class"] for column in profile["columns"]}
    assert {"title", "pageid", "revisionid", "timestamp", "contributor", "articletext"} <= classes
    text = [column for column in profile["columns"] if column["field_class"] == "articletext"]
    assert text and all(not column["eligible_short_field"] for column in text)
    assert all(column["raw_column_table_bytes"] >= column["raw_values_bytes"] for column in profile["columns"])


def test_d2_random_adversarial_round_trips_and_rejects_simple_corruption():
    rng = __import__("random").Random(7302026)
    noisy = bytes(rng.randrange(256) for _ in range(1024))
    data = noisy + b'<page><title>x</title><text>y</text></page>' + os.urandom(257)
    frame, _ = encode(data)
    assert decode(bytes(frame)) == data
    with pytest.raises(ValueError):
        decode(MAGIC[:-1] + b'X' + frame[len(MAGIC):])
    with pytest.raises(ValueError):
        decode(frame[:-1])
