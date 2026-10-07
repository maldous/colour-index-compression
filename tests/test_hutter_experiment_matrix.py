from benchmarks.hutter_experiment_matrix import OPPORTUNITY_CLASSES, define_matrix, import_result_row, opportunity_cells, rank_groups, summarize_candidate
from benchmarks.hutter_opportunity_inputs import CLASSES


def _row(candidate, input_id, delta, **extra):
    row = {"candidate_id": candidate, "input_id": input_id, "match_class": "representative", "backend": "PAQv216-4",
           "scale": "dev4MiB", "context_reset": "reset_empty", "control_id": "original", "status": "COMPLETE",
           "verified": True, "size_delta_bytes": delta}
    row.update(extra)
    return row


def test_matrix_is_bounded_and_keeps_unavailable_work_visible():
    cells = define_matrix()
    assert 25 <= len(cells) <= 40
    assert any(cell["status"] == "HOLDOUT_RESERVED" for cell in cells)
    assert any(cell["status"] == "BLOCKED_DEPENDENCY" and cell["representation"] == "typed_streams" for cell in cells)
    assert any(cell["status"] == "INAPPLICABLE" and cell["cell_id"] == "invalid-original-rank" for cell in cells)
    assert all(cell["backend"] != "PAQv216-higher" or cell["status"] == "BLOCKED_DEPENDENCY" for cell in cells)
    assert {cell["strength"] for cell in cells if cell["evidence_stratum"] == "synthetic"} == {"strong", "weak", "absent"}
    assert any(cell["status"] == "NOT_IMPLEMENTED" for cell in cells)
    holdout = next(cell for cell in cells if cell["status"] == "HOLDOUT_RESERVED")
    assert "historically read" in holdout["reason"] and "unread" not in holdout["reason"]


def test_opportunity_factorial_coverage_is_explicit_not_an_execution_queue():
    cells = opportunity_cells()
    assert len(cells) == 7 * 5 * 8 * 4
    assert OPPORTUNITY_CLASSES is CLASSES
    assert {cell["opportunity_class"] for cell in cells} == set(CLASSES)
    assert any(cell["status"] == "NOT_IMPLEMENTED" for cell in cells)
    assert any(cell["status"] == "BLOCKED_DEPENDENCY" for cell in cells)
    assert all("automatic" not in cell["reason"] for cell in cells)


def test_missing_or_unverified_or_size_rejected_rows_cannot_win():
    expected = {"representative": ["dev-a", "dev-b"]}
    rows = [
        _row("complete", "dev-a", -10), _row("complete", "dev-b", -8),
        _row("missing", "dev-a", -100),
        _row("unverified", "dev-a", -1000), _row("unverified", "dev-b", -1000, verified=False),
        _row("rejected", "dev-a", -1000), _row("rejected", "dev-b", -1000, status="SIZEREJ", verified=False),
    ]
    result = summarize_candidate(rows, expected)
    assert result[0]["candidate_id"] == "complete" and result[0]["promotable"] is True
    assert {item["candidate_id"] for item in result[1:]} == {"missing", "unverified", "rejected"}
    assert not any(item["promotable"] for item in result[1:])


def test_same_backend_scale_and_match_class_are_not_mixed():
    expected = {"representative": ["dev-a"], "targeted": ["target-a"]}
    rows = [_row("candidate", "dev-a", -5)]
    rows.append(_row("candidate", "target-a", -500, match_class="targeted"))
    rows.append(_row("candidate", "dev-a", -900, backend="PAQv216-higher"))
    ranked = rank_groups(rows, expected)
    assert len(ranked) == 3
    assert {item["comparison_group"]["match_class"] for item in ranked} == {"representative", "targeted"}
    flattened = [candidate for group in ranked for candidate in group["candidates"]]
    current = [item for item in flattened if item["backend"] == "PAQv216-4" and item["match_class"] == "representative"][0]
    assert current["promotable"] is True and current["total_verified_gain_bytes"] == 5
    alternative = [item for item in flattened if item["backend"] == "PAQv216-higher"][0]
    assert alternative["promotable"] is True and alternative["total_verified_gain_bytes"] == 900
    assert current["rank_within_comparison_group"] == alternative["rank_within_comparison_group"] == 1


def test_receipt_importer_refuses_missing_control_or_verification():
    identity = {"candidate_id": "x", "input_id": "dev-a", "match_class": "representative", "backend": "PAQv216-4",
                "scale": "dev4MiB", "context_reset": "reset_empty", "control_id": "original"}
    complete = import_result_row({"physical_bytes": 90, "control_physical_bytes": 100, "verified": True}, identity)
    missing = import_result_row({"physical_bytes": 90, "verified": True}, identity)
    assert complete["status"] == "COMPLETE" and complete["size_delta_bytes"] == -10
    assert missing["status"] == "BLOCKED_DEPENDENCY" and missing["size_delta_bytes"] is None


def test_native_screening_and_size_rejection_status_and_costs_are_preserved():
    identity = {"candidate_id": "x", "input_id": "dev-a", "match_class": "representative", "backend": "PAQv216-4",
                "scale": "dev4MiB", "context_reset": "reset_empty", "control_id": "original", "opportunity_class": "bodylines",
                "evidence_stratum": "representative_development", "strength": "mixed"}
    screening = import_result_row({"archive_bytes": 90, "control_archive_bytes": 100, "status": "VERIFIED_SCREENING", "verified": True,
                                   "compression_seconds": 2.5, "peak_rss_bytes": 123}, identity)
    rejected = import_result_row({"archive_bytes": 90, "control_archive_bytes": 100, "status": "SIZE_REJECTED_UNVERIFIED", "verified": False,
                                  "decompression_seconds": 3.5}, identity)
    assert screening["status"] == "VERIFIED_SCREENING" and screening["compression_seconds"] == 2.5
    assert rejected["status"] == "SIZE_REJECTED_UNVERIFIED" and rejected["decompression_seconds"] == 3.5
    result = summarize_candidate([screening, rejected], {"representative": ["dev-a"]})
    assert not any(item["promotable"] for item in result)


def test_native_verified_mapping_is_screening_complete_but_never_auto_promoted():
    identity = {"candidate_id": "x", "input_id": "dev-a", "match_class": "representative", "backend": "PAQv216-4",
                "scale": "dev4MiB", "context_reset": "reset_empty", "control_id": "original"}
    row = import_result_row({"archive_bytes": 90, "control_archive_bytes": 100, "status": "VERIFIED_SCREENING",
                             "verification": {"sha256_match": True}, "peak_rss_bytes": 123}, identity)
    assert row["verified"] is True and row["status"] == "VERIFIED_SCREENING" and row["peak_rss_bytes"] == 123
    summary = summarize_candidate([row], {"representative": ["dev-a"]})[0]
    assert summary["promotable"] is True and summary["automatic_stage_promotion"] is False
