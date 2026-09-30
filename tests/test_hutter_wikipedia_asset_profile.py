from pathlib import Path

from benchmarks.hutter_wikipedia_asset_profile import WINDOW, normalise_line, profile_asset


def test_normalization_and_profile_reserve(tmp_path: Path):
    assert normalise_line(b"[[A]] 123") == b"<L> <N>"
    source = tmp_path / "tiny.bin"
    line = b"<page><title>T</title><text>{{Infobox|n=1}} [[A]] 123 repeated body text long enough to census\n</text></page>\n"
    source.write_bytes(line * 3)
    result = profile_asset(source, wall_seconds=5)
    assert result["canonical_hashes"]["sha256"]
    assert result["windows"][0]["status"] == "PROFILED"
    assert result["windows"][0]["infobox_openings"] == 3
    assert result["windows"][0]["body_line_census"]["repeated_occurrences"] >= 2
    assert result["structural_window_recommendations"]["eligibility_not_gain"]


def test_profile_marks_reserved_windows_without_statistics(tmp_path: Path, monkeypatch):
    import benchmarks.hutter_wikipedia_asset_profile as module
    monkeypatch.setattr(module, "WINDOW", 4)
    monkeypatch.setattr(module, "RESERVED", ((4, 8),))
    source = tmp_path / "tiny.bin"; source.write_bytes(b"aaaabbbbcccc")
    result = module.profile_asset(source, wall_seconds=5)
    assert result["windows"][1]["status"] == "RESERVED_HASHED_ONLY"
    assert "infobox_openings" not in result["windows"][1]


def test_reservation_is_any_intersection_not_only_window_start(monkeypatch):
    import benchmarks.hutter_wikipedia_asset_profile as module
    monkeypatch.setattr(module, "RESERVED", ((10, 20),))
    assert module.reserved(8, 4)
    assert module.reserved(19, 4)
    assert not module.reserved(0, 10)


def test_redirect_after_xml_text_and_us_census_rule_not_town_table(tmp_path: Path):
    source = tmp_path / "patterns.bin"
    source.write_bytes(b"<page><text xml:space=\"preserve\">#REDIRECT [[Target]]\n"
                       b"Town population 123\n"
                       b"Population 123; households 45; families 30\n</text></page>")
    result = profile_asset(source, wall_seconds=5)
    row = result["windows"][0]
    assert row["redirect_title_directives"] == 1
    assert row["us_census_pattern_lines"]["count"] == 1
