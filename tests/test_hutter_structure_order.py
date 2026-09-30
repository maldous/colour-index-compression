from benchmarks import hutter_structure_order as structure


def test_balanced_markup_preserves_byte_order_and_forces_closes():
    data = b'<r a="1"><x>text</x><!-- c --><![CDATA[</>]]></r>'
    transformed, info = structure.encode(data)
    assert info["mode"] == 1
    assert info["forced_closing_tags"] == 2
    assert structure.decode(transformed, info["mode"], info) == data


def test_incomplete_and_malformed_markup_are_literal_fallbacks():
    for data in (b'<r><x>unfinished', b'<r a="unterminated><x></x></r>', b'plain < text', b'\0</>'):
        transformed, info = structure.encode(data)
        assert info["mode"] == 0
        assert transformed == data
        assert structure.decode(transformed, info["mode"], info) == data


def test_outer_frame_round_trip_uses_selected_complete_frame():
    data = b'<r><x>text</x></r>' * 10
    frame, info = structure.encode_frame(data, "-4")
    assert info["physical_bytes"] == len(frame)
    assert info["outer_framing_bytes"] + info["selector_bytes"] + info["raw_payload_bytes"] == info["raw_complete_bytes"]
    assert info["raw_complete_bytes"] >= len(frame)
    assert structure.decode_frame(frame) == data
