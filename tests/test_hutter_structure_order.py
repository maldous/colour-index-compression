import subprocess
import sys

from benchmarks import hutter_structure_order as structure


def test_transform_api_does_not_eagerly_load_competitive_portfolio():
    result = subprocess.check_output([sys.executable, "-c", "import sys; import benchmarks.hutter_structure_order; print('benchmarks.competitive_codec' in sys.modules)"], text=True)
    assert result.strip() == "False"


def test_balanced_markup_preserves_byte_order_and_forces_closes():
    data = b'<r a="1"><x>text</x><!-- c --><![CDATA[</>]]></r>'
    transformed, info = structure.encode(data)
    assert info["mode"] == 1
    assert info["forced_closing_tags"] == 2
    assert structure.decode(transformed, info["mode"], info) == data


def test_malformed_markup_is_literal_fallback():
    for data in (b'<r a="unterminated><x></x></r>', b'plain < text', b'\0</>'):
        transformed, info = structure.encode(data)
        assert info["mode"] == 0
        assert transformed == data
        assert structure.decode(transformed, info["mode"], info) == data


def test_partial_boundaries_keep_unmatched_tags_literal_but_predict_local_close():
    data = b'</outside><r><x>inner</x>'
    transformed, info = structure.encode(data)
    assert info["mode"] == 1
    assert info["forced_closing_tags"] == 1
    assert structure.decode(transformed, info["mode"], info) == data


def test_outer_frame_round_trip_uses_selected_complete_frame():
    data = b'<r><x>text</x></r>' * 10
    frame, info = structure.encode_frame(data, "-4")
    assert info["physical_bytes"] == len(frame)
    assert info["outer_framing_bytes"] + info["selector_bytes"] + info["raw_payload_bytes"] == info["raw_complete_bytes"]
    assert info["raw_complete_bytes"] >= len(frame)
    assert structure.decode_frame(frame) == data
