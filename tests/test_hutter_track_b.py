import subprocess
import sys

from benchmarks.hutter_track_b import decode_archive, encode_archive, line_prefix_transform, inverse_line_prefix


def test_every_representation_round_trips_and_charges_framing():
    data = (b"<page title=\"same title\"> a repeated record </page>\n" * 80) + b"tail"
    for mode in ("control", "space-mask", "line-prefix"):
        archive, costs = encode_archive(data, mode)
        assert decode_archive(archive) == data
        assert costs["framing_bytes"] >= 6
        assert costs["payload_bytes"] + costs["framing_bytes"] == len(archive)


def test_line_prefix_preserves_empty_and_trailing_records():
    data = b"alpha\nalpha beta\n\nalpha beta\n"
    assert inverse_line_prefix(line_prefix_transform(data)) == data


def test_archive_only_fresh_decoder(tmp_path):
    data = b"alpha beta gamma\n" * 100
    archive, _ = encode_archive(data, "space-mask")
    archive_path = tmp_path / "input.htb"
    restored = tmp_path / "restored"
    archive_path.write_bytes(archive)
    result = subprocess.run([sys.executable, "-m", "benchmarks.hutter_track_b", "decode", "--archive", str(archive_path), "--output", str(restored)], check=False)
    assert result.returncode == 0
    assert restored.read_bytes() == data
