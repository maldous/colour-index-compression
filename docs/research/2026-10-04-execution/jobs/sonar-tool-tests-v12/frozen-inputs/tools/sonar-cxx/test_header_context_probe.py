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

    def test_measured_context_records_the_per_file_analyzer_only_change(self):
        class Repair:
            digest = staticmethod(probe.sha256)

        row, _, record = probe.measured_context(Repair(), normalize_gnu_visibility=True)
        self.assertEqual(row["defines"]["__attribute__(...)"], "")
        normalization = record["analyzer_only_normalization"]
        self.assertTrue(normalization["enabled"])
        self.assertEqual(normalization["abi_or_layout_claim"], "none")
        self.assertEqual(normalization["source_header_sha256"], record["header_sha256"])


if __name__ == "__main__":
    unittest.main()
