import random

import pytest

from benchmarks import hutter_wikipedia_body_units as units


def _paragraph(index: int) -> bytes:
    # Differences are constrained to recognised LINK/NUMBER holes.  The
    # literal is deliberately over 512 bytes and contains odd non-UTF-8 data.
    return (b"The district report for [[Town-" + str(index).encode() + b"]] records population "
            + str(1000 + index).encode() + b". " + b"fixed encyclopedic literal " * 28
            + b"\xff literal end " + str(9000 + index).encode() + b"\n")


def _source() -> bytes:
    pages = []
    for index in range(4):
        pages.append(b"<page><text xml:space=\"preserve\">" + _paragraph(index) + b"</text></page>")
    return b"prefix\x80" + b"".join(pages) + b"<text>incomplete [[tail]] 77"


@pytest.mark.parametrize("mode", ("paragraph-16384", "line-4096"))
def test_long_units_round_trip_self_contained(mode):
    source = _source()
    frame, accounting = units.encode(source, mode)
    assert frame.startswith(units.MAGIC)
    assert units.decode(frame) == source
    assert accounting["selected_family_count"] == 1
    assert accounting["selected_member_count"] == 4
    assert accounting["selected_source_bytes"] > 512 * 3
    assert sum(accounting[key] for key in ("rules_bytes", "dictionary_bytes", "descriptor_bytes", "framing_bytes")) == len(frame)


def test_modes_are_real_one_factor_segmentations():
    source = _source()
    paragraph, p_cost = units.encode(source, "paragraph-16384")
    line, l_cost = units.encode(source, "line-4096")
    assert paragraph != line
    assert p_cost["mode"] == "paragraph-16384"
    assert l_cost["mode"] == "line-4096"
    assert units.decode(paragraph) == units.decode(line) == source


def test_literal_noop_and_incomplete_boundaries_remain_exact_literals():
    source = b"<text>unfinished [[link]] 42" + (b" ordinary literal " * 20) + b"\x00"
    for mode in units.MODES:
        frame, cost = units.encode(source, mode)
        assert cost["selected_member_count"] == 0
        assert units.decode(frame) == source


def test_randomized_prefix_suffix_and_weird_bytes_round_trip():
    rng = random.Random(77)
    core = _source()
    for _ in range(20):
        prefix = bytes(rng.randrange(256) for _ in range(rng.randrange(17)))
        suffix = bytes(rng.randrange(256) for _ in range(rng.randrange(17)))
        for mode in units.MODES:
            frame, _cost = units.encode(prefix + core + suffix, mode)
            assert units.decode(frame) == prefix + core + suffix


def test_decoder_rejects_wrong_magic_mode_and_declared_oversize():
    frame, _ = units.encode(_source(), "line-4096")
    with pytest.raises(ValueError):
        units.decode(b"BAD!!" + frame[5:])
    with pytest.raises(ValueError):
        units.decode(units.MAGIC + b"\xff" + frame[6:])
    too_large = units.MAGIC + bytes((1,)) + units.vencode(units.MAX_SOURCE + 1)
    with pytest.raises(ValueError):
        units.decode(too_large)


def test_source_bound_is_enforced():
    with pytest.raises(ValueError):
        units.encode(b"x" * (units.MAX_SOURCE + 1), "line-4096")
