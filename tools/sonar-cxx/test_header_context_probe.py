"""Pure checks for the opt-in JXL header-context normalization path."""
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "header_context_probe", Path(__file__).with_name("header_context_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class HeaderContextProbeTests(unittest.TestCase):
    def test_visibility_normalization_is_the_exact_linux_header_spelling(self):
        header = '#  define CIX_JXL_API __attribute__((visibility("default")))\n'
        normalized = probe.gnu_visibility_normalization(
            header, {"__cplusplus": "201703L", "__linux__": "1"})
        self.assertEqual(normalized["__attribute__(...)"], "")
        self.assertEqual(normalized["__cplusplus"], "201703L")

    def test_visibility_normalization_rejects_windows_or_another_attribute_shape(self):
        header = '#  define CIX_JXL_API __attribute__((visibility("default")))\n'
        with self.assertRaises(RuntimeError):
            probe.gnu_visibility_normalization(header, {"_WIN32": "1", "__linux__": "1"})
        with self.assertRaises(RuntimeError):
            probe.gnu_visibility_normalization('__attribute__((unused))\n', {"__linux__": "1"})

    def test_worker_flag_is_explicit_and_opt_in(self):
        out = Path("/tmp/cix-header-probe")
        self.assertNotIn("--normalize-gnu-visibility", probe.worker_arguments(out, False))
        self.assertIn("--normalize-gnu-visibility", probe.worker_arguments(out, True))

    def test_bridge_context_flag_is_explicit_and_does_not_change_default_arguments(self):
        out = Path("/tmp/cix-header-probe")
        capture = Path("/tmp/cix-bridge-context")
        self.assertNotIn("--bridge-context-directory", probe.worker_arguments(out, False))
        arguments = probe.worker_arguments(out, False, capture)
        self.assertEqual(arguments[-2:], ["--bridge-context-directory", str(capture)])

    def test_result_metadata_distinguishes_requested_and_effective_bridge_normalization(self):
        bridge_record = {"entries": [
            {"header": "first.h"}, {"header": "second.h"},
        ]}
        metadata = probe.normalization_metadata(False, bridge_record)
        self.assertFalse(metadata["requested_single_header_gnu_visibility"])
        self.assertEqual(metadata["effective_mode"], "captured_per_file_gnu_visibility")
        self.assertEqual(metadata["headers"], ["first.h", "second.h"])
        self.assertEqual(probe.normalization_metadata(False)["effective_mode"], "none")

    def test_measured_context_records_the_per_file_analyzer_only_change(self):
        class Repair:
            digest = staticmethod(probe.sha256)

        row, _, record = probe.measured_context(Repair(), normalize_gnu_visibility=True)
        self.assertEqual(row["defines"]["__attribute__(...)"], "")
        normalization = record["analyzer_only_normalization"]
        self.assertTrue(normalization["enabled"])
        self.assertEqual(normalization["abi_or_layout_claim"], "none")
        self.assertEqual(normalization["source_header_sha256"], record["header_sha256"])

    def test_completed_bridge_capture_fixture_has_six_exact_per_file_contexts(self):
        class Repair:
            digest = staticmethod(probe.sha256)

        rows, mounts, record = probe.measured_bridge_contexts(Repair(), probe.BRIDGE_CAPTURE)
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({row["file"] for row in rows}), 6)
        self.assertEqual(len(mounts), len({container for _, container in mounts}))
        self.assertEqual(sum(record["previous_recovery_counts"].values()), 39)
        self.assertEqual(len(record["capture_context_sha256"]), 64)
        self.assertEqual(len(record["capture_receipt_sha256"]), 64)
        for row in rows:
            self.assertEqual(row["defines"]["__attribute__(...)"], "")
            self.assertEqual(row["directory"], "/usr/src")
            self.assertTrue(row["includes"])


if __name__ == "__main__":
    unittest.main()
