"""Focused preflight tests for the non-mutating native source allowlist validator.

Do not run this directly as release evidence. The coordinator schedules it with
an authenticated source identity and stores its receipt.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
VALIDATOR = ROOT / "rust/cix-native/packaging/export/validate_source_allowlist.py"
MANIFEST = ROOT / "rust/cix-native/packaging/export/source-allowlist.json"


def load_validator():
    specification = importlib.util.spec_from_file_location("cix_export_allowlist", VALIDATOR)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def fixture_tree(temporary: str, manifest: dict) -> Path:
    root = Path(temporary) / "rust/cix-native"
    root.mkdir(parents=True)
    for relative in manifest["required_exact_files"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    return root


class SourceAllowlistTests(unittest.TestCase):
    def test_current_native_tree_has_selected_conformance_members(self) -> None:
        validator = load_validator()
        report = validator.validate(ROOT / "rust/cix-native", validator.read_manifest(MANIFEST))
        self.assertEqual(report["status"], "validated_source_members_only_not_exported")
        self.assertEqual(report["dependency_closure_status"], "not_checked_source_members_only")
        self.assertIn("examples/native_buffer.rs", report["selected_members"])
        self.assertIn("tests/c_api_consumer.c", report["selected_members"])
        self.assertIn("tests/fixtures/native_ports/pointer.input", report["selected_members"])

    def test_unallowlisted_file_is_rejected(self) -> None:
        validator = load_validator()
        manifest = json.loads(MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = fixture_tree(temporary, manifest)
            (root / "unlisted.txt").write_text("must not ship")
            with self.assertRaisesRegex(ValueError, "unallowlisted"):
                validator.validate(root, manifest)

    def test_research_like_prefix_is_not_selected(self) -> None:
        validator = load_validator()
        manifest = json.loads(MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = fixture_tree(temporary, manifest)
            blocked = root / "experiments/retained-but-not-shipping.rs"
            blocked.parent.mkdir(parents=True)
            blocked.write_text("no export")
            report = validator.validate(root, manifest)
            self.assertNotIn("experiments/retained-but-not-shipping.rs", report["selected_members"])

    def test_full_engine_profile_requires_accepted_dependency_closure(self) -> None:
        validator = load_validator()
        manifest = validator.read_manifest(MANIFEST)
        with self.assertRaisesRegex(ValueError, "full-engine RC source export blocked"):
            validator.validate(ROOT / "rust/cix-native", manifest, validator.FULL_ENGINE_PROFILE)


if __name__ == "__main__":
    unittest.main()
