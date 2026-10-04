"""Lightweight fail-closed coverage and benchmark-isolation checks; no scans."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("repair", Path(__file__).with_name("repair.py"))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairAcceptanceTests(unittest.TestCase):
    def test_analyzer_must_execute_and_index_vendor_as_cpp(self):
        files = ["native/src/zpaq_ffi.cpp", "native/vendor/libzpaq715/libzpaq.cpp"]
        components = [{"path": path, "language": "cxx"} for path in files]
        self.assertEqual(repair.validate_indexed(files, components, "Sensor CXX [cxx]"), set(files))
        for rows, log in ((components[:1], "Sensor CXX [cxx]"), (components, "scanner succeeded"),
                          ([{**row, "language": "text"} for row in components], "Sensor CXX [cxx]")):
            with self.assertRaises(RuntimeError):
                repair.validate_indexed(files, rows, log)

    def test_partial_or_different_benchmark_cannot_start_server(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cells = [{"id": f"{mode}-{index}", "profile": mode, "source": {"sha256": str(index)}}
                     for mode in ("fast", "default", "best") for index in range(12)]
            repair.save(root / "plan.json", {"cells": cells})
            rows = [{"cell": row["id"], "profile": row["profile"], "source": row["source"], "status": "VERIFIED"} for row in cells]
            summary = {"plan_sha256": repair.digest(root / "plan.json"), "rows": rows}
            repair.save(root / "summary.json", summary)
            repair.require_confirmation(root / "summary.json")
            for malformed in (rows[:2], rows[:-1] + rows[:1],
                              [{**row, "status": "STARTED"} for row in rows],
                              [{**row, "source": {"sha256": "wrong"}} for row in rows]):
                repair.save(root / "summary.json", {**summary, "rows": malformed})
                with self.assertRaises(RuntimeError):
                    repair.require_confirmation(root / "summary.json")

    def test_inventory_covers_every_declared_vendor_tree_and_detects_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for prefixes in repair.SCOPES.values():
                for prefix in prefixes:
                    target = root / prefix
                    target.mkdir(parents=True)
                    (target / "sample.cpp").write_text("int x;\n")
            before = repair.inventory(root)
            self.assertEqual(set(before), set(repair.SCOPES))
            (root / "vendor/paq/v215/sample.cpp").write_text("int changed;\n")
            self.assertNotEqual(before, repair.inventory(root))


if __name__ == "__main__":
    unittest.main()
