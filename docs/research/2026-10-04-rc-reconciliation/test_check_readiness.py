"""Synthetic gate mechanics only: no codec, benchmark, process or source edits."""
import copy
import json
from pathlib import Path
import unittest

from check_readiness import evaluate

LEDGER = Path(__file__).with_name("requirements.json")


def synthetic_ready():
    document = json.loads(LEDGER.read_text())
    identity = "synthetic-rc"
    receipt = {"rc_identity": identity, "path": "synthetic-only", "sha256": "a" * 64}
    for row in document["requirements"] + document["external_obligations"]:
        row["status"] = "accepted"
        row["current_rc_evidence"] = [copy.deepcopy(receipt)]
    document["readiness"] = {
        "rc_identity": identity,
        "freeze_manifest": copy.deepcopy(receipt),
        "benchmark_plan": copy.deepcopy(receipt),
        "independent_review": copy.deepcopy(receipt),
        "transition_accepted": True,
    }
    document["benchmark_gate"] = "READY"
    return document


class ReadinessTests(unittest.TestCase):
    def test_missing_evidence_blocks(self):
        document = synthetic_ready()
        document["requirements"][0]["current_rc_evidence"] = []
        self.assertFalse(evaluate(document)["benchmark_ready"])

    def test_pending_benchmark_does_not_block_its_own_start(self):
        document = synthetic_ready()
        row = next(r for r in document["requirements"] if r["id"] == "RC52")
        row["status"] = "not_started"
        row["current_rc_evidence"] = []
        self.assertTrue(evaluate(document)["benchmark_ready"])

    def test_external_owned_work_cannot_be_skipped(self):
        for identifier in document_external_ids():
            document = synthetic_ready()
            row = next(r for r in document["external_obligations"] if r["id"] == identifier)
            row["status"] = "open"
            self.assertFalse(evaluate(document)["source_prerequisites_ready"], identifier)

    def test_readiness_review_follows_source_work(self):
        document = synthetic_ready()
        row = next(r for r in document["requirements"] if r["id"] == "RC51")
        row["current_rc_evidence"] = []
        result = evaluate(document)
        self.assertTrue(result["source_prerequisites_ready"])
        self.assertFalse(result["benchmark_ready"])

    def test_prior_source_evidence_is_not_current_evidence(self):
        document = synthetic_ready()
        document["requirements"][0]["current_rc_evidence"][0]["rc_identity"] = "old-rc"
        self.assertFalse(evaluate(document)["benchmark_ready"])

    def test_stock_claim_requires_external_outcome(self):
        document = synthetic_ready()
        document["support_claims"]["stock_format_extensions"] = True
        row = next(r for r in document["external_obligations"] if r["id"] == "RC42-upstream")
        row["status"] = "external_pending"
        self.assertFalse(evaluate(document)["benchmark_ready"])

    def test_prerequisite_deletion_is_not_a_waiver(self):
        document = synthetic_ready()
        document["pre_benchmark_prerequisites"].remove("RC55")
        self.assertFalse(evaluate(document)["benchmark_ready"])

    def test_hold_blocks_even_synthetic_complete_evidence(self):
        document = synthetic_ready()
        document["benchmark_gate"] = "HOLD"
        self.assertFalse(evaluate(document)["benchmark_ready"])


def document_external_ids():
    return ["RC42-owned", "RC54-sdk-runners", "RC54-identities"]


if __name__ == "__main__":
    unittest.main()
