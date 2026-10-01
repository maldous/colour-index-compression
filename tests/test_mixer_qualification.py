import hashlib
import json
import unittest

from benchmarks.cix_mixer_qualification import (
    EXECUTION_ORDER,
    implementation_revision,
    load_control_binding,
    validate_archive_consensus,
)


def digest(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


def write_receipt(path, revision="2b26cc074", *, encoder=None, decoder=None):
    encoder = encoder or digest("control-cix")
    decoder = decoder or digest("control-uncix")
    path.write_text(json.dumps({
        "status": "VERIFIED_SCREENING",
        "verification": {"matched": True},
        "identity": {
            "configuration": {
                "candidate_revision": revision,
                "encoder_sha256": encoder,
                "decoder_sha256": decoder,
            },
            "build_sha256": {
                "rust/cix-native/Cargo.toml": digest("cargo"),
                "rust/cix-native/src/lib.rs": digest("lib"),
                "snapshots/old/cix": encoder,
                "snapshots/old/uncix": decoder,
            },
        },
    }))
    return encoder, decoder


class MixerQualificationTests(unittest.TestCase):
    def test_control_receipt_binds_revision_binaries_and_prior_source_identity(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            encoder, decoder = write_receipt(receipt)
            binding = load_control_binding(receipt, "2b26cc074", encoder, decoder)
        self.assertEqual(binding["implementation_revision"], "2b26cc074")
        self.assertEqual(binding["encoder_sha256"], encoder)
        self.assertEqual(binding["prior_build_source_sha256"]["rust/cix-native/src/lib.rs"], digest("lib"))

    def test_control_receipt_rejects_mismatched_revision_or_binary_hash(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as directory:
            receipt = Path(directory) / "receipt.json"
            encoder, decoder = write_receipt(receipt)
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                load_control_binding(receipt, "087bad", encoder, decoder)
            with self.assertRaisesRegex(RuntimeError, "binary hash"):
                load_control_binding(receipt, "2b26cc074", digest("wrong"), decoder)

    def test_abba_order_and_per_cell_revisions_are_explicit(self):
        self.assertEqual(EXECUTION_ORDER, (("control", 1), ("candidate", 1), ("candidate", 2), ("control", 2)))
        self.assertEqual(implementation_revision("control", "old2b", "new087"), "old2b")
        self.assertEqual(implementation_revision("candidate", "old2b", "new087"), "new087")

    def test_archive_consensus_requires_valid_equal_complete_sizes(self):
        hash_value = digest("archive")
        valid = [{"archive_sha256": hash_value, "archive_bytes": 123}] * 4
        validate_archive_consensus(valid)
        with self.assertRaisesRegex(RuntimeError, "nonnegative"):
            validate_archive_consensus([{"archive_sha256": hash_value, "archive_bytes": -1}] * 4)
        with self.assertRaisesRegex(RuntimeError, "nonnegative"):
            validate_archive_consensus([{"archive_sha256": hash_value, "archive_bytes": True}] * 4)
        with self.assertRaisesRegex(RuntimeError, "complete archives differ"):
            validate_archive_consensus([
                {"archive_sha256": hash_value, "archive_bytes": 123},
                {"archive_sha256": hash_value, "archive_bytes": 123},
                {"archive_sha256": hash_value, "archive_bytes": 124},
                {"archive_sha256": hash_value, "archive_bytes": 123},
            ])
