"""Focused pure-function checks for final-Sonar admission math."""
import importlib.util
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("native_sonar", Path(__file__).with_name("run.py"))
native_sonar = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native_sonar)


class FakeCxx:
    RETAINED_NATIVE_WORK = Path("/retained")
    PROBE_SERVER_DATA_BYTES = 20
    PROBE_SERVER_LOG_BYTES = 3
    PROBE_SERVER_TEMP_BYTES = 7
    PROBE_SERVER_EXTENSIONS_BYTES = 5
    PROBE_SERVER_TMP_BYTES = 9
    PROBE_SCANNER_TEMP_BYTES = 11
    PROBE_EVIDENCE_RESERVE_BYTES = 13
    IMAGE_CORE_EXTENSION_INVENTORY = (
        ("sonar-rust-plugin-1.8.1.3395.jar", 17, "rust"),
        ("sonar-python-plugin-5.31.0.36502.jar", 19, "python"),
    )

    @staticmethod
    def allocated_bytes(path):
        assert path == FakeCxx.RETAINED_NATIVE_WORK
        return 31


class AdmissionTests(unittest.TestCase):
    def test_inventory_selects_only_required_language_plugins(self):
        self.assertEqual(native_sonar.expected_plugins(FakeCxx()), [
            {"jar": "sonar-rust-plugin-1.8.1.3395.jar", "bytes": 17},
            {"jar": "sonar-python-plugin-5.31.0.36502.jar", "bytes": 19},
        ])

    def test_accounting_includes_retained_tmpfs_plugins_and_evidence(self):
        old = native_sonar.TEMP_BUDGET
        native_sonar.TEMP_BUDGET = 200
        try:
            receipt = native_sonar.temporary_accounting(FakeCxx(), native_sonar.expected_plugins(FakeCxx()))
        finally:
            native_sonar.TEMP_BUDGET = old
        self.assertEqual(receipt["aggregate_bytes"], 31 + 20 + 3 + 7 + 5 + 9 + 11 + 17 + 19 + 13)

    def test_accounting_refuses_over_budget_before_staging(self):
        old = native_sonar.TEMP_BUDGET
        native_sonar.TEMP_BUDGET = 1
        try:
            with self.assertRaises(RuntimeError):
                native_sonar.temporary_accounting(FakeCxx(), native_sonar.expected_plugins(FakeCxx()))
        finally:
            native_sonar.TEMP_BUDGET = old


if __name__ == "__main__":
    unittest.main()
