import hashlib
import subprocess
import sys
from pathlib import Path

from benchmarks import hutter_track_a as track


def test_both_physical_coders_round_trip_and_charge_identical_counts():
    source = b"aaaabaaaaccccccaaaaab" * 13
    frames = {}
    stats = {}
    for method in ("rank", "range"):
        frames[method], stats[method] = track.encode(source, method)
        assert track.decode(frames[method]) == source
        assert stats[method]["count_metadata_bytes"] == stats["rank"]["count_metadata_bytes"]
        assert stats[method]["exception_bytes"] == stats["rank"]["exception_bytes"]
    assert frames["rank"] != frames["range"]


def test_independent_cli_decoder(tmp_path):
    source = bytes(range(255, -1, -1)) * 3
    frame, _ = track.encode(source, "range")
    packed = tmp_path / "sample.cix-ta"
    restored = tmp_path / "restored.bin"
    packed.write_bytes(frame)
    subprocess.run([sys.executable, str(Path(track.__file__)), "--decode", str(packed), "--output", str(restored)], check=True)
    assert hashlib.sha256(restored.read_bytes()).digest() == hashlib.sha256(source).digest()
