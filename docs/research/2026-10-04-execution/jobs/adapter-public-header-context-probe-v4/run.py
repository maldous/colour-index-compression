#!/usr/bin/env python3
"""Bounded Sonar probe for the RocksDB public header using its exact C++ argv.

The v2 probe used synthetic ``defines`` and ``includes`` fields.  This probe
keeps the recorded owner command's semantic arguments, rebases only its CIX
public-header source operand and recorded include paths onto read-only mounts,
and runs inside the existing exclusive CXX hygiene helper.
"""
from __future__ import annotations
import argparse, collections, fcntl, hashlib, importlib.util, inspect, json, os, subprocess, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
CAPTURE = ROOT / "benchmark-work/native-rc-check-v1/adapter-public-header-context-v1"
BASELINE = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/adapter-context-probe-v2/adapter/issues.json"
TOOL_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/sonar-tool-tests-v18/receipt.json"
HEADER = "rust/cix-native/adapters/rocksdb/cix_compression_manager.h"
OWNER = "rust/cix-native/adapters/rocksdb/cix_compression_manager.cc"
EXPECTED = {HEADER: 2}
SERVER = "cix-cxx-adapter-public-header-context-v3"
SCANNER = "cix-hygiene-scanner-rocks-full-context"
WORKER_UNIT = "cix-cxx-adapter-public-header-context-v3.service"
WORKER_RUNTIME_SECONDS = 1200
CLIENT_TIMEOUT_SECONDS = 1260


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def baseline_counts() -> dict[str, int]:
    issues = json.loads(BASELINE.read_text())["issues"]
    counts = {header: sum(row.get("rule") == "cxx:ParsingErrorRecovery" and
                          row.get("component", "").endswith(header) for row in issues)
              for header in (HEADER,)}
    if counts != EXPECTED:
        raise RuntimeError("retained RocksDB parser baseline changed: " + repr(counts))
    return counts


def verify_tool_receipt(repair) -> None:
    receipt = json.loads(TOOL_RECEIPT.read_text())
    required = ("repair.py", "include_context.py", "translation_context.py")
    if receipt.get("status") != "pass" or receipt.get("source_unchanged") is not True:
        raise RuntimeError("current Sonar tool receipt did not pass")
    if any(receipt.get("source_sha256", {}).get("tools/sonar-cxx/" + name) !=
           repair.digest(ROOT / "tools/sonar-cxx" / name) for name in required):
        raise RuntimeError("Sonar tool receipt is not bound to current analysis tools")


def captured_context(repair):
    """Build one standard JSON-compilation row from the recorded Rocks argv.

    v2 already proved the paths named by GCC's verbose include list are mounted.
    It did not preserve the command's ``-I`` spelling, category, or order.  This
    carrier retains every semantic option from the NDEBUG-qualified C++ TU and
    changes only its input from the owner TU to this owned public header.
    """
    paths = {name: CAPTURE / name for name in ("context.json", "include-mappings.json", "receipt.json")}
    if any(not path.is_file() for path in paths.values()):
        raise RuntimeError("public-header context capture is absent")
    receipt, context, mappings = (json.loads(paths[name].read_text()) for name in ("receipt.json", "context.json", "include-mappings.json"))
    if receipt.get("status") != "captured_no_analyzer_run" or receipt.get("input_sha256_before") != receipt.get("input_sha256_after"):
        raise RuntimeError("public-header context capture is incomplete or changed during capture")
    if receipt.get("context_sha256") != digest(paths["context.json"]) or receipt.get("include-mappings_sha256") != digest(paths["include-mappings.json"]):
        raise RuntimeError("public-header context receipt does not bind its context files")
    entries = {row.get("header"): row for row in context.get("entries", []) if isinstance(row, dict)}
    mapped = {row.get("header"): row for row in mappings if isinstance(row, dict)}
    entry, mapping = entries.get(HEADER), mapped.get(HEADER)
    if not isinstance(entry, dict) or not isinstance(mapping, dict):
        raise RuntimeError("capture lacks the RocksDB public-header entry")
    if digest(ROOT / HEADER) != entry.get("header_sha256") or digest(ROOT / OWNER) != entry.get("source_sha256"):
        raise RuntimeError("current RocksDB header or owner TU differs from capture")
    provenance = entry.get("compiler_context", {}).get("provenance")
    if not isinstance(provenance, dict) or provenance.get("compiler") != "/usr/bin/c++":
        raise RuntimeError("capture lacks the exact C++ compiler provenance")
    retained = provenance.get("retained")
    recorded = provenance.get("recorded_argv")
    compiler_context = entry.get("compiler_context")
    if (not isinstance(retained, list) or not all(isinstance(value, str) for value in retained)
            or not isinstance(recorded, list) or not all(isinstance(value, str) for value in recorded)
            or provenance.get("source") not in recorded or "-c" not in recorded
            or not isinstance(compiler_context, dict)):
        raise RuntimeError("capture lacks one exact owner-TU compile argv")
    if any(value in {"-c", "-o"} or value.startswith("-o") for value in retained):
        raise RuntimeError("captured semantic options contain an output or source action")
    header = (ROOT / HEADER).resolve()
    captured_paths = compiler_context.get("system_include_paths")
    captured_macros = compiler_context.get("macros")
    if (not isinstance(captured_paths, list) or not all(isinstance(value, str) for value in captured_paths)
            or not isinstance(captured_macros, list) or not all(isinstance(value, dict) for value in captured_macros)):
        raise RuntimeError("capture lacks measured implicit include or macro context")
    original_user_roots = [value[2:] for value in retained if value.startswith("-I")]
    if captured_paths[:len(original_user_roots)] != original_user_roots:
        raise RuntimeError("compiler include search does not begin with the recorded user roots")
    implicit_roots = captured_paths[len(original_user_roots):]
    if not implicit_roots or any(not Path(value).is_dir() for value in implicit_roots):
        raise RuntimeError("captured C++ standard-library roots are absent or unreadable")
    defines = {value.get("name"): value.get("value", "") for value in captured_macros
               if isinstance(value.get("name"), str) and isinstance(value.get("value", ""), str)}
    if len(defines) != len(captured_macros) or "__cplusplus" not in defines:
        raise RuntimeError("captured C++ builtin macros are incomplete")
    # A header has no historical object output. The carrier retains the exact
    # user options and then materializes the measured implicit GCC search list
    # as ordered -isystem operands. It also retains the actual empty-input
    # builtin macro set through the plugin's supported per-file field.
    carrier = {"file": str(header), "directory": provenance["directory"],
               "arguments": [provenance["compiler"], *retained,
                             *[item for root in implicit_roots for item in ("-isystem", root)],
                             "-c", str(header)],
               "defines": defines}
    rows, mounts, evidence = repair.rebase_include_commands([carrier], ROOT)
    if len(rows) != 1 or len(mounts) < 3 or not isinstance(rows[0].get("arguments"), list):
        raise RuntimeError("recorded RocksDB include context could not be rebased")
    row = rows[0]
    if row.get("file") != "/usr/src/" + HEADER or row.get("defines") != defines or "includes" in row:
        raise RuntimeError("full compiler context is not a faithful header carrier")
    actual_includes = [value for value in row["arguments"] if value.startswith("-I")]
    expected_includes = [value for value in retained if value.startswith("-I")]
    if len(actual_includes) != len(expected_includes) or len(actual_includes) != 3:
        raise RuntimeError("RocksDB user include roots were lost while rebasing")
    operands = [value for value in evidence if value.get("flag") == "-I"]
    if [value.get("original") for value in operands] != [value[2:] for value in expected_includes]:
        raise RuntimeError("RocksDB user include ordering differs from qualified command")
    if any(value.get("disposition") != "resolved-directory" or value.get("mount_read_only") is not True or not str(value.get("mapped", "")).startswith(("/cix-external/", "/usr/src/")) for value in operands):
        raise RuntimeError("RocksDB user include root is not a read-only mapped directory")
    captured_roots = mapping.get("include_paths")
    if not isinstance(captured_roots, list):
        raise RuntimeError("capture lacks its RocksDB include mapping")
    captured_hosts = [value.get("host") for value in captured_roots if isinstance(value, dict)]
    if [value[2:] for value in expected_includes] != captured_hosts[:len(expected_includes)]:
        raise RuntimeError("captured RocksDB user roots differ from the qualified command")
    system_operands = [value for value in evidence if value.get("flag") == "-isystem"]
    if [value.get("original") for value in system_operands] != implicit_roots:
        raise RuntimeError("captured implicit C++ include order differs after rebasing")
    if any(value.get("disposition") != "resolved-directory" or value.get("mount_read_only") is not True or not str(value.get("mapped", "")).startswith(("/cix-external/", "/usr/src/")) for value in system_operands):
        raise RuntimeError("captured C++ standard-library roots are not read-only mapped directories")
    if "-DNDEBUG" not in row["arguments"] or "-std=gnu++20" not in row["arguments"] or "-fno-rtti" not in row["arguments"]:
        raise RuntimeError("RocksDB qualified C++ language context was not retained")
    proof = {"header": HEADER, "header_sha256": entry["header_sha256"], "owner": OWNER,
             "owner_sha256": entry["source_sha256"], "qualified_command": recorded,
             "retained_semantic_arguments": retained, "header_carrier_arguments": row["arguments"],
             "compiler_builtin_defines": defines,
             "analysis_only_implicit_system_roots": implicit_roots,
             "include_operand_resolution": evidence, "read_only_include_mounts": [
                 {"host": str(host), "container": container} for host, container in mounts],
             "normalization": None,
             "scope": "qualified -I options/order plus measured implicit GCC standard-library roots and builtins; only owner input is substituted by the public header"}
    return row, mounts, proof, paths


def identities(repair, capture_paths: dict[str, Path]) -> dict:
    values = {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
              str(BASELINE.relative_to(ROOT)): digest(BASELINE),
              str(TOOL_RECEIPT.relative_to(ROOT)): digest(TOOL_RECEIPT)}
    for path in capture_paths.values(): values[str(path.relative_to(ROOT))] = digest(path)
    for header in (HEADER, OWNER): values[header] = digest(ROOT / header)
    for name in ("repair.py", "include_context.py", "translation_context.py"):
        path = ROOT / "tools/sonar-cxx" / name; values[str(path.relative_to(ROOT))] = digest(path)
    for path in (repair.HYGIENE / "schedule_scan.py", repair.HYGIENE / "run_scan.py"):
        values[str(path.relative_to(ROOT))] = digest(path)
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    values["external:" + str(plugin)] = digest(plugin)
    return values


def validate_helper_signatures(repair) -> None:
    """Reject analysis-tool drift before slice allocation or server start."""
    expected = {
        "bounded_scanner": ("h", "base", "password", "token", "envfile", "parent", "name", "source", "out", "budget", "include_mounts"),
        "rebase_include_commands": ("commands", "source"),
        "collect": ("h", "base", "key", "task", "password", "out", "budget"),
        "validate_indexed": ("files", "components", "log"),
        "save": ("path", "value", "budget", "failure", "terminal"),
        "save_terminal_result": ("path", "value", "budget"),
        "probe_temporary_accounting": (),
        "server_start_contract": ("entrypoint",),
        "wait_server_or_exit": ("h", "base", "password", "server"),
        "profile": ("h", "base", "password", "raw", "budget"),
        "bounded_server_log": ("server", "budget", "h", "secrets_to_scrub"),
    }
    for name, parameters in expected.items():
        if tuple(inspect.signature(getattr(repair, name)).parameters) != parameters:
            raise RuntimeError("repair helper signature changed: " + name)
    runtime = repair.load_module("public_header_probe_signature_runtime", repair.HYGIENE / "run_scan.py")
    for name, parameters in {"docker_run": ("name", "image", "memory", "parent", "options", "command"),
                             "stop": ("name",), "image_receipt": ("image",)}.items():
        if tuple(inspect.signature(getattr(runtime, name)).parameters) != parameters:
            raise RuntimeError("scanner runtime helper signature changed: " + name)


def preflight(repair):
    """Read-only fail-closed validation before the parent reserves a slice."""
    repair.require_stopped_confirmation(repair.SUMMARY)
    validate_helper_signatures(repair)
    verify_tool_receipt(repair)
    row, mounts, proof, capture_paths = captured_context(repair)
    baseline = baseline_counts()
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    if digest(plugin) != repair.PACKAGES[plugin.name][1]:
        raise RuntimeError("pinned Sonar CXX plugin changed")
    temporary = repair.probe_temporary_accounting()
    return row, mounts, proof, capture_paths, baseline, temporary, identities(repair, capture_paths)


def record_early_failure(out: Path, repair, stage: str, error: Exception) -> None:
    """Retain a bounded terminal outcome even if preflight fails before a server."""
    if (out / "result.json").exists():
        return
    try:
        budget = repair.EvidenceBudget(out)
        if not out.exists(): budget.mkdir(out)
        raw = out / "raw"
        if not raw.exists(): budget.mkdir(raw, failure=True)
        repair.save(raw / "early-failure.json", {"stage": stage, "error": str(error),
                    "runner_sha256": digest(Path(__file__))}, budget, failure=True)
        repair.save_terminal_result(out / "result.json", {"status": "FAILED_BEFORE_SERVER",
                    "stage": stage, "error": str(error)}, budget)
    except Exception:
        pass


def execute(out: Path) -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if "cix-cxx-hygiene.slice" not in Path("/proc/self/cgroup").read_text():
        raise RuntimeError("worker is outside root's exclusive CXX hygiene slice")
    if out.exists():
        raise RuntimeError("refusing to overwrite a public-header probe attempt")
    repair = load("public_header_probe_repair", ROOT / "tools/sonar-cxx/repair.py")
    row, mounts, proof, capture_paths, baseline, temporary, before = preflight(repair)
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    h = repair.load_module("public_header_probe_runtime", repair.HYGIENE / "run_scan.py")
    budget = repair.EvidenceBudget(out); budget.mkdir(out); raw = out / "raw"; budget.mkdir(raw)
    repair.save(raw / "identities.json", before, budget)
    repair.save(raw / "baseline.json", {"parser_recovery": baseline}, budget)
    repair.save(raw / "context-proof.json", proof, budget)
    budget.mkdir(raw / "capture"); budget.mkdir(raw / "source")
    for name, path in capture_paths.items(): budget.write_bytes(raw / "capture" / name, path.read_bytes())
    for source in (HEADER, OWNER):
        destination = raw / "source" / source
        if not destination.parent.exists():
            budget.mkdir(destination.parent)
        budget.write_bytes(destination, (ROOT / source).read_bytes())
    repair.save(raw / "temporary-accounting.json", temporary, budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    extensions = repair.prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, token, password, envfile = "http://127.0.0.1:9017", None, "Aa1!" + repair.secrets.token_urlsafe(32), raw / ".scanner-env"
    results = {"status": "STARTED", "kind": "ROCKSDB_PUBLIC_HEADER_FULL_INCLUDE_CONTEXT_PROBE_V4", "headers": [HEADER],
               "baseline_parser_recovery": baseline,
               "gio": "untouched; known direct-header C++ parser limitation retained",
               "blosc": "v2 parser recovery already reached zero; this v3 isolates RocksDB"}
    options, command, contract = repair.server_start_contract(); repair.save(raw / "server-start-contract.json", contract, budget)
    try:
        h.docker_run(SERVER, h.SERVER_IMAGE, h.SERVER_MEMORY, "cix-cxx-hygiene.slice", [
            "-p", "127.0.0.1:9017:9000", *options,
            "-v", f"{extensions}:/opt/sonarqube/lib/extensions:ro",
            "-v", f"{plugin}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"], command)
        repair.wait_server_or_exit(h, base, password, SERVER)
        if "cxx" not in {row["key"] for row in repair.request(h, base, password, "/api/languages/list")["languages"]}:
            raise RuntimeError("CXX sensor is unavailable")
        repair.profile(h, base, password, raw, budget)
        token = repair.request(h, base, password, "/api/user_tokens/generate", {"name": "cix-public-header-context-v3"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"; budget.admit(envfile, len(credentials.encode()))
        descriptor = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream: stream.write(credentials)
        target = out / "rocks-full-context"; budget.mkdir(target)
        repair.save(target / "compile_commands.json", [row], budget)
        budget.write_text(target / "properties", "\n".join([
            "sonar.projectKey=cix-cxx-adapter-public-header-context-v3",
            "sonar.sources=" + HEADER, "sonar.sourceEncoding=UTF-8",
            "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true", "sonar.working.directory=/tmp/.scannerwork",
            "sonar.cxx.file.suffixes=.h,.hh,.hpp,.hxx", "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json", ""]))
        task = repair.bounded_scanner(h, base, password, token, envfile, "cix-cxx-hygiene.slice", target.name,
                                      ROOT, target, budget, mounts)
        repair.collect(h, base, "cix-cxx-adapter-public-header-context-v3", task, password, target, budget)
        components = repair.request(h, base, password, "/api/components/tree?component=cix-cxx-adapter-public-header-context-v3&qualifiers=FIL&ps=500&p=1")["components"]
        repair.save(target / "indexed-files.json", components, budget); repair.validate_indexed([HEADER], components, (target / "scanner.log").read_text())
        issues = json.loads((target / "issues.json").read_text())["issues"]
        actual = {header: sum(row.get("rule") == "cxx:ParsingErrorRecovery" and row.get("component", "").endswith(header) for row in issues) for header in (HEADER,)}
        results.update(status="PROBE_COMPLETED_NOT_FULL_SCAN_QUALIFICATION", actual_parser_recovery=actual,
                       rules=dict(collections.Counter(row["rule"] for row in issues)), issues=len(issues))
        if before != identities(repair, capture_paths): raise RuntimeError("capture, headers, tools, or plugin changed during probe")
    except Exception as error:
        results.update(status="FAILED", error=h.scrub(str(error), [password, token])); raise
    finally:
        try:
            if token:
                try: repair.request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-public-header-context-v3"})
                except Exception: results["token_revocation"] = "failed; ephemeral server removed"
            if envfile.exists(): envfile.unlink()
            budget.write_text(raw / "server.log", repair.bounded_server_log(SERVER, budget, h, [password, token]), failure=True)
        finally:
            try: h.stop(SERVER)
            finally: repair.save_terminal_result(out / "result.json", results, budget)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("run", "worker"))
    parser.add_argument("--out", type=Path, required=True); args = parser.parse_args()
    out = args.out.resolve()
    repair = load("public_header_probe_entry", ROOT / "tools/sonar-cxx/repair.py")
    if args.action == "worker":
        try:
            execute(out)
        except Exception as error:
            record_early_failure(out, repair, "worker-preflight-or-setup", error)
            raise
        return
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if out.exists():
        raise RuntimeError("refusing to overwrite a public-header probe attempt")
    # This parent performs only read-only gate checks before it reserves the
    # existing exclusive helper's slice. It never calls an ordinary scheduler.
    try:
        preflight(repair)
    except Exception as error:
        record_early_failure(out, repair, "parent-preflight", error)
        raise
    scheduler_module = repair.load_module("public_header_probe_scheduler", repair.HYGIENE / "schedule_scan.py")
    scheduler = scheduler_module.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=12_000_000_000,
                                                max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True); parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [scheduler_module._core(cpu) for cpu in scheduler_module.CPUS]}])
        try:
            repair.assert_benchmark_idle(); scheduler_module._make_slice(parent, anchor)
            slice_receipt = scheduler_module._slice_receipt(parent); scheduler_module._verify_slice(slice_receipt)
            command = ["sudo", "-n", "systemd-run", "--unit", WORKER_UNIT,
                       f"--property=RuntimeMaxSec={WORKER_RUNTIME_SECONDS}s",
                       "--setenv=CIX_RELEASE_LEASE=1",
                       "--uid", str(os.getuid()), "--gid", str(os.getgid()), "--wait", "--pipe", "--collect",
                       "--slice", parent, sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(out)]
            result = subprocess.run(command, timeout=CLIENT_TIMEOUT_SECONDS)
            if out.exists(): repair.EvidenceBudget(out).write_text(out / "slice-receipt.txt", slice_receipt)
            if result.returncode: raise RuntimeError("RocksDB full-context probe failed; retained evidence explains the result")
        finally:
            # All names are unique to this probe. Stop the worker before either
            # container is removed, then release only this helper's anchor.
            subprocess.run(["sudo", "-n", "systemctl", "stop", WORKER_UNIT], check=False, capture_output=True, timeout=30)
            for container in (SCANNER, SERVER):
                subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True, timeout=30)
            subprocess.run(["sudo", "-n", "systemctl", "reset-failed", WORKER_UNIT], check=False, capture_output=True, timeout=30)
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True, timeout=30)
            for lease in leases: lease.close()


if __name__ == "__main__": main()
