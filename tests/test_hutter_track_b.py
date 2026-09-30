import subprocess
import sys

from benchmarks.hutter_track_b import decode_archive, encode_archive, line_prefix_transform, inverse_line_prefix, copy_delta_transform, inverse_copy_delta, static_xml_transform, inverse_static_xml, serialize_tokens, deserialize_tokens, XML_TOKENS


def test_every_representation_round_trips_and_charges_framing():
    data = (b"<page title=\"same title\"> a repeated record </page>\n" * 80) + b"tail"
    for mode in ("control", "space-mask", "line-prefix", "copy-delta", "static-xml", "static-xml-table"):
        archive, costs = encode_archive(data, mode)
        assert decode_archive(archive) == data
        assert costs["framing_bytes"] >= 6
        assert costs["payload_bytes"] + costs["metadata_bytes"] + costs["framing_bytes"] == len(archive)


def test_line_prefix_preserves_empty_and_trailing_records():
    data = b"alpha\nalpha beta\n\nalpha beta\n"
    assert inverse_line_prefix(line_prefix_transform(data)) == data


def test_copy_delta_is_causal_and_preserves_small_edits():
    source = bytearray((b"same causal block with one predictable change " * 30)[:1024])
    edited = bytearray(source)
    edited[200] ^= 7
    data = bytes(source) + bytes(edited) + bytes(source)
    transformed, stats = copy_delta_transform(data)
    assert stats["copy_delta_copied_blocks"] >= 1
    assert inverse_copy_delta(transformed) == data


def test_static_xml_grammar_escapes_and_restores_every_token():
    data = b'<page><title>A &amp; B</title><text xml:space="preserve">x\xff</page>'
    transformed, stats = static_xml_transform(data)
    assert stats["static_xml_replacements"] >= 4
    assert inverse_static_xml(transformed) == data
    assert deserialize_tokens(serialize_tokens(XML_TOKENS)) == XML_TOKENS


def test_archive_only_fresh_decoder(tmp_path):
    data = b"alpha beta gamma\n" * 100
    archive, _ = encode_archive(data, "space-mask")
    archive_path = tmp_path / "input.htb"
    restored = tmp_path / "restored"
    archive_path.write_bytes(archive)
    result = subprocess.run([sys.executable, "-m", "benchmarks.hutter_track_b", "decode", "--archive", str(archive_path), "--output", str(restored)], check=False)
    assert result.returncode == 0
    assert restored.read_bytes() == data
