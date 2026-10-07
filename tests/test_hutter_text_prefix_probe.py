from benchmarks.hutter_text_prefix_probe import prefix


def test_prefix_has_requested_initial_bytes(tmp_path):
    source = tmp_path / "enwik9"
    source.write_bytes(b"abcdefgh")
    target = tmp_path / "prefix"
    prefix(source, target, 5, expected_size=8)
    assert target.read_bytes() == b"abcde"
