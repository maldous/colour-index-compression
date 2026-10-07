#!/usr/bin/env python3
"""Bounded v3 adapter Sonar context probe; dispatched only by the root lease."""
from __future__ import annotations
import argparse, collections, fcntl, hashlib, importlib.util, json, os
from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
PREPARED = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v6"
FREEZE = JOB / "frozen-scope.json"
TOOL_TEST_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/sonar-tool-tests-v15/receipt.json"
CURRENT_DELTAS = {
    "rust/cix-native/adapters/squashfs/profile/src/cix_squashfs_profile.c",
    "rust/cix-native/bindings/node/src/cix_node.c",
    "rust/cix-native/packaging/squash/contract.c",
}
BASELINE = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/scan-v3/cix-native-adapters/issues.json"
PREFIXES = tuple(str(ROOT / "rust/cix-native" / part) + "/" for part in ("adapters", "bindings", "packaging", "tests"))
TOOLS = ("repair.py", "include_context.py", "translation_context.py")
WORKER_UNIT = "cix-cxx-adapter-context-probe-v3.service"
WORKER_RUNTIME_SECONDS = 1200
CLIENT_TIMEOUT_SECONDS = 1260
SERVER_CONTAINER = "cix-cxx-adapter-context-probe-v3"
SCANNER_CONTAINER = "cix-hygiene-scanner-adapter-context-probe-v3"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def scope_and_commands():
    """Validate the immutable current-source analysis freeze without changing prepared-v6."""
    freeze = json.loads(FREEZE.read_text())
    if freeze.get("schema") != "cix.adapter-sonar-derived-freeze.v3":
        raise RuntimeError("adapter probe v3 freeze has an unknown schema")
    historical = freeze["historical_prepared_v6"]
    if digest(PREPARED / "plan.json") != historical["plan_sha256"] or digest(PREPARED / "compile_commands.host.json") != historical["compile_commands_sha256"]:
        raise RuntimeError("prepared-v6 input differs from the v3 analysis freeze")
    plan = json.loads((PREPARED / "plan.json").read_text())
    historical_files = {row["path"]: row["sha256"] for row in plan["scopes"]["cix-native-adapters"]["files"]}
    entries = freeze["current_scope"]
    expected = {row["path"]: row["current_sha256"] for row in entries}
    if len(entries) != 55 or len(expected) != 55 or set(expected) != set(historical_files):
        raise RuntimeError("v3 freeze does not retain the exact 55-file adapter scope")
    if any(row["historical_prepared_v6_sha256"] != historical_files[row["path"]] for row in entries):
        raise RuntimeError("v3 freeze does not bind every scope entry to prepared-v6")
    changed = {row["path"] for row in entries if row["historical_prepared_v6_sha256"] != row["current_sha256"]}
    if changed != CURRENT_DELTAS or set(freeze.get("current_analysis_inputs", {})) != CURRENT_DELTAS:
        raise RuntimeError("v3 freeze does not contain exactly the three current analysis-input deltas")
    context = freeze["command_context"]
    commands = [row for row in json.loads((PREPARED / "compile_commands.host.json").read_text()) if row["file"].startswith(PREFIXES)]
    if len(commands) != context["record_count"] or len(commands) != 43:
        raise RuntimeError("v3 freeze does not retain exactly 43 adapter compiler-context records")
    if canonical_json_digest(commands) != context["records_sha256"]:
        raise RuntimeError("historical adapter compiler context differs from the v3 freeze")
    return expected, commands, freeze


def validate_tool_test_receipt(repair):
    receipt = json.loads(TOOL_TEST_RECEIPT.read_text())
    required = ("repair.py", "test_repair.py", "include_context.py", "test_include_context.py", "translation_context.py", "test_translation_context.py")
    sources = receipt.get("source_sha256", {})
    if (receipt.get("status") != "pass" or receipt.get("source_unchanged") is not True or
            any(sources.get("tools/sonar-cxx/" + name) != repair.digest(ROOT / "tools/sonar-cxx" / name) for name in required) or
            not receipt.get("commands") or any(row.get("returncode") != 0 for row in receipt["commands"])):
        raise RuntimeError("focused v15 repair-tool receipt is absent, failed, or bound to different tool inputs")


def identity_label(path: Path) -> str:
    """Keep external immutable tools addressable without claiming they are repository files."""
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return "external:" + str(path)


def identities(expected: dict[str, str], repair) -> dict:
    paths = [Path(__file__).resolve(), PREPARED / "plan.json", PREPARED / "compile_commands.host.json", BASELINE, FREEZE,
             TOOL_TEST_RECEIPT,
             repair.HYGIENE / "schedule_scan.py", repair.HYGIENE / "run_scan.py"]
    paths += [ROOT / "tools/sonar-cxx" / name for name in TOOLS]
    paths += [ROOT / "tools/sonar-cxx/test_include_context.py", repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"]
    values = {identity_label(path): digest(path) for path in paths}
    values["current_adapter_scope"] = {name: repair.digest(ROOT / name) for name in sorted(expected)}
    return values


def assert_current(expected: dict[str, str], repair):
    actual = {name: repair.digest(ROOT / name) for name in sorted(expected)}
    if actual != expected:
        changed = [name for name in expected if actual.get(name) != expected[name]]
        raise RuntimeError("current adapter source differs from the derived probe freeze: " + ", ".join(changed))

def preflight_inputs(repair):
    """Read-only fail-closed validation before scheduling or starting a server."""
    validate_tool_test_receipt(repair)
    expected, commands, freeze = scope_and_commands()
    assert_current(expected, repair)
    mapped, mounts, evidence = repair.rebase_include_commands(commands, ROOT)
    if len(mapped) != 43 or len(evidence) < 43:
        raise RuntimeError("adapter compiler records lack complete direct include-context mapping")
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    if repair.digest(plugin) != repair.PACKAGES[plugin.name][1]:
        raise RuntimeError("pinned Sonar CXX plugin changed")
    temporary = repair.probe_temporary_accounting()
    return expected, commands, freeze, {"temporary_accounting": temporary,
        "historical_parser_recoveries": baseline_counts(), "identities": identities(expected, repair),
        "include_context_preflight": {"command_records": len(mapped), "mounts": [str(root) for root, _ in mounts],
                                      "operand_evidence": evidence}}


def record_early_failure(out: Path, repair, stage: str, error: Exception) -> None:
    """Persist a bounded terminal receipt for failures before execute() owns its normal finally block."""
    if (out / "result.json").exists():
        return
    try:
        budget = repair.EvidenceBudget(out)
        if not out.exists():
            budget.mkdir(out)
        raw = out / "raw"
        if not raw.exists():
            budget.mkdir(raw, failure=True)
        repair.save(raw / "early-failure.json", {"stage": stage, "error": str(error),
                    "runner_sha256": digest(Path(__file__).resolve())}, budget, failure=True)
        repair.save_terminal_result(out / "result.json", {"status": "FAILED_BEFORE_SERVER",
                    "stage": stage, "error": str(error)}, budget)
    except Exception:
        # Do not replace the original launch/preflight error if evidence storage is itself unavailable.
        pass


def baseline_counts():
    issues = json.loads(BASELINE.read_text())["issues"]
    counts = collections.Counter(row["component"].split(":", 1)[-1] for row in issues
                                 if row.get("rule") == "cxx:ParsingErrorRecovery")
    if sum(counts.values()) != 26:
        raise RuntimeError("scan-v3 adapter baseline is not the retained 26 recoveries")
    return dict(sorted(counts.items()))


def validate_projection_receipts(out: Path, repair) -> dict:
    """Require only the reviewed 14 projections and fresh kernel input evidence."""
    rows = json.loads((out / "adapter" / "cppcheck-preprocessing.json").read_text())
    if len(rows) != 14:
        raise RuntimeError("v3 did not retain exactly the reviewed 14 compiler projections")
    expected_kernel = {
        "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c",
        "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
        "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
    }
    for row in rows:
        relative = str(Path(row["source"]).resolve().relative_to(ROOT))
        if "--unshare-net" not in row["sandbox_argv"] or "-E" not in row["compiler_argv"]:
            raise RuntimeError("projection lacks its actual isolated compiler-preprocessing contract")
        if relative in expected_kernel:
            evidence = row.get("input_context")
            if not evidence or evidence.get("kind") != "NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF" or not evidence.get("sha256"):
                raise RuntimeError("kernel projection lacks fresh, explicitly non-historical input evidence")
        if row.get("removed_dependency_outputs") and any(value in row["compiler_argv"] for value in row["removed_dependency_outputs"]):
            raise RuntimeError("dependency-output normalization did not remove the analyzer-side effect")
    errors = [row.attrib for row in repair.ET.parse(out / "adapter" / "cppcheck.xml").iter("error")]
    counts = collections.Counter(row["id"] for row in errors)
    fatal = {name: counts.get(name, 0) for name in ("preprocessorErrorDirective", "unknownMacro")}
    if any(fatal.values()):
        raise RuntimeError("v3 retains Cppcheck configuration diagnostics: " + repr(fatal))
    return {"projection_count": len(rows), "kernel_analysis_input_freezes": len(expected_kernel), "cppcheck_configuration_diagnostics": fatal}


def execute(out: Path, parent: str):
    repair = load("adapter_probe_repair", ROOT / "tools/sonar-cxx/repair.py")
    repair.require_stopped_confirmation(repair.SUMMARY)
    expected, commands, freeze, preflight = preflight_inputs(repair)
    budget = repair.EvidenceBudget(out); budget.mkdir(out); raw = out / "raw"; budget.mkdir(raw)
    before = preflight["identities"]
    repair.save(raw / "identities.json", before, budget)
    repair.save(raw / "temporary-accounting.json", preflight["temporary_accounting"], budget)
    repair.save(raw / "include-context-preflight.json", preflight["include_context_preflight"], budget)
    repair.save(raw / "historical-baseline.json", {"issues_sha256": digest(BASELINE),
                "parsing_error_recovery_by_file": baseline_counts()}, budget)
    repair.save(raw / "scope.json", {"derived_freeze": freeze, "commands": 43,
                "scope": "current immutable 55-file analysis scope; all 43 compiler records are historical context only"}, budget)
    h = load("adapter_probe_runtime", repair.HYGIENE / "run_scan.py")
    base, server, token = "http://127.0.0.1:9017", SERVER_CONTAINER, None
    password, envfile = "Aa1!" + repair.secrets.token_urlsafe(32), raw / ".scanner-env"
    results = {"status": "STARTED", "kind": "FROZEN_ADAPTER_CONTEXT_PROBE_V3",
               "files": 55, "commands": 43, "historical_parser_recoveries": preflight["historical_parser_recoveries"]}
    options, command, contract = repair.server_start_contract()
    repair.save(raw / "server-start-contract.json", contract, budget)
    try:
        h.docker_run(server, h.SERVER_IMAGE, h.SERVER_MEMORY, parent, [
            "-p", "127.0.0.1:9017:9000", *options,
            "-v", f"{repair.prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)}:/opt/sonarqube/lib/extensions:ro",
            "-v", f"{repair.TOOLS / 'sonar-cxx-plugin-2.3.0.1496.jar'}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"], command)
        repair.wait_server_or_exit(h, base, password, server)
        if "cxx" not in {row["key"] for row in repair.request(h, base, password, "/api/languages/list")["languages"]}:
            raise RuntimeError("CXX sensor is unavailable")
        repair.profile(h, base, password, raw, budget)
        token = repair.request(h, base, password, "/api/user_tokens/generate", {"name": "cix-adapter-context"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"
        budget.admit(envfile, len(credentials.encode()))
        descriptor = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream: stream.write(credentials)
        results["probe"] = repair.scan(h, base, password, token, envfile, parent,
                                       "adapter-context-probe-v3", ROOT, sorted(expected), commands,
                                       out / "adapter", budget)
        results["projection_postconditions"] = validate_projection_receipts(out, repair)
        assert_current(expected, repair)
        after = identities(expected, repair)
        if before != after:
            raise RuntimeError("source, derived freeze, focused tool receipt, baseline, or scanner tools changed during probe")
        results["status"] = "PROBE_COMPLETED_NOT_FULL_SCAN_QUALIFICATION"
    except Exception as error:
        results.update(status="FAILED", error=h.scrub(str(error), [password, token])); raise
    finally:
        try:
            if token:
                try: repair.request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-adapter-context"})
                except Exception: results["token_revocation"] = "failed; ephemeral server removed"
            if envfile.exists(): envfile.unlink()
            budget.write_text(raw / "server.log", repair.bounded_server_log(server, budget, h, [password, token]), failure=True)
        finally:
            try: h.stop(server)
            finally: repair.save_terminal_result(out / "result.json", results, budget)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "worker")); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    repair = load("adapter_probe_repair_entry", ROOT / "tools/sonar-cxx/repair.py")
    if args.action == "worker":
        try:
            if "cix-cxx-hygiene.slice" not in Path("/proc/self/cgroup").read_text():
                raise RuntimeError("worker is outside the reserved aggregate slice")
            execute(out, "cix-cxx-hygiene.slice")
        except Exception as error:
            record_early_failure(out, repair, "worker-preflight-or-setup", error)
            raise
        return
    repair.require_stopped_confirmation(repair.SUMMARY)
    if out.exists(): raise RuntimeError("refusing to overwrite an adapter probe attempt")
    # No unit, container, or slice is created until source, mapper, identity, and capacity preflight pass.
    try:
        preflight_inputs(repair)
    except Exception as error:
        record_early_failure(out, repair, "parent-preflight", error)
        raise
    scheduler_module = repair.load_module("adapter_probe_scheduler", repair.HYGIENE / "schedule_scan.py")
    scheduler = scheduler_module.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True); parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [scheduler_module._core(cpu) for cpu in scheduler_module.CPUS]}])
        try:
            repair.assert_benchmark_idle(); scheduler_module._make_slice(parent, anchor)
            receipt = scheduler_module._slice_receipt(parent); scheduler_module._verify_slice(receipt)
            command = ["sudo", "-n", "systemd-run", "--unit", WORKER_UNIT,
                       f"--property=RuntimeMaxSec={WORKER_RUNTIME_SECONDS}s",
                       "--uid", str(os.getuid()), "--gid", str(os.getgid()), "--wait", "--pipe", "--collect",
                       "--slice", parent, sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(out)]
            result = subprocess.run(command, timeout=CLIENT_TIMEOUT_SECONDS)
            if out.exists(): repair.EvidenceBudget(out).write_text(out / "slice-receipt.txt", receipt)
            if result.returncode: raise RuntimeError("adapter context probe failed; retained evidence explains the result")
        finally:
            # Each cleanup name is unique to this probe. Stop the worker first so it cannot
            # create a replacement container while cleanup is in progress.
            subprocess.run(["sudo", "-n", "systemctl", "stop", WORKER_UNIT], check=False, capture_output=True, timeout=30)
            for container in (SCANNER_CONTAINER, SERVER_CONTAINER):
                subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True, timeout=30)
            subprocess.run(["sudo", "-n", "systemctl", "reset-failed", WORKER_UNIT], check=False, capture_output=True, timeout=30)
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True, timeout=30)
            for lease in leases: lease.close()

if __name__ == "__main__": main()
