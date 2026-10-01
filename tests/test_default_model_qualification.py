from pathlib import Path
import unittest

from benchmarks import cix_default_model_qualification as qualification


class DefaultModelQualificationTests(unittest.TestCase):
    def test_abba_order_is_predeclared_per_range(self):
        control, candidate = Path("control/cix"), Path("candidate/cix")
        self.assertEqual(qualification.abba_order(control, candidate), (
            ("control", control, 1),
            ("native-candidate", candidate, 1),
            ("native-candidate", candidate, 2),
            ("control", control, 2),
        ))

    def test_control_receipt_requires_its_own_revision_and_binary_hash(self):
        revision = "a" * 40
        binary_hash = "b" * 64
        receipt = {"identity": {"configuration": {
            "implementation": "control",
            "implementation_revision": revision,
            "encoder_sha256": binary_hash,
        }}}
        qualification.validate_control_receipt(receipt, binary_hash, revision)
        receipt["identity"]["configuration"]["implementation_revision"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "implementation_revision"):
            qualification.validate_control_receipt(receipt, binary_hash, revision)
        receipt["identity"]["configuration"]["implementation_revision"] = revision
        receipt["identity"]["configuration"]["encoder_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "encoder_sha256"):
            qualification.validate_control_receipt(receipt, binary_hash, revision)

    def test_complete_archive_validation_requires_equal_nonnegative_integer_replicates(self):
        rows = [
            {"cell_id": "dev-control-r1", "range_kind": "development", "implementation": "control", "archive_bytes": 17},
            {"cell_id": "dev-control-r2", "range_kind": "development", "implementation": "control", "archive_bytes": 17},
        ]
        self.assertEqual(qualification.validate_complete_archive_replicates(rows), {"development/control": 17})
        rows[1]["archive_bytes"] = 18
        with self.assertRaisesRegex(RuntimeError, "differ"):
            qualification.validate_complete_archive_replicates(rows)
        rows[1]["archive_bytes"] = True
        with self.assertRaisesRegex(RuntimeError, "non-negative"):
            qualification.validate_complete_archive_replicates(rows)

    def test_policy_requires_ratio_and_causal_opportunity_floor(self):
        self.assertIn("greater than 0.1", qualification.POLICY)
        self.assertIn("at least 64 causal prediction opportunities", qualification.POLICY)

    def test_normalized_receipt_recovers_range_only_from_hash_checked_manifest(self):
        root = Path("/tmp/qualification-root")
        cell = {
            "cell_id": "development-control-r1",
            "manifest_path": "manifests/control.json",
            "expected_manifest_sha256": "manifest-sha",
        }
        declared = {
            "configuration": {"implementation": "control", "implementation_revision": "a" * 40},
            "input": {"range_kind": "development"},
        }

        def loader(path):
            self.assertEqual(path, (root / "manifests/control.json").resolve())
            return declared, "manifest-sha"

        self.assertEqual(
            qualification.provenance_from_normalized_identity(
                cell, {"implementation": "control"}, {}, root=root, manifest_loader=loader),
            ("control", "development", "a" * 40),
        )
        with self.assertRaisesRegex(RuntimeError, "hash changed"):
            qualification.provenance_from_normalized_identity(
                {**cell, "expected_manifest_sha256": "wrong"},
                {"implementation": "control"}, {}, root=root, manifest_loader=loader)
