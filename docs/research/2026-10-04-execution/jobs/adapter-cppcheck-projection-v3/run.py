#!/usr/bin/env python3
"""Root-leased projection-only prerequisite; it never starts a Sonar server."""
from __future__ import annotations
import hashlib, importlib.util, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
PREPARED = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v6"
FREEZE = JOB / "frozen-scope.json"
TOOLS_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/sonar-tool-tests-v18/receipt.json"
PREFIXES = tuple(str(ROOT / "rust/cix-native" / part) + "/" for part in ("adapters", "bindings", "packaging", "tests"))


def load():
    spec = importlib.util.spec_from_file_location("projection_repair", ROOT / "tools/sonar-cxx/repair.py")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    return module


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def preflight(repair):
    freeze = json.loads(FREEZE.read_text())
    if freeze.get("schema") != "cix.adapter-sonar-derived-freeze.v4": raise RuntimeError("unknown v4 projection freeze")
    if digest(PREPARED / "plan.json") != freeze["historical_prepared_v6"]["plan_sha256"] or digest(PREPARED / "compile_commands.host.json") != freeze["historical_prepared_v6"]["compile_commands_sha256"]: raise RuntimeError("prepared-v6 changed")
    scope = {row["path"]: row["current_sha256"] for row in freeze["current_scope"]}
    if len(scope) != 55 or any(digest(ROOT / name) != sha for name, sha in scope.items()): raise RuntimeError("current 55-file scope differs from freeze")
    commands = [row for row in json.loads((PREPARED / "compile_commands.host.json").read_text()) if row["file"].startswith(PREFIXES)]
    if len(commands) != 43 or canonical(commands) != freeze["command_context"]["records_sha256"]: raise RuntimeError("43-command context differs from freeze")
    receipt = json.loads(TOOLS_RECEIPT.read_text())
    required = ("repair.py", "test_repair.py", "include_context.py", "test_include_context.py", "translation_context.py", "test_translation_context.py")
    if receipt.get("status") != "pass" or receipt.get("source_unchanged") is not True or any(receipt.get("source_sha256", {}).get("tools/sonar-cxx/" + name) != digest(ROOT / "tools/sonar-cxx" / name) for name in required): raise RuntimeError("v18 tool receipt does not bind current inputs")
    mapped, mounts, evidence = repair.rebase_include_commands(commands, ROOT)
    if len(mapped) != 43 or len(evidence) < 43: raise RuntimeError("incomplete direct include context")
    return scope, commands, {"include_operands": evidence, "mounts": [str(host) for host, _ in mounts]}


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1": raise RuntimeError("root scheduler lease required")
    repair = load(); repair.require_stopped_confirmation(repair.SUMMARY)
    if (JOB / "receipt.json").exists(): raise RuntimeError("refusing to overwrite projection prerequisite")
    scope, commands, context = preflight(repair)
    bound_paths = [Path(__file__), FREEZE, TOOLS_RECEIPT] + [ROOT / "tools/sonar-cxx" / name for name in ("repair.py", "include_context.py", "translation_context.py")]
    inputs_before = {str(path): digest(path) for path in bound_paths}
    raw = JOB / "raw"; budget = repair.EvidenceBudget(raw); budget.mkdir(raw)
    repair.save(raw / "include-context.json", context, budget)
    selected, rows = repair.project_cppcheck_translation_units(ROOT, commands, raw, budget)
    repair.save(raw / "projection-receipts.json", rows, budget)
    repair.save(raw / "projected-commands.json", selected, budget)
    if len(selected) != 43 or len(rows) != 14: raise RuntimeError("projection selection is not the reviewed 14 of 43 records")
    large = {str(ROOT / "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c"), str(ROOT / "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c")}
    if {row["source"] for row in rows if row["size_limit_bytes"] == repair.CPPHECK_KERNEL_PROJECTED_TU_BYTES} != large: raise RuntimeError("8 MiB cap is not limited to the two reviewed kernel TUs")
    if any(row["size_limit_bytes"] not in (repair.CPPHECK_PROJECTED_TU_BYTES, repair.CPPHECK_KERNEL_PROJECTED_TU_BYTES) for row in rows): raise RuntimeError("unreviewed projection cap")
    decompressor = next(row for row in rows if row["source"].endswith("cix_squashfs_decompressor.c"))
    if decompressor.get("gnu_typeof_spellings_normalised", 0) < 1: raise RuntimeError("kernel projected source did not retain the reviewed GNU typeof spelling normalisation")
    if any(row.get("gnu_typeof_spellings_normalised", 0) for row in rows if row is not decompressor): raise RuntimeError("GNU typeof normalisation escaped the decompressor projection")
    if any(digest(ROOT / name) != sha for name, sha in scope.items()): raise RuntimeError("source changed during projection")
    if any(digest(path) != sha for path, sha in inputs_before.items()): raise RuntimeError("analysis tool or frozen prerequisite changed during projection")
    (JOB / "receipt.json").write_text(json.dumps({"status":"pass", "scope_files":55, "commands":43, "projections":14, "default_cap_bytes":repair.CPPHECK_PROJECTED_TU_BYTES, "kernel_cap_bytes":repair.CPPHECK_KERNEL_PROJECTED_TU_BYTES, "source_unchanged":True, "source_sha256":{name:digest(ROOT / name) for name in sorted(scope)}, "tool_sha256":{name:digest(ROOT / "tools/sonar-cxx" / name) for name in ("repair.py","include_context.py","translation_context.py")}}, indent=2) + "\n")

if __name__ == "__main__": main()
