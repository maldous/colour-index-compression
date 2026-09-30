from benchmarks.hutter_wikipedia_opportunity_profile import compact_locations, profile


def test_profile_returns_absolute_structural_locations_and_no_gain_claim():
    line = lambda value: (b"{{Infobox|name=[[Entity]]|url=https://example.org/a|value=" + str(value).encode()
                          + b"}} repeated eligible content here\n")
    data = (b"<mediawiki><page><title>Same</title><redirect title=\"Else\"/><revision><id>7</id>"
            b"<timestamp>2020-01-01</timestamp><text>" + line(17) + b"[[Category:Science]]\n{| table\n</text></revision></page>"
            b"<page><title>Same</title><revision><id>8</id><text>" + line(18) + b"</text></revision></page>"
            b"<page><title>Other</title><revision><id>9</id><text>" + line(19) + b"</text></revision></page></mediawiki>")
    result = profile(data, 1_000)
    assert result["provenance"]["absolute_offset"] == 1_000
    assert result["body_line_families"]["family_count"] >= 1
    family_range = result["body_line_families"]["families"][0]["ranges"][0]
    assert family_range["start"] >= 1_000 and family_range["end"] > family_range["start"]
    assert result["references_topology"]["categories"]["count"] == 1
    assert result["markup_locations"]["infobox"]["count"] == 3
    assert result["numeric_evidence"]["count"] >= 3
    assert "no numerical correlation" in result["numeric_evidence"]["note"]
    assert result["union_and_overlap"]["union_bytes"] <= result["union_and_overlap"]["occurrence_bytes"]


def test_profile_rejects_negative_absolute_offset():
    try:
        profile(b"<page></page>", -1)
    except ValueError as error:
        assert "nonnegative" in str(error)
    else:
        raise AssertionError("negative offsets must be rejected")


def test_compact_locations_keeps_exact_count_and_bounds_evidence():
    line = b"{{Infobox|name=[[Entity]]|url=https://example.org/a|value=17}} repeated eligible content here\n"
    data = b"".join(b"<page><text>" + line + b"</text></page>" for _ in range(3))
    compact = compact_locations(profile(data, 0), max_per_class=1)
    infobox = compact["markup_locations"]["infobox"]
    assert infobox["exact_location_count"] == 3
    assert len(infobox["representative_ranges"]) == 1
    assert compact["location_detail_policy"]["representative_locations_per_class"] == 1
