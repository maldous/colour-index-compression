"""Fixtures for the isolated completed boundary-command reader."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "compiler_refresh", Path(__file__).with_name("compiler_refresh.py"))
refresh = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = refresh
spec.loader.exec_module(refresh)


class CompilerRefreshTests(unittest.TestCase):
    def _fixture(self, folder: Path) -> tuple[Path, tuple[object, ...]]:
        root = folder / "project"
        jobs, work = root / "jobs", root / "work"
        current = root / "current"
        for relative in ("rocks", "spatial/tests"):
            (current / relative).mkdir(parents=True, exist_ok=True)
        (current / "rocks/CMakeLists.txt").write_text("project(rocks)\n")
        (current / "rocks/cix_compression_manager.cc").write_text('#include "cix_compression_manager.h"\n')
        (current / "rocks/cix_compression_manager.h").write_text("#pragma once\n")
        (current / "rocks/contract_test.cc").write_text('#include "cix_compression_manager.h"\n')
        (current / "spatial/CMakeLists.txt").write_text("project(spatial)\n")
        (current / "spatial/cix_spatial_bridge.cpp").write_text('#include "cix_spatial_bridge.h"\n')
        (current / "spatial/cix_spatial_bridge.h").write_text("#pragma once\n")
        (current / "spatial/tests/spatial_stride_contract.cpp").write_text('#include "cix_spatial_bridge.h"\n')
        specs = (
            refresh._CmakeReceipt("rocks", "rocks", "rocks", ("cix_compression_manager.cc", "contract_test.cc"),
                                  ("CMakeLists.txt", "cix_compression_manager.cc", "cix_compression_manager.h", "contract_test.cc")),
            refresh._CmakeReceipt("spatial", "spatial", "spatial", ("cix_spatial_bridge.cpp",),
                                  ("CMakeLists.txt", "cix_spatial_bridge.cpp", "cix_spatial_bridge.h")),
        )
        for job, source_root, unit_names in (("rocks", current / "rocks", ("cix_compression_manager.cc", "contract_test.cc")),
                                             ("spatial", current / "spatial", ("cix_spatial_bridge.cpp",))):
            retained = work / job
            snapshot, build = retained / "source", retained / "build"
            for source_file in source_root.rglob("*"):
                if source_file.is_file():
                    copied = snapshot / source_file.relative_to(source_root)
                    copied.parent.mkdir(parents=True, exist_ok=True)
                    copied.write_bytes(source_file.read_bytes())
            rows = []
            for unit in unit_names:
                target = "cix_rocksdb_compression_manager" if unit == "cix_compression_manager.cc" else (
                    "cix_rocksdb_contract" if unit == "contract_test.cc" else "cix_spatial_bridge")
                object_dir = build / "CMakeFiles" / f"{target}.dir"
                object_dir.mkdir(parents=True, exist_ok=True)
                source_file = snapshot / unit
                header = snapshot / ("cix_compression_manager.h" if job == "rocks" else "cix_spatial_bridge.h")
                (object_dir / f"{unit}.o.d").write_text(f"out: {source_file} {header}\n")
                rows.append({"directory": str(build), "file": str(source_file),
                             "arguments": ["/usr/bin/c++", "-O3", "-c", str(source_file)]})
            # The production spatial receipt uses project-relative keys; file
            # names exercise the helper's equivalent accepted receipt form.
            hashes = {path.name: refresh._digest(path) for path in snapshot.rglob("*") if path.is_file()}
            commands = [{"returncode": 0}]
            if job == "spatial":
                prefix = retained / "prefix/include/cix"; prefix.mkdir(parents=True)
                (prefix / "cix_spatial_bridge.h").write_bytes((snapshot / "cix_spatial_bridge.h").read_bytes())
                test = snapshot / "tests/spatial_stride_contract.cpp"
                commands.append({"label": "compile-contract", "returncode": 0,
                                 "argv": ["c++", "-Wall", "-Wextra", "-Werror", str(test),
                                          "-I", str(prefix), "-L", str(retained / "prefix/lib"),
                                          "-Wl,-rpath," + str(retained / "prefix/lib"),
                                          "-lcix_spatial_bridge", "-o",
                                          str(retained / "spatial_stride_contract")]})
                receipt = {"status": "pass", "commands": commands, "source_sha256": hashes}
            else:
                receipt = {"commands": commands, "source_sha256": hashes}
            (jobs / job).mkdir(parents=True)
            for receipt_path in (jobs / job / "receipt.json", retained / "receipt.json"):
                receipt_path.parent.mkdir(parents=True, exist_ok=True)
                receipt_path.write_text(json.dumps(receipt))
            for database_path in (jobs / job / "compile_commands.json", build / "compile_commands.json"):
                database_path.parent.mkdir(parents=True, exist_ok=True)
                database_path.write_text(json.dumps(rows))
        return current, specs

    def test_matching_current_sources_emit_cmake_and_direct_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            current, specs = self._fixture(root)
            with patch.object(refresh, "JOBS", root / "project/jobs"), patch.object(refresh, "WORK", root / "project/work"):
                rows, provenance = refresh._completed_boundary_commands(current, specs)
            self.assertEqual({Path(row["file"]).name for row in rows},
                             {"cix_compression_manager.cc", "contract_test.cc", "cix_spatial_bridge.cpp", "spatial_stride_contract.cpp"})
            direct = next(row for row in rows if Path(row["file"]).name == "spatial_stride_contract.cpp")
            self.assertNotIn("-c", direct["arguments"])
            self.assertIn("-Wall", direct["arguments"])
            self.assertEqual(provenance["spatial-direct"]["status"], "qualified_direct_compiler_argv_reused")

    def test_changed_header_or_database_mirror_rejects_affected_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            current, specs = self._fixture(root)
            (current / "spatial/cix_spatial_bridge.h").write_text("changed\n")
            with patch.object(refresh, "JOBS", root / "project/jobs"), patch.object(refresh, "WORK", root / "project/work"):
                rows, provenance = refresh._completed_boundary_commands(current, specs)
            self.assertNotIn("cix_spatial_bridge.cpp", {Path(row["file"]).name for row in rows})
            self.assertEqual(provenance["spatial"]["status"], "stale_source_or_header")
            current, specs = self._fixture(root / "second")
            documented = root / "second/project/jobs/rocks/compile_commands.json"
            documented.write_text("[]")
            with patch.object(refresh, "JOBS", root / "second/project/jobs"), patch.object(refresh, "WORK", root / "second/project/work"):
                _, provenance = refresh._completed_boundary_commands(current, specs)
            self.assertEqual(provenance["rocks"]["status"], "unavailable")

    def test_changed_installed_spatial_header_rejects_only_direct_row(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            current, specs = self._fixture(root)
            installed = root / "project/work/spatial/prefix/include/cix/cix_spatial_bridge.h"
            installed.write_text("changed\n")
            with patch.object(refresh, "JOBS", root / "project/jobs"), patch.object(refresh, "WORK", root / "project/work"):
                rows, provenance = refresh._completed_boundary_commands(current, specs)
            self.assertIn("cix_spatial_bridge.cpp", {Path(row["file"]).name for row in rows})
            self.assertNotIn("spatial_stride_contract.cpp", {Path(row["file"]).name for row in rows})
            self.assertEqual(provenance["spatial-direct"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
