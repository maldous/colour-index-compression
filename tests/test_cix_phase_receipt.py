import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks import cix_rust_perf_audit as audit


class ChildStatusTests(unittest.TestCase):
    def test_child_status_and_resource_failure(self):
        for child, outer, reason, expected in [
            (0, 0, None, 0), (2, 0, None, 2), (-15, 143, None, -15),
            (0, 1, "wall_budget_exhausted", 1),
            (2, 1, "memory_budget_exhausted", 1),
        ]:
            with self.subTest(child=child, reason=reason), tempfile.TemporaryDirectory() as tmp:
                def phase(**kwargs):
                    Path(kwargs["command"][2]).write_text(json.dumps({
                        "command": ["true"], "child_exit_code": child}))
                    return {"exit_code": outer, "stop_reason": reason}
                with patch.object(audit, "supervised_phase", phase):
                    result = audit.execute_phase(unit="case", command=["true"], destination=Path(tmp))
                self.assertEqual(result["exit_code"], expected)
                self.assertEqual(result["child_status"]["child_exit_code"], child)

    def test_missing_or_mismatched_receipt(self):
        for value in [None, {"command": ["wrong"], "child_exit_code": 0},
                      {"command": ["true"], "child_exit_code": False}]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                def phase(**kwargs):
                    if value is not None:
                        Path(kwargs["command"][2]).write_text(json.dumps(value))
                    return {"exit_code": 0, "stop_reason": None}
                with patch.object(audit, "supervised_phase", phase):
                    result = audit.execute_phase(unit="case", command=["true"], destination=Path(tmp))
                self.assertFalse(audit.phase_ok(result))

    def test_stale_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)
            (destination / "case.child-status.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "stale"):
                audit.execute_phase(unit="case", command=["true"], destination=destination)

    def test_old_binding_requires_new_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp)
            binding = destination / "manifest-binding.json"
            binding.write_text(json.dumps({"implementation": {}}))
            with self.assertRaisesRegex(RuntimeError, "child-status supervisor"):
                audit.validate_binding(destination, audit.sha256(binding))


if __name__ == "__main__":
    unittest.main()
