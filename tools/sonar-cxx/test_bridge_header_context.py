"""Pure validation tests for the six bridge-header context preparation helpers."""
import importlib.util
from pathlib import Path
import sys
import unittest


spec = importlib.util.spec_from_file_location(
    "bridge_header_context", Path(__file__).with_name("bridge_header_context.py"))
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class BridgeHeaderContextTests(unittest.TestCase):
    def test_visibility_normalization_accepts_one_linux_default_visibility_definition(self):
        # The helper reads a path; use the known current header rather than a
        # synthetic interface so its exact spelling remains part of the test.
        header = module.ROOT / module.BRIDGES[0].header
        name, defines = module.visibility_normalization(
            header, {"__linux__": "1", "__cplusplus": "201703L"})
        self.assertEqual(name, "CIX_JXL_API")
        self.assertEqual(defines["__attribute__(...)"], "")

    def test_visibility_normalization_rejects_non_linux_context(self):
        header = module.ROOT / module.BRIDGES[0].header
        with self.assertRaises(module.BridgeContextError):
            module.visibility_normalization(header, {"_WIN32": "1", "__linux__": "1"})

    def test_bridge_inventory_is_exactly_the_six_owned_headers(self):
        self.assertEqual(len(module.BRIDGES), 6)
        self.assertEqual({bridge.name for bridge in module.BRIDGES}, {
            "jxl", "spatial", "paq-v215", "paq-v216", "paq-joint-discount", "paq-store-state"})
        for bridge in module.BRIDGES:
            header = module.ROOT / bridge.header
            self.assertTrue(header.is_file())
            name, normalized = module.visibility_normalization(
                header, {"__linux__": "1", "__cplusplus": "201703L"})
            self.assertTrue(name.startswith("CIX_") and name.endswith("_API"))
            self.assertEqual(normalized["__attribute__(...)"], "")


if __name__ == "__main__":
    unittest.main()
