import json
import tempfile
import unittest
from pathlib import Path

from benchmarks import cix_rust_scaling_audit as audit


class ScalingAuditPlanTest(unittest.TestCase):
    def test_frozen_sweep_profiles_and_real_independent_forms(self):
        self.assertEqual(audit.THREADS, (1, 2, 4, 8, 12, 16, 20, 24))
        self.assertEqual(set(audit.PROFILES), {"fast", "default", "best"})
        self.assertEqual([item["format"] for item in audit.independent_forms()], ["cixg1", "cixg2"])
        self.assertTrue(all(item["history"] == "0" for item in audit.independent_forms()))

    def test_nonzero_history_is_rejected_before_release_or_input_access(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "nonzero --history"):
                audit.plan(Path(directory) / "release", [Path(directory) / "input"],
                           Path(directory) / "plan.json", "64KiB", "1MiB", "512MiB", 1)

    def test_execute_rejects_missing_cleanup_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "cleanup gate"):
                audit.execute_frozen(Path(directory) / "plan.json", Path(directory) / "gate")

    def test_gate_binds_exact_plan_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            plan, gate = Path(directory) / "plan.json", Path(directory) / "gate.json"
            plan.write_text("{}\n")
            gate.write_text(json.dumps({"schema": "cix-rust-scaling-execution-gate-v1",
                                        "authorize_dispatch": True,
                                        "plan_sha256": audit.digest(plan)}))
            self.assertTrue(audit.load_gate(plan, gate)["authorize_dispatch"])
            plan.write_text("{ }\n")
            with self.assertRaisesRegex(RuntimeError, "does not bind"):
                audit.load_gate(plan, gate)

    def test_decode_command_is_single_thread_for_twenty_thread_encode(self):
        cell = {"input": {"path": "/input", "bytes": 1, "sha256": "x"},
                "encode_flags": ["--threads", "20"], "decode_flags": ["--threads", "1"]}
        release = {"binaries": {"cix": {"path": "/cix"}, "uncix": {"path": "/uncix"}}}
        command, _, _ = audit.cell_command(cell, release, Path("/tmp/cix-scaling-unit"), True)
        self.assertIn("/uncix", command)
        self.assertEqual(command[command.index("/uncix"):command.index("/uncix") + 3], ["/uncix", "--threads", "1"])
        self.assertNotIn("20", command)

    def test_unproven_persistent_container_is_not_a_dispatch_form(self):
        self.assertNotIn("cixm6", [item["format"] for item in audit.independent_forms()])

    def test_logical_selection_uses_siblings_only_after_physical_cores(self):
        topology = {"visible": [{"cpu": 8, "package": "0", "core": "0", "capacity": "1"}, {"cpu": 9, "package": "0", "core": "1", "capacity": "1"}, {"cpu": 10, "package": "0", "core": "0", "capacity": "1"}], "physical_count": 2, "logical_count": 3, "mixed_capacity": False}
        self.assertEqual(audit.select_cpus(3, topology), [8, 9, 10])

    def test_cell_uses_existing_phase_runner_and_qualifies_fresh_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "input"; source.write_bytes(b"scale")
            cell = {"cell_id": "unit", "input": {"path": str(source), "bytes": 5,
                    "sha256": audit.digest(source)}, "encode_flags": ["--threads", "2"],
                    "decode_flags": ["--threads", "1"]}
            release = {"binaries": {"cix": {"path": "/cix"}, "uncix": {"path": "/uncix"}}}
            def phase_runner(**kwargs):
                command = kwargs["command"]
                Path(command[4]).write_text("pid 1's current affinity list: 10,11\n")
                Path(command[5]).write_text("cpuset=10,11\nmemory.max=12000000000\nmemory.swap.max=0\n")
                native = command[6:]
                Path(native[native.index("-o") + 1]).write_text("User time (seconds): 0.01\nSystem time (seconds): 0.00\nElapsed (wall clock) time (h:mm:ss or m:ss): 0:00.01\nMaximum resident set size (kbytes): 1\n")
                output = Path(native[native.index("-o", native.index("-o") + 1) + 1])
                if kwargs["unit"].endswith("encode"):
                    output.write_bytes(b"archive")
                else:
                    output.write_bytes(source.read_bytes())
                return {"exit_code": 0, "stop_reason": None, "child_status": {"child_exit_code": 0}}
            result = audit.run_cell(cell, release, root / "results", [10, 11], phase_runner)
            self.assertEqual(result["status"], "VERIFIED")
            self.assertEqual([item["name"] for item in result["phases"]], ["encode", "decode"])
            self.assertGreater(result["phases"][0]["metrics"]["throughput_bytes_per_second"], 0)
            self.assertTrue((root / "results" / "cells" / "unit" / "result.json").is_file())

    def test_phase_exception_is_retained_as_unqualified_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "input"; source.write_bytes(b"scale")
            cell = {"cell_id": "exception", "input": {"path": str(source), "bytes": 5,
                    "sha256": audit.digest(source)}, "encode_flags": ["--threads", "1"],
                    "decode_flags": ["--threads", "1"]}
            release = {"binaries": {"cix": {"path": "/cix"}, "uncix": {"path": "/uncix"}}}
            def broken_phase_runner(**kwargs):
                raise RuntimeError("synthetic direct-child failure")
            result = audit.run_cell(cell, release, root / "missing-parent", [10], broken_phase_runner)
            receipt = root / "missing-parent" / "cells" / "exception" / "result.json"
            self.assertEqual(result["status"], "UNQUALIFIED")
            self.assertEqual(result["failed_phase"], "encode")
            self.assertIn("synthetic direct-child failure", result["execution_error"])
            self.assertEqual(json.loads(receipt.read_text())["status"], "UNQUALIFIED")
