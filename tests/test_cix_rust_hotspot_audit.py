import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "benchmarks/cix_rust_hotspot_audit.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HotspotAuditTest(unittest.TestCase):
    def test_prepare_only_binds_fixture_and_pins_perf_before_opening_counters(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            fixture = base / "fixture.bin"; fixture.write_bytes(b"CIX hotspot fixture\n")
            release = base / "release"; release.mkdir()
            bins = {}
            for name in ("cix", "uncix"):
                p = release / name; p.write_text("#!/bin/sh\nexit 0\n"); p.chmod(p.stat().st_mode | stat.S_IXUSR)
                bins[name] = {"sha256": sha(p)}
            (release / "native-release.json").write_text(json.dumps({"source_revision": "a" * 40, "binaries": bins}))
            plan = base / "plan.json"
            plan.write_text(json.dumps({"rows": [{"task_id": "row", "profile": "default", "flags": [], "threads": 1,
                "input": {"path": str(fixture), "sha256": sha(fixture), "bytes": fixture.stat().st_size}}]}))
            output = base / "out"
            run = subprocess.run([sys.executable, str(SCRIPT), "prepare", "--release", str(release), "--cca-plan", str(plan), "--task-id", "row", "--output", str(output)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            value = json.loads((output / "preflight.json").read_text())
            self.assertEqual(value["status"], "PREPARED_NOT_EXECUTED_AWAITING_QUALIFIED_RELEASE_FREEZE")
            self.assertFalse((output / "raw").exists())
            for item in value["cpu_profiles"]:
                stat_command = item["commands"]["perf_stat"]
                self.assertEqual(stat_command[:5], ["/usr/bin/taskset", "-c", str(item["cpu"]["cpu"]), "/usr/bin/perf", "stat"])
                events = stat_command[stat_command.index("-e") + 1].split(",")
                self.assertTrue({"cache-misses", "branch-misses", "context-switches", "cpu-migrations"}.issubset(events))

    def test_run_refuses_to_start_without_execute(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            (output / "preflight.json").write_text(json.dumps({"status": "PREPARED_NOT_EXECUTED_AWAITING_QUALIFIED_RELEASE_FREEZE"}))
            run = subprocess.run([sys.executable, str(SCRIPT), "run", "--output", str(output), "--freeze", str(output / "freeze.json"), "--scheduler-lease", str(output / "lease.json")], text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("requires --execute", run.stderr)


if __name__ == "__main__":
    unittest.main()

class HotspotLeaseGuardTest(unittest.TestCase):
    @staticmethod
    def module():
        import importlib.util
        spec = importlib.util.spec_from_file_location("hotspot_audit", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def valid_lease(self, module, directory: Path):
        preflight = {"task": {"task_id": "row"}, "release": {"source_revision": "a" * 40},
                     "cpu_profiles": [{"cpu": {"cpu": 8}}, {"cpu": {"cpu": 16}}]}
        binding = module.preflight_sha256(preflight)
        claim = directory / "claim.json"
        claim.write_text(json.dumps({"status": "ACTIVE", "claim_id": "hotspot-row", "preflight_sha256": binding}))
        lease = {"status": "ACTIVE", "claim_id": "hotspot-row", "scheduler": {"status": "ACTIVE", "active_claim_id": "hotspot-row"}, "preflight_sha256": binding,
                 "task_id": "row", "release": preflight["release"], "cpus": [8, 16],
                 "physical_cores": [module.physical_core(8), module.physical_core(16)],
                 "resources": {"memory_max_bytes": 1_073_741_824, "swap_max_bytes": 0,
                               "aggregate_memory_reserved_bytes": 2_147_483_648, "aggregate_swap_bytes": 0},
                 "allowed_phases": ["perf_stat", "perf_record", "perf_lock", "strace_io"],
                 "active_claim_path": str(claim), "active_claim_sha256": sha(claim)}
        return preflight, lease

    def test_lease_rejects_wrong_cpu_memory_swap_status_and_phase(self):
        with tempfile.TemporaryDirectory() as temp:
            module = self.module(); preflight, lease = self.valid_lease(module, Path(temp))
            module.validate_lease(lease, preflight)
            for field, value in (("status", "LEASED"), ("cpus", [8]), ("allowed_phases", ["perf_stat"]),
                                 ("resources", {"memory_max_bytes": 1_073_741_824, "swap_max_bytes": 1,
                                                "aggregate_memory_reserved_bytes": 2_147_483_648, "aggregate_swap_bytes": 0})):
                broken = dict(lease); broken[field] = value
                with self.assertRaises(RuntimeError):
                    module.validate_lease(broken, preflight)
            wrong_core = dict(lease); wrong_core["physical_cores"] = [module.physical_core(8), module.physical_core(8)]
            with self.assertRaises(RuntimeError):
                module.validate_lease(wrong_core, preflight)
            claim = Path(lease["active_claim_path"])
            claim.write_text(json.dumps({"status": "STALE", "claim_id": "hotspot-row", "preflight_sha256": lease["preflight_sha256"]}))
            with self.assertRaises(RuntimeError):
                module.validate_lease(lease, preflight)
