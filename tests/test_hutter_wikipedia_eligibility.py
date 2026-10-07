from benchmarks.hutter_wikipedia_eligibility import _body_profile, _column_profile, profile


def _body(value: bytes) -> bytes:
    return b"<page><revision><text xml:space=\"preserve\">" + value + b"</text></revision></page>"


def test_body_audit_separates_policy_and_family_exclusions():
    prefix = b"This bounded literal body line has enough stable prose for a family and "
    data = b"".join(_body(prefix + b"[[Town-%d]] recorded number %d.\n" % (index, index)) for index in range(3))
    data += _body(b"short\n" + b"x" * 600 + b" [[x]] 12\n" + b"unterminated [[x]] 12")
    audit = _body_profile(data, 512)
    assert audit["complete_body_count"] == 4
    assert audit["selected_family_count"] == 1
    assert audit["selected_source_bytes"] > 0
    assert audit["line_policy_exclusions"]["line_lt48"] == 1
    assert audit["line_policy_exclusions"]["line_gt_limit"] == 1
    assert audit["line_policy_exclusions"]["unterminated_lines"] == 1


def test_long_line_equivalent_scope_and_column_article_guard():
    long = b"This line remains literal for the 512 frame but has sufficient stable prose " + b"x" * 550 + b" [[Town-X]] 123.\n"
    data = _body(long)
    narrow, wide = _body_profile(data, 512), _body_profile(data, 4096)
    assert narrow["line_policy_exclusions"]["line_gt_limit"] == 1
    assert wide["candidate_line_count"] == 1
    columns = _column_profile(data)
    assert columns["articletext_excluded_columns"] >= 1
    assert "paragraph structures" in profile(data)["body_codec_never_reaches"][7]
