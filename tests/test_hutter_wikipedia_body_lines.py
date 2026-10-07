import hashlib

import pytest

from benchmarks import hutter_wikipedia_body_lines as lines


def _page(title: bytes, body: bytes, contributor: bytes = b"Ada") -> bytes:
    return (b"<page><title>" + title + b"</title><revision><contributor><username>" + contributor
            + b"</username><id>17</id></contributor><text xml:space=\"preserve\">" + body
            + b"</text></revision></page>")


def test_global_variable_line_family_round_trips_from_frame_only():
    prefix = b"This is a sufficiently long repeated line whose article "
    data = b"header\x00" + b"".join([
        _page(b"One", prefix + b"has [[Alpha]] at https://one.example/a and number 101.\n"),
        _page(b"Two", prefix + b"has [[Beta]] at https://two.example/b and number 202.\n"),
        _page(b"Three", prefix + b"has [[Gamma]] at https://three.example/c and number 303.\n"),
    ]) + b"tail\x00"
    frame, costs = lines.encode(data)
    restored = lines.decode(bytes(frame))
    assert hashlib.sha256(restored).digest() == hashlib.sha256(data).digest()
    assert costs["selected_family_count"] == 1
    assert costs["selected_member_count"] == 3
    assert costs["selected_source_bytes"] > 0
    assert sum(costs[key] for key in ("rules_bytes", "dictionary_bytes", "descriptor_bytes", "framing_bytes")) == len(frame)


def test_policy_keeps_short_exact_and_incomplete_bodies_literal():
    line = b"This is a sufficiently long line but it has no variable holes at all whatsoever.\n"
    data = _page(b"One", line) + _page(b"Two", line) + b"<text>unterminated [[x]] 123"
    frame, costs = lines.encode(data)
    assert costs["selected_family_count"] == 0
    assert lines.decode(frame) == data


def test_corruption_and_unknown_rule_are_rejected():
    data = b"".join(_page(str(index).encode(), b"This is a sufficiently long line with [[X]] and number %d for the test.\n" % index)
                    for index in range(3))
    frame, _ = lines.encode(data)
    with pytest.raises(ValueError):
        lines.decode(b"bad" + frame)
    # The declared rule stream is part of the physical frame; altering it is
    # not silently accepted by a decoder compiled for this experiment.
    broken = bytearray(frame)
    at = len(lines.MAGIC)
    _size, at = lines.vdecode(broken, at)
    rule_size, at = lines.vdecode(broken, at)
    broken[at:at + rule_size] = b"x" * rule_size
    with pytest.raises(ValueError):
        lines.decode(bytes(broken))
