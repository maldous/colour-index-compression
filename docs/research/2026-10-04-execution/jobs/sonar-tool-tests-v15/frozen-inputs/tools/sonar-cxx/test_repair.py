"""Lightweight fail-closed coverage and benchmark-isolation checks; no scans."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hashlib
import subprocess
import sys

spec = importlib.util.spec_from_file_location("repair", Path(__file__).with_name("repair.py"))
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairAcceptanceTests(unittest.TestCase):
    def test_evidence_budget_admits_exact_rounded_boundary_and_rejects_one_over(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "evidence"
            budget = repair.EvidenceBudget(root, limit=16384, failure_reserve=0)
            with patch.object(repair, "evidence_allocated_bytes", return_value=0):
                budget.write_bytes(root / "exact.bin", b"x" * 4096)
                with self.assertRaises(repair.EvidenceLimitError):
                    budget.write_bytes(root / "one-over.bin", b"x" * 12289)

    def test_evidence_budget_charges_new_entry_in_existing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "evidence"
            root.mkdir()
            budget = repair.EvidenceBudget(root, limit=4096, failure_reserve=0)
            with patch.object(repair, "evidence_allocated_bytes", return_value=0):
                with self.assertRaises(repair.EvidenceLimitError):
                    budget.write_bytes(root / "new-entry.bin", b"x")

    def test_bounded_pipe_capture_counts_both_pipes_and_kills_group(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "evidence"
            budget = repair.EvidenceBudget(root, limit=1024, failure_reserve=0)
            command = (
                "import sys; "
                "sys.stdout.write('a' * 800); sys.stdout.flush(); "
                "sys.stderr.write('b' * 800); sys.stderr.flush(); "
                "__import__('time').sleep(30)"
            )
            process = subprocess.Popen([sys.executable, "-c", command], stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, start_new_session=True)
            with patch.object(repair, "evidence_allocated_bytes", return_value=0):
                with self.assertRaises(repair.EvidenceLimitError):
                    repair.collect_bounded_pipes(process, budget, timeout=10)
            self.assertIsNotNone(process.returncode)
            self.assertNotEqual(process.returncode, 0)

    def test_projection_preexec_applies_the_file_limit(self):
        with patch.object(repair.resource, "setrlimit") as setrlimit:
            repair._projected_file_limit()
        setrlimit.assert_called_once_with(repair.resource.RLIMIT_FSIZE,
                                          (repair.CPPHECK_PROJECTED_TU_BYTES, repair.CPPHECK_PROJECTED_TU_BYTES))

    def test_projected_command_replays_compile_operands_as_preprocess(self):
        row = {"directory": "/source", "file": "/source/unit.cpp", "arguments": ["/usr/bin/c++", "-DVALUE=1", "-c",
               "/source/unit.cpp", "-o", "/old/unit.o"]}
        argv = repair._projected_command(row, Path("/evidence/unit.cpp"))
        self.assertEqual(argv, ["/usr/bin/c++", "-DVALUE=1", "/source/unit.cpp", "-E", "-o", "/evidence/unit.cpp"])

    def test_context_probe_projection_selection_is_exactly_the_three_confirmed_raw_tus(self):
        self.assertEqual(repair.CPPHECK_PROBE_V2_CONFIRMED_RELATIVES, frozenset({
            "rust/cix-native/adapters/blosc2/tests/blosc2_cix_contract.c",
            "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
            "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
        }))
        self.assertNotIn("rust/cix-native/adapters/blosc2/src/cix_blosc2_adapter.c",
                         repair.CPPHECK_PROBE_V2_CONFIRMED_RELATIVES)
        self.assertEqual(repair.CPPHECK_NEW_ANALYSIS_KERNEL_RELATIVES, frozenset({
            "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c",
            "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
            "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
        }))

    def test_projected_rows_replace_their_original_source_rows(self):
        original = {"file": "/source/unit.cpp", "arguments": ["c++", "-c", "/source/unit.cpp"]}
        projected = {"file": "/evidence/projected.cpp", "arguments": ["c++", "-c", "/evidence/projected.cpp"]}
        rows = repair._replace_projected_rows([original], [projected], [{"source": "/source/unit.cpp"}])
        self.assertEqual(rows, [projected])

    def test_overlay_expected_children_includes_staged_cfg_leaf(self):
        children = [Path("/host/libc.so.6"), Path("/host/glib-2.0")]
        self.assertEqual(repair._overlay_expected_children(children), {"libc.so.6", "glib-2.0", "cppcheck"})

    def test_preprocessor_projection_preserves_raw_and_quoted_extension_tokens(self):
        source = (
            '# 12 "fixture.cpp" 1\n#pragma GCC diagnostic ignored "-Wpedantic"\n'
            'const char* quoted = "__extension__";\nconst char* raw = R"tag(__extension__\n# 77 "literal.cpp"\n#pragma GCC diagnostic ignored)tag";\n'
            '__extension__ int value;\n'
        ).encode()
        projected, pragmas, extensions = repair._normalise_preprocessor_projection(source)
        self.assertIn(b'#line 12 "fixture.cpp"', projected)
        self.assertIn(b'"__extension__"', projected)
        self.assertIn(b'R"tag(__extension__\n# 77 "literal.cpp"\n#pragma GCC diagnostic ignored)tag"', projected)
        self.assertEqual((pragmas, extensions), (1, 1))

    def test_terminal_result_is_compacted_to_the_reserved_receipt_size(self):
        with tempfile.TemporaryDirectory() as folder:
            budget = repair.EvidenceBudget(Path(folder) / "evidence")
            with patch.object(budget, "write_text") as write:
                repair.save_terminal_result(budget.root / "result.json", {"status": "FAILED", "error": "x" * 100000}, budget)
            self.assertLessEqual(len(write.call_args.args[1].encode()), repair.TERMINAL_RECEIPT_RESERVE_BYTES)
            self.assertTrue(write.call_args.kwargs["terminal"])

    def test_server_start_contract_is_read_only_and_binds_extensions_tmpfs(self):
        mounts, command, receipt = repair.server_start_contract(["/recorded/entrypoint", "run"])
        self.assertIn("--read-only", mounts)
        self.assertIn("--log-driver", mounts)
        self.assertIn("none", mounts)
        self.assertIn("/opt/sonarqube/extensions", " ".join(mounts))
        self.assertEqual(command[-2:], ["/recorded/entrypoint", "run"])
        self.assertIn("cix-startup-exit", receipt["exit_marker"])
        self.assertEqual(receipt["image_volumes_bounded"], list(repair.SERVER_IMAGE_VOLUMES))
        self.assertIn("head -c 65536", receipt["wrapper"])
        self.assertIn("cat > /dev/null", receipt["wrapper"])

    def test_external_paths_map_attached_and_separate_include_operands(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/"source"; source.mkdir()
            external=root/"headers"; external.mkdir(); nested=external/"generated"; nested.mkdir()
            unit=source/"unit.c"; unit.write_text("int value;")
            rows=[{"file":str(unit),"directory":str(external),"arguments":["cc","-I"+str(external),"-isystem",str(nested),str(unit)]}]
            mapped,mounts=repair.containerize_commands(rows,source)
            paths=dict((str(host),container) for host,container in mounts)
            self.assertEqual(mapped[0]["file"],"/usr/src/unit.c")
            self.assertEqual(mapped[0]["directory"],paths[str(external)])
            self.assertEqual(mapped[0]["arguments"][1],"-I"+paths[str(external)])
            self.assertEqual(mapped[0]["arguments"][3],paths[str(nested)])
            self.assertNotIn(str(root),json.dumps(mapped))

    def test_c_api_capture_rejects_tampered_source_or_header(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "rust/cix-native/tests"; source.mkdir(parents=True)
            target = source / "c_api_consumer.c"; target.write_text("int main(void){}")
            header = root / "header.h"; header.write_text("x")
            receipt = root / "receipt.json"
            value = {"kind":"NEW_ANALYSIS_CONFIGURATION","returncode":0,"source":str(target),
                     "source_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),"headers":{str(header):hashlib.sha256(header.read_bytes()).hexdigest()},"cwd":str(root),"argv":["cc",str(target)]}
            repair.save(receipt,value)
            with patch.object(repair,"C_API_CAPTURE_RECEIPT",receipt):
                self.assertEqual(len(repair._c_api_capture_command(root)[0]),1)
                header.write_text("changed")
                self.assertEqual(repair._c_api_capture_command(root)[0],[])
                header.write_text("x")
                target.write_text("changed")
                self.assertEqual(repair._c_api_capture_command(root)[0],[])

    def test_host_capture_rejects_build_source_log_and_resolution_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "rust/cix-native/tests"; source.mkdir(parents=True)
            current = source / "fixture.c"; current.write_text("int x;\n")
            snapshot = root / "snapshot.c"; snapshot.write_bytes(current.read_bytes())
            host = root / "job"; host.mkdir(); work = root / "benchmark-work/native-rc-check-v1/compiler-capture-host-v3"; work.mkdir(parents=True)
            invocation = {"cwd": str(root), "argv": ["-c", str(current)]}
            receipt = {"schema":"cix.compiler-capture-host.v3","kind":"NEW_ANALYSIS_CONFIGURATION",
                       "commands":[{"returncode":0}],"compiler_invocations":[invocation],
                       "source_identity":{"fixture":{"current":str(current),"snapshot":str(snapshot),"sha256":repair.digest(current)}}}
            repair.save(work / "receipt.json", receipt); repair.save(host / "receipt.json", receipt)
            (host / "compiler-invocations.jsonl").write_text(json.dumps(invocation) + "\n")
            resolution = {"capture_receipt":{"sha256":repair.digest(work / "receipt.json")},"records":[]}
            repair.save(root / "resolution.json", resolution)
            with patch.object(repair,"HOST_V3",host), patch.object(repair,"HOST_V3_RESOLUTION",root / "resolution.json"), patch.object(repair,"ROOT",root):
                self.assertEqual(len(repair._host_capture_v3_commands(root)[0]), 1)
                bad = dict(receipt); bad["commands"]=[{"returncode":1}]; repair.save(work / "receipt.json",bad); repair.save(host / "receipt.json",bad)
                self.assertEqual(repair._host_capture_v3_commands(root)[0], [])
                repair.save(work / "receipt.json",receipt); repair.save(host / "receipt.json",receipt); current.write_text("changed")
                self.assertEqual(repair._host_capture_v3_commands(root)[0], [])
                current.write_bytes(snapshot.read_bytes()); (host / "compiler-invocations.jsonl").write_text('{"cwd":"bad","argv":[]}\n')
                self.assertEqual(repair._host_capture_v3_commands(root)[0], [])
                (host / "compiler-invocations.jsonl").write_text(json.dumps(invocation) + "\n"); resolution["capture_receipt"]["sha256"]="bad"; repair.save(root / "resolution.json",resolution)
                self.assertEqual(repair._host_capture_v3_commands(root)[0], [])
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

    def test_coverage_gate_rejects_sonar_recovery_and_scanner_syntax_errors(self):
        gaps = repair.analysis_coverage_gaps(
            [{"rule": "cxx:ParsingErrorRecovery"}],
            "WARN Source code parser: 39 syntax error(s) detected.",
            {},
        )
        self.assertEqual(gaps["cxx_parsing_error_recovery"], 1)
        self.assertEqual(gaps["scanner_syntax_errors"], 39)
        self.assertTrue(repair.has_analysis_coverage_gaps(gaps))

    def test_coverage_gate_rejects_cppcheck_configuration_findings_without_double_counting(self):
        gaps = repair.analysis_coverage_gaps(
            [{"rule": "cppcheck:unknownMacro"},
             {"rule": "cppcheck:preprocessorErrorDirective"}],
            "analysis successful",
            {"unknownMacro": 1, "preprocessorErrorDirective": 1},
        )
        self.assertEqual(gaps["cppcheck_configuration_errors"], {
            "preprocessorErrorDirective": 1,
            "unknownMacro": 1,
        })
        self.assertTrue(repair.has_analysis_coverage_gaps(gaps))

    def test_coverage_gate_allows_a_clean_parser_and_preprocessor_result(self):
        gaps = repair.analysis_coverage_gaps([], "analysis successful", {})
        self.assertEqual(gaps, {
            "cxx_parsing_error_recovery": 0,
            "scanner_syntax_errors": 0,
            "cppcheck_configuration_errors": {},
        })
        self.assertFalse(repair.has_analysis_coverage_gaps(gaps))

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

    def test_inventory_covers_current_scopes_and_detects_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for prefixes in repair.SCOPES.values():
                for prefix in prefixes:
                    target = root / prefix
                    target.mkdir(parents=True)
                    (target / "sample.cpp").write_text("int x;\n")
            before = repair.inventory(root)
            self.assertEqual(set(before), set(repair.SCOPES))
            first = next(iter(repair.SCOPES.values()))[0]
            (root / first / "sample.cpp").write_text("int changed;\n")
            self.assertNotEqual(before, repair.inventory(root))


if __name__ == "__main__":
    unittest.main()
