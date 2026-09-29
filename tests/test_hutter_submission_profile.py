import json

from benchmarks.hutter_submission_profile import build_draft


def test_draft_bundle_is_hash_inventoried_and_marked_ineligible(tmp_path):
    source = tmp_path / "source"
    (source / "cix").mkdir(parents=True)
    (source / "benchmarks").mkdir()
    (source / "cix" / "__init__.py").write_text("")
    (source / "cix" / "cli.py").write_text("")
    (source / "benchmarks" / "hutter_cix.py").write_text("")
    report = build_draft(source, tmp_path / "draft.zip")
    assert report["submission_status"].startswith("DRAFT_NOT_ELIGIBLE")
    assert report["bundle"]["bytes"] > 0
    assert {entry["path"] for entry in report["bundle"]["files"]} == {
        "cix/__init__.py", "cix/cli.py", "benchmarks/hutter_cix.py"}
