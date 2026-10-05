#!/usr/bin/env python3
"""Capture two receipt-bound public-header analyzer contexts under a root lease.

The job runs only empty-input compiler probes.  It starts neither Sonar nor
Cppcheck and never builds a product target.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/adapter-public-header-context-v1"
ADAPTER_DB = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v6/compile_commands.host.json"
ADAPTER_RESULT = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/adapter-context-probe-v2/result.json"
ADAPTER_BASELINE = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/scan-v3/cix-native-adapters/issues.json"
BLOSC_SOURCE_RECEIPT = ROOT / "benchmark-work/native-rc-check-v1/compiler-capture-v1/receipt.json"
ROCKS_DB = ROOT / "benchmark-work/native-rc-check-v1/rocksdb-contract-ndebug-v1/build/compile_commands.json"
ROCKS_RECEIPT = ROOT / "benchmark-work/native-rc-check-v1/rocksdb-contract-ndebug-v1/receipt.json"

ENTRIES = (
    {
        "name": "blosc-c",
        "header": "rust/cix-native/adapters/blosc2/include/cix_blosc2_adapter.h",
        "source": "rust/cix-native/adapters/blosc2/src/cix_blosc2_adapter.c",
        "database": ADAPTER_DB,
        "receipt": BLOSC_SOURCE_RECEIPT,
        "normalization": "gnu-default-visibility-only",
    },
    {
        "name": "rocks-cpp",
        "header": "rust/cix-native/adapters/rocksdb/cix_compression_manager.h",
        "source": "rust/cix-native/adapters/rocksdb/cix_compression_manager.cc",
        "database": ROCKS_DB,
        "receipt": ROCKS_RECEIPT,
        "normalization": None,
    },
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_hash(receipt: dict, relative: str) -> str:
    for key in ("source_sha256", "source_hashes", "source_hash"):
        values = receipt.get(key)
        if isinstance(values, dict):
            for candidate in (relative, relative.removeprefix("rust/cix-native/"), Path(relative).name):
                value = values.get(candidate)
                if isinstance(value, str):
                    return value
    raise RuntimeError("receipt lacks a source binding for " + relative)


def command_for(entry: dict, bridge) -> tuple[dict, Path]:
    rows = json.loads(entry["database"].read_text())
    target = (ROOT / entry["source"]).resolve()
    matches = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("file"), str):
            continue
        source = Path(row["file"])
        # The passed RocksDB command references a retained snapshot; it is
        # accepted only after its receipt proves it equals the current owner TU.
        if source.name == target.name:
            matches.append(dict(row))
    if len(matches) != 1:
        raise RuntimeError(entry["name"] + ": expected one recorded owner command")
    row = matches[0]
    row["arguments"] = bridge._arguments(row)
    return row, target


def verify_entry(entry: dict, bridge) -> tuple[dict, Path, dict]:
    header, source = ROOT / entry["header"], ROOT / entry["source"]
    if not header.is_file() or not source.is_file():
        raise RuntimeError(entry["name"] + ": header or owner TU is absent")
    receipt = json.loads(entry["receipt"].read_text())
    if entry["name"] == "blosc-c":
        result = json.loads(ADAPTER_RESULT.read_text())
        if result.get("status") != "PROBE_COMPLETED_NOT_FULL_SCAN_QUALIFICATION":
            raise RuntimeError("Blosc command carrier is not the completed adapter context probe")
    else:
        if any(row.get("returncode") != 0 for row in receipt.get("commands", [])):
            raise RuntimeError("RocksDB NDEBUG qualification has a failed command")
        if receipt.get("qualification", {}).get("configuration") != "Release with explicit -DNDEBUG and no -UNDEBUG in the actual contract compile command":
            raise RuntimeError("RocksDB command is not the qualified NDEBUG configuration")
    expected = source_hash(receipt, entry["source"])
    if digest(source) != expected:
        raise RuntimeError(entry["name"] + ": current owner TU differs from its receipt")
    if digest(header) != source_hash(receipt, entry["header"]):
        raise RuntimeError(entry["name"] + ": current public header differs from its receipt")
    row, target = command_for(entry, bridge)
    recorded = Path(row["file"])
    if entry["name"] == "rocks-cpp" and digest(recorded) != expected:
        raise RuntimeError("RocksDB retained command source differs from its passed source identity")
    return row, target, receipt


def identities(bridge_path: Path, context_path: Path, repair_path: Path) -> dict:
    paths = [Path(__file__), bridge_path, context_path, repair_path, ADAPTER_DB,
             ADAPTER_RESULT, ADAPTER_BASELINE, BLOSC_SOURCE_RECEIPT, ROCKS_DB, ROCKS_RECEIPT]
    for entry in ENTRIES:
        paths.extend((ROOT / entry["header"], ROOT / entry["source"]))
    return {str(path.relative_to(ROOT)): digest(path) for path in paths}


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError("refusing to overwrite public-header context evidence")
    bridge_path = ROOT / "tools/sonar-cxx/bridge_header_context.py"
    context_path = ROOT / "tools/sonar-cxx/compiler_context.py"
    repair_path = ROOT / "tools/sonar-cxx/repair.py"
    bridge = load("public_header_bridge", bridge_path)
    context = bridge.context_module()  # shared, receipt-tested argv derivation/parser
    repair = load("public_header_budget", repair_path)
    before = identities(bridge_path, context_path, repair_path)
    budget = repair.EvidenceBudget(WORK, limit=8 * 1024**2)
    budget.mkdir(WORK); raw = WORK / "raw"; budget.mkdir(raw)
    calls, records, mappings = [], [], []
    status, error = "STARTED", None
    try:
        for entry in ENTRIES:
            row, owner, receipt = verify_entry(entry, bridge)
            argv, provenance = context.prepare_argv(row)
            expected_language = "c" if entry["name"] == "blosc-c" else "c++"
            if provenance["language"] != expected_language:
                raise RuntimeError(entry["name"] + ": compiler context inferred the wrong language")
            destination = raw / entry["name"]; budget.mkdir(destination)
            sandbox = ["bwrap", "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/", "--", *argv]
            process = subprocess.Popen(sandbox, cwd=row["directory"], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True)
            stdout, stderr = repair.collect_bounded_pipes(process, budget, timeout=30, maximum=2 * 1024**2)
            budget.write_bytes(destination / "macros.txt", stdout)
            budget.write_bytes(destination / "compiler-verbose.txt", stderr)
            calls.append({"name": entry["name"], "argv": sandbox, "cwd": row["directory"],
                          "returncode": process.returncode,
                          "macro_stdout_sha256": digest(destination / "macros.txt"),
                          "include_stderr_sha256": digest(destination / "compiler-verbose.txt")})
            if process.returncode:
                raise RuntimeError(entry["name"] + ": empty-input compiler context failed")
            parsed = context.parse_compiler_output(stdout.decode(), stderr.decode())
            defines = {item["name"]: item["value"] for item in parsed["macros"]}
            header = ROOT / entry["header"]
            if entry["name"] == "blosc-c":
                if "__cplusplus" in defines or "_WIN32" in defines or "__linux__" not in defines:
                    raise RuntimeError("Blosc capture is not the recorded non-Windows C context")
                literal = '# define CIX_BLOSC2_EXPORT __attribute__((visibility("default")))'
                if literal not in header.read_text():
                    raise RuntimeError("Blosc visibility source definition changed")
                sonar_defines = {**defines, "__attribute__(...)": ""}
                normalization = {"kind": "analyzer_only_per_file_preprocessor_normalization",
                                 "define": "__attribute__(...)", "replacement": "",
                                 "source_definition": literal,
                                 "source_header_sha256": digest(header),
                                 "abi_or_layout_claim": "none"}
            else:
                if "__cplusplus" not in defines:
                    raise RuntimeError("RocksDB capture is not C++")
                sonar_defines, normalization = defines, None
            roots = parsed["system_include_paths"]
            if any(not Path(root).is_absolute() or not Path(root).is_dir() for root in roots):
                raise RuntimeError(entry["name"] + ": compiler emitted unreadable include root")
            containers = [f"/cix-context/{entry['name']}/{index}" for index in range(len(roots))]
            records.append({"name": entry["name"], "header": entry["header"],
                            "header_sha256": digest(header), "source": entry["source"],
                            "source_sha256": digest(owner),
                            "command_database": str(entry["database"].relative_to(ROOT)),
                            "command_database_sha256": digest(entry["database"]),
                            "qualification_receipt": str(entry["receipt"].relative_to(ROOT)),
                            "qualification_receipt_sha256": digest(entry["receipt"]),
                            "compiler_context": {**parsed, "provenance": provenance},
                            "sonar_per_file": {"file": "/usr/src/" + entry["header"],
                                               "directory": "/usr/src", "defines": sonar_defines,
                                               "includes": containers,
                                               "include_paths_require_read_only_container_mapping": True},
                            "analyzer_only_normalization": normalization})
            mappings.append({"name": entry["name"], "header": entry["header"],
                             "include_paths": [{"host": root, "container": container}
                                               for root, container in zip(roots, containers)]})
        if before != identities(bridge_path, context_path, repair_path):
            raise RuntimeError("context tools, source, receipts, or command inputs changed during capture")
        repair.save(WORK / "context.json", {"schema": "cix.adapter-public-header-context.v1",
                    "entries": records, "gio_excluded_reason": "GIO remains untouched: its actual C macro expansion contains a GNU statement expression unsupported by this C++ parser"}, budget)
        repair.save(WORK / "include-mappings.json", mappings, budget)
        status = "captured_no_analyzer_run"
    except Exception as raised:
        status, error = "FAILED", str(raised)
    finally:
        receipt = {"schema": "cix.adapter-public-header-context-receipt.v1", "status": status,
                   "scope": "two empty-input contexts from exact retained C/C++ owner commands; no product build, Sonar, or Cppcheck run",
                   "input_sha256_before": before, "input_sha256_after": identities(bridge_path, context_path, repair_path),
                   "compiler_calls": calls, "sonar_or_cppcheck_started": False}
        if error: receipt["error"] = error
        for name in ("context.json", "include-mappings.json"):
            path = WORK / name
            if path.is_file(): receipt[name.replace(".json", "_sha256")] = digest(path)
        repair.save(WORK / "receipt.json", receipt, budget)
    if error:
        raise RuntimeError(error)


if __name__ == "__main__":
    main()
