from benchmarks.hutter_structure import decode, encode


def test_all_modes_preserve_whitespace_entities_numeric_spelling_and_order():
    data = (b'<?xml version="1.0"?>\n<page><title> 42 </title><id>00042</id>'
            b'<revision><text xml:space="preserve">A &amp; B &lt;x&gt;  007\n</text>'
            b'</revision></page>\n')
    for mode in ("control", "C", "D"):
        frame, costs = encode(data, mode)
        assert decode(frame) == data
        assert costs["physical_bytes"] == sum(value for key, value in costs.items() if key.endswith("_bytes") and key != "physical_bytes")


def test_page_skeletons_share_complete_pages_and_keep_outside_literal():
    page = b'<page><title>T</title><revision><id>1</id><text xml:space="preserve">x</text></revision></page>'
    data = b'header\n' + page + b'\n' + page.replace(b'>T<', b'>U<').replace(b'>1<', b'>2<') + b'\ntrailer'
    frame, costs = encode(data, "D")
    assert decode(frame) == data
    assert costs["page_records"] == 2
    assert costs["dictionary_bytes"] > 0


def test_truncated_page_is_literal_fallback_and_never_needs_xml_validity():
    data = b'prefix <page><title>unfinished &amp; 0007</title><text> <bad'
    frame, costs = encode(data, "D")
    assert decode(frame) == data
    assert costs["page_records"] == 0
    assert costs["literal_bytes"] == len(data)


def test_page_skeleton_escapes_nul_sequence_inside_a_recognized_comment():
    data = b'<page><!--\x00\x01--><title>x</title></page>'
    frame, _ = encode(data, "D")
    assert decode(frame) == data
