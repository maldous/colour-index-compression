import hashlib
import subprocess
import sys
from pathlib import Path

from benchmarks import hutter_track_a_feedback as feedback


def test_causal_and_paid_feedback_are_self_contained_round_trips():
    source = (b"aaaaabbbbcccccdddddddd" * 31) + bytes(range(64))
    for method in ("causal", "feedback"):
        frame, stats = feedback.encode(source, method)
        assert feedback.decode(frame) == source
        assert stats["composition_metadata_bytes"] == (0 if method == "causal" else stats["composition_metadata_bytes"])
        assert (stats["framing_bytes"] + stats["first_literal_bytes"] + stats["composition_metadata_bytes"] + stats["payload_bytes"] == stats["physical_bytes"])


def test_feedback_child_decoder(tmp_path):
    source = bytes(range(256)) * 4
    frame, _ = feedback.encode(source, "feedback")
    packed = tmp_path / "feedback.cixtf"
    restored = tmp_path / "restored.bin"
    packed.write_bytes(frame)
    subprocess.run([sys.executable, str(Path(feedback.__file__)), "--decode", str(packed), "--output", str(restored)], check=True)
    assert hashlib.sha256(restored.read_bytes()).digest() == hashlib.sha256(source).digest()
