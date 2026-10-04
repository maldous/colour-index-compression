"""Lightweight fail-closed coverage and benchmark-isolation checks; no scans."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("repair", Path(__file__).with_name("repair.py"))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairAcceptanceTests(unittest.TestCase):
    def _stopped_fixture(self, root: Path):
        ids = list(repair.STOP_VERIFIED) + [repair.STOP_INTERRUPTED] + [f"unstarted-{n}" for n in range(30)]
        plan = root / "plan.json"; stop = root / "stop.json"; summary = root / "summary.json"
        repair.save(plan, {"cells": [{"id": cell} for cell in ids]})
        receipt = {"status": "STOPPED_BY_USER", "plan_sha256": repair.digest(plan),
                   "automatic_restart_allowed": False, "verified_cells": sorted(repair.STOP_VERIFIED),
                   "interrupted_cells": [{"cell": repair.STOP_INTERRUPTED, "phase": "encode",
                                           "status": "INTERRUPTED_UNQUALIFIED", "decode_started": False}],
                   "not_started_cells": [f"unstarted-{n}" for n in range(30)]}
        repair.save(stop, receipt)
        repair.save(summary, {"plan_sha256": repair.digest(plan), "stop_receipt": "stop.json",
                              "rows": [{"cell": cell, "status": "VERIFIED"} for cell in repair.STOP_VERIFIED]})
        return plan, stop, summary

    def test_exact_committed_stop_authorizes_only_expected_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); plan, stop, summary = self._stopped_fixture(root)
            with patch.object(repair, "STOP_PLAN_SHA256", repair.digest(plan)), patch.object(repair, "STOP_SHA256", repair.digest(stop)):
                repair.require_stopped_confirmation(summary, stop, committed_reader=lambda _: stop.read_bytes(), root=root)
                stop.write_text(stop.read_text().replace("STOPPED_BY_USER", "STARTED"))
                with self.assertRaises(RuntimeError):
                    repair.require_stopped_confirmation(summary, stop, committed_reader=lambda _: b"different", root=root)

    def test_stop_rejects_wrong_counts_and_summary_or_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); plan, stop, summary = self._stopped_fixture(root)
            with patch.object(repair, "STOP_PLAN_SHA256", repair.digest(plan)), patch.object(repair, "STOP_SHA256", repair.digest(stop)):
                value = json.loads(stop.read_text()); value["not_started_cells"] = value["not_started_cells"][:-1]; repair.save(stop, value)
                with patch.object(repair, "STOP_SHA256", repair.digest(stop)):
                    with self.assertRaises(RuntimeError):
                        repair.require_stopped_confirmation(summary, stop, committed_reader=lambda _: stop.read_bytes(), root=root)
            plan.write_text('{"cells": []}')
            with self.assertRaises(RuntimeError):
                repair.require_stopped_confirmation(summary, stop, committed_reader=lambda _: stop.read_bytes(), root=root)

    def test_idle_guard_rejects_process_unit_and_cgroup_without_host_access(self):
        class Result:
            def __init__(self, text): self.stdout = text
        def safe(command, **_): return Result("inactive\n" if command[0] == "systemctl" else "")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repair.assert_benchmark_idle(runner=safe, cgroup_root=root)
            def active(command, **_): return Result("123 " + str(repair.SUMMARY.parent) if command[0] == "ps" else "inactive\n")
            with self.assertRaises(RuntimeError): repair.assert_benchmark_idle(runner=active, cgroup_root=root)
            def unit(command, **_): return Result("active\n" if command[0] == "systemctl" else "")
            with self.assertRaises(RuntimeError): repair.assert_benchmark_idle(runner=unit, cgroup_root=root)
            group = root / "cix-silesia-confirmation.service"; group.mkdir(); (group / "cgroup.procs").write_text("9\n")
            with self.assertRaises(RuntimeError): repair.assert_benchmark_idle(runner=safe, cgroup_root=root)

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
