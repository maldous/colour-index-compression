"""Read actual JXL compiler context under the existing root resource lease."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/compiler-context-capture-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    WORK.mkdir()
    context_path = ROOT / "tools/sonar-cxx/compiler_context.py"
    repair_path = ROOT / "tools/sonar-cxx/repair.py"
    identities = {str(path.relative_to(ROOT)): sha(path) for path in (context_path, repair_path)}
    context = module("cix_context_capture", context_path)
    repair = module("cix_context_budget", repair_path)
    budget = repair.EvidenceBudget(WORK, limit=8 * 1024**2)
    qualified = ROOT / "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1"
    receipt_path = qualified / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if receipt["status"] != "pass" or not receipt["source_unchanged"] or not receipt["dependencies_unchanged"]:
        raise RuntimeError("JXL qualification was not successful")
    for relative, expected in receipt["source_sha256"].items():
        if sha(qualified / "source" / relative) != expected:
            raise RuntimeError("qualified source changed")
    dependency = Path(receipt["dependency_root"])
    for relative, expected in receipt["dependency_sha256"].items():
        if sha(dependency / relative) != expected:
            raise RuntimeError("qualified dependency changed")
    database_path = qualified / "build/compile_commands.json"
    rows = json.loads(database_path.read_text())
    if len(rows) != 1:
        raise RuntimeError("expected exactly one qualified JXL TU")
    row = rows[0]
    record = {**row, "arguments": row.get("arguments") or shlex.split(row["command"])}
    argv, provenance = context.prepare_argv(record)
    # No container is launched. The existing compiler runs with its host view
    # mounted read-only and no network; empty stdin supplies no header guards.
    command = ["bwrap", "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/", "--", *argv]
    process = subprocess.Popen(command, cwd=record["directory"], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    stdout, stderr = repair.collect_bounded_pipes(process, budget, timeout=30, maximum=2 * 1024**2)
    budget.write_bytes(WORK / "macros.txt", stdout)
    budget.write_bytes(WORK / "compiler-verbose.txt", stderr)
    if process.returncode:
        raise RuntimeError("compiler context probe failed: " + stderr.decode(errors="replace"))
    parsed = context.parse_compiler_output(stdout.decode(), stderr.decode())
    names = {entry["name"] for entry in parsed["macros"]}
    if "CIX_JXL_BRIDGE_H" in names or "__cplusplus" not in names:
        raise RuntimeError("probe contains the target header guard or lacks actual C++ context")
    process = subprocess.Popen(["ninja", "-C", str(qualified / "build"), "-t", "deps"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    deps_stdout, deps_stderr = repair.collect_bounded_pipes(process, budget, timeout=30, maximum=2 * 1024**2)
    if process.returncode:
        raise RuntimeError("retained Ninja dependency read failed")
    budget.write_bytes(WORK / "ninja-dependencies.txt", deps_stdout)
    budget.write_bytes(WORK / "ninja-dependencies.stderr.txt", deps_stderr)
    parsed["provenance"] = {**provenance, "sandbox_argv": command, "exit_code": 0,
        "compile_database_sha256": sha(database_path), "qualified_receipt_sha256": sha(receipt_path),
        "tool_sha256": identities, "macro_stdout_sha256": sha(WORK / "macros.txt"),
        "include_stderr_sha256": sha(WORK / "compiler-verbose.txt"),
        "scope": "C++ context of the actual qualified JXL bridge compilation; not a global context for unrelated C or kernel files"}
    if any(sha(ROOT / name) != expected for name, expected in identities.items()):
        raise RuntimeError("tool changed during context capture")
    repair.save(WORK / "context.json", parsed, budget)
    for path in WORK.iterdir():
        if path.is_file():
            shutil.copyfile(path, JOB / path.name)
    for name in identities:
        shutil.copyfile(ROOT / name, JOB / (Path(name).name + ".txt"))


if __name__ == "__main__":
    main()
