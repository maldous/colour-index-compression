import json
import os
import subprocess
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
        for value in [None, [], {"command": ["wrong"], "child_exit_code": 0},
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




class CgroupReadbackTests(unittest.TestCase):
    def test_wrapper_reads_unified_cgroup_third_colon_field(self):
        script = audit.affinity_wrapped(["true"], Path("affinity"), Path("cgroup"))[2]
        expression = script.split("cg=$(", 1)[1].split(");", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cgroup"
            source.write_text("0::/system.slice/cix-test.scope\n")
            expression = expression.replace("/proc/self/cgroup", '"$CIX_TEST_CGROUP_SOURCE"')
            result = subprocess.run(["/bin/bash", "-c", expression],
                                    env={**os.environ, "CIX_TEST_CGROUP_SOURCE": str(source)},
                                    text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "/system.slice/cix-test.scope")

    def test_wrapper_reads_unified_record_among_other_controllers(self):
        script = audit.affinity_wrapped(["true"], Path("affinity"), Path("cgroup"))[2]
        expression = script.split("cg=$(", 1)[1].split(");", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cgroup"
            source.write_text("3:cpu:/legacy\n0::/user.slice/native.scope\n")
            expression = expression.replace("/proc/self/cgroup", '"$CIX_TEST_CGROUP_SOURCE"')
            result = subprocess.run(["/bin/bash", "-c", expression],
                                    env={**os.environ, "CIX_TEST_CGROUP_SOURCE": str(source)},
                                    text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), "/user.slice/native.scope")


class ReleaseIdentityTests(unittest.TestCase):
    def test_legacy_and_nested_release_schema(self):
        revision = "a" * 40
        for value in [{"source_revision": revision}, {"source": {"revision": revision}},
                      {"source_revision": revision, "source": {"revision": revision}}]:
            self.assertEqual(audit.release_revision(value), revision)

    def test_missing_invalid_and_conflicting_identity_rejected(self):
        for value in [{}, {"source_revision": "short"}, {"source_revision": "z" * 40},
                      {"source": {"revision": 123}},
                      {"source_revision": "a" * 40, "source": {"revision": "b" * 40}}]:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                audit.release_revision(value)


if __name__ == "__main__":
    unittest.main()
