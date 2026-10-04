"""Capture six receipt-bound bridge header contexts under the root lease.

This is preparation evidence only.  It captures empty-input compiler builtin
macros and include search paths; it does not start Sonar or Cppcheck.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/bridge-header-context-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save_copy(destination: Path, source: Path, budget) -> None:
    """Write a retained input or result through the bounded evidence budget."""
    budget.mkdir(destination.parent)
    budget.write_bytes(destination, source.read_bytes())


def input_identities(bridge_path: Path, compiler_context_path: Path, repair_path: Path,
                     bridge) -> dict[str, str]:
    paths = [bridge_path, compiler_context_path, repair_path]
    for descriptor in bridge.BRIDGES:
        paths.extend((ROOT / descriptor.header, ROOT / descriptor.source,
                      ROOT / descriptor.database, ROOT / descriptor.receipt))
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def mirror_small_evidence(source: Path, destination: Path, repair) -> None:
    """Retain replay inputs and small compiler outputs beside this job recipe."""
    if destination.exists():
        raise RuntimeError("refusing to overwrite mirrored bridge context evidence")
    budget = repair.EvidenceBudget(destination, limit=8 * 1024**2)
    budget.mkdir(destination)
    for name in ("context.json", "include-mappings.json", "receipt.json"):
        path = source / name
        if path.is_file():
            save_copy(destination / name, path, budget)
    for descriptor in (source / "raw").glob("*/") if (source / "raw").is_dir() else ():
        for name in ("macros.txt", "compiler-verbose.txt"):
            path = descriptor / name
            if path.is_file():
                save_copy(destination / "raw" / descriptor.name / name, path, budget)


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError("refusing to overwrite bridge header context evidence")

    bridge_path = ROOT / "tools/sonar-cxx/bridge_header_context.py"
    compiler_context_path = ROOT / "tools/sonar-cxx/compiler_context.py"
    repair_path = ROOT / "tools/sonar-cxx/repair.py"
    bridge = load_module("cix_bridge_header_context", bridge_path)
    repair = load_module("cix_bridge_header_budget", repair_path)
    budget = repair.EvidenceBudget(WORK, limit=8 * 1024**2)
    budget.mkdir(WORK)
    raw = WORK / "raw"
    budget.mkdir(raw)
    calls: list[dict] = []
    call_index = 0
    captured = None
    error = None
    status = "STARTED"
    identities_before = None

    def runner(argv: list[str], cwd: Path) -> tuple[bytes, bytes, int]:
        nonlocal call_index
        if call_index >= len(bridge.BRIDGES):
            raise RuntimeError("bridge context module requested more than six compiler calls")
        descriptor = bridge.BRIDGES[call_index]
        call_index += 1
        destination = raw / descriptor.name
        budget.mkdir(destination)
        command = ["bwrap", "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/", "--", *argv]
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        stdout, stderr = repair.collect_bounded_pipes(
            process, budget, timeout=30, maximum=2 * 1024**2)
        budget.write_bytes(destination / "macros.txt", stdout)
        budget.write_bytes(destination / "compiler-verbose.txt", stderr)
        calls.append({
            "bridge": descriptor.name,
            "argv": command,
            "cwd": str(cwd),
            "returncode": process.returncode,
            "macro_stdout_sha256": sha256(destination / "macros.txt"),
            "include_stderr_sha256": sha256(destination / "compiler-verbose.txt"),
        })
        return stdout, stderr, process.returncode

    try:
        identities_before = input_identities(bridge_path, compiler_context_path, repair_path, bridge)
        frozen_inputs = JOB / "frozen-inputs"
        if frozen_inputs.exists():
            raise RuntimeError("refusing to overwrite frozen bridge context inputs")
        freeze_budget = repair.EvidenceBudget(frozen_inputs, limit=8 * 1024**2)
        freeze_budget.mkdir(frozen_inputs)
        for source in (bridge_path, compiler_context_path, repair_path):
            save_copy(frozen_inputs / source.name, source, freeze_budget)
        captured = bridge.capture_contexts(runner)
        if call_index != len(bridge.BRIDGES):
            raise RuntimeError("bridge context module did not request every configured compiler context")
        mappings = []
        for entry in captured["entries"]:
            roots = entry["compiler_context"]["system_include_paths"]
            mapped = [
                {"host": root, "container": f"/cix-context/{entry['name']}/{index}"}
                for index, root in enumerate(roots)
            ]
            entry["sonar_per_file"]["includes"] = [item["container"] for item in mapped]
            mappings.append({"bridge": entry["name"], "header": entry["header"], "include_paths": mapped})
        repair.save(WORK / "context.json", captured, budget)
        repair.save(WORK / "include-mappings.json", mappings, budget)
        status = "captured_no_analyzer_run"
    except Exception as raised:
        error = str(raised)
        status = "FAILED"
    finally:
        try:
            identities_after = input_identities(bridge_path, compiler_context_path, repair_path, bridge)
        except Exception as raised:
            identities_after = None
            if error is None:
                error = "unable to snapshot bridge context inputs after capture: " + str(raised)
                status = "FAILED"
        if identities_before is not None and identities_before != identities_after and error is None:
            error = "bridge context tools, headers, compiler databases, receipts, or bridge TUs changed during capture"
            status = "FAILED"
        receipt = {
            "schema": "cix.bridge-header-context-receipt.v1",
            "status": status,
            "scope": "current header freeze and actual compiler flags from retained qualified bridge TUs; not a new bridge build claim",
            "input_sha256_before": identities_before,
            "input_sha256_after": identities_after,
            "compiler_calls": calls,
            "sonar_or_cppcheck_started": False,
        }
        if error is not None:
            receipt["error"] = error
        if (WORK / "context.json").is_file():
            receipt["context_sha256"] = sha256(WORK / "context.json")
        if (WORK / "include-mappings.json").is_file():
            receipt["include_mappings_sha256"] = sha256(WORK / "include-mappings.json")
        repair.save(WORK / "receipt.json", receipt, budget)
        mirror_small_evidence(WORK, JOB / "captured", repair)
    if error is not None:
        raise RuntimeError(error)


if __name__ == "__main__":
    main()
