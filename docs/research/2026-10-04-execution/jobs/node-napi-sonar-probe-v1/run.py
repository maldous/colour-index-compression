#!/usr/bin/env python3
"""Bounded Sonar probe for the captured Node N-API C translation unit.

This analyzer-only probe preserves the receipt-bound Node command and applies
only the captured GNU visibility normalization. It uses the established
exclusive lifecycle; it never builds the Node add-on.
"""
from __future__ import annotations
import argparse, collections, fcntl, hashlib, importlib.util, inspect, json, os, subprocess, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
CAPTURE = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/node-napi-context-probe-v1"
BASELINE = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/adapter-context-probe-v2/adapter/issues.json"
TOOL_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/sonar-tool-tests-v18/receipt.json"
SOURCE = "rust/cix-native/bindings/node/src/cix_node.c"
SDK = ROOT / "benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8/include"
NODE_HEADERS = Path("/usr/include/node")
EXPECTED = {SOURCE: 3}
SERVER = "cix-cxx-node-napi-probe-v1"
SCANNER = "cix-hygiene-scanner-node-napi"
WORKER_UNIT = "cix-cxx-node-napi-probe-v1.service"
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
              for header in (SOURCE,)}
    if counts != EXPECTED:
        raise RuntimeError("retained Node parser baseline changed: " + repr(counts))
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
    """Return the exact captured Node C row and its explicit RO mounts."""
    receipt_path = CAPTURE / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError("Node compiler-context receipt is absent")
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("status") != "captured_no_analyzer_run" or receipt.get("input_sha256") != receipt.get("input_sha256_after"):
        raise RuntimeError("Node compiler-context receipt is incomplete or unstable")
    capture_inputs = receipt.get("input_sha256")
    if not isinstance(capture_inputs, dict) or not capture_inputs:
        raise RuntimeError("Node compiler-context receipt has no input identities")
    for recorded_path, expected_sha in capture_inputs.items():
        path = Path(recorded_path)
        if not path.is_absolute():
            path = ROOT / path
        if not isinstance(expected_sha, str) or not path.is_file() or digest(path) != expected_sha:
            raise RuntimeError("Node capture input differs from receipt: " + recorded_path)
    command = receipt.get("command")
    expected = ["/usr/bin/cc", "-DNAPI_VERSION=8", "-Dcix_node_EXPORTS", "-I/mnt", "-I/usr/include/node", "-fPIC", "-fvisibility=hidden", "-c", "/usr/src/" + SOURCE]
    if command != expected:
        raise RuntimeError("Node captured compiler row differs from the reviewed command")
    raw = CAPTURE / "raw"
    for name in ("effective-macros.stdout", "include-trace.stderr", "registration-expansion.stdout"):
        if not (raw / name).is_file():
            raise RuntimeError("Node capture lacks " + name)
    tokens = receipt.get("registration_tokens_present")
    required = ("node_api_module_get_api_version_v1", "napi_register_module_v1", "return init(env, exports)")
    if not isinstance(tokens, dict) or any(tokens.get(token) is not True for token in required):
        raise RuntimeError("Node capture does not prove expected registration expansion")
    headers = receipt.get("effective_node_header_sha256")
    if not isinstance(headers, dict) or not headers:
        raise RuntimeError("Node capture lacks effective header identities")
    for raw_path, expected_sha in headers.items():
        path = Path(raw_path)
        if not path.is_file() or digest(path) != expected_sha:
            raise RuntimeError("Node effective header differs from capture: " + raw_path)
    if not SDK.is_dir() or not NODE_HEADERS.is_dir():
        raise RuntimeError("Node SDK or Node header include root is absent")
    mounts = [(SDK, "/mnt"), (NODE_HEADERS, "/usr/include/node")]
    row = {"directory": "/usr/src/rust/cix-native/bindings/node", "file": "/usr/src/" + SOURCE,
           "arguments": ["/usr/bin/cc", "-DNAPI_VERSION=8", "-Dcix_node_EXPORTS", "-D__attribute__(...)=",
                         "-I/mnt", "-I/usr/include/node", "-fPIC", "-fvisibility=hidden", "-c", "/usr/src/" + SOURCE]}
    proof = {"source": SOURCE, "source_sha256": digest(ROOT / SOURCE),
             "capture_receipt_sha256": digest(receipt_path), "captured_command": command,
             "header_sha256": headers,
             "read_only_include_mounts": [{"host": str(host), "container": container} for host, container in mounts],
             "normalization": {"define": "__attribute__(...)", "replacement": "",
                               "scope": "analyzer-only GNU visibility syntax normalization; no source, ABI, or API alteration"},
             "required_registration_tokens": list(required)}
    return row, mounts, proof, {"receipt.json": receipt_path, **{name: raw / name for name in ("effective-macros.stdout", "include-trace.stderr", "registration-expansion.stdout")}}


def identities(repair, capture_paths: dict[str, Path]) -> dict:
    values = {str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
              str(BASELINE.relative_to(ROOT)): digest(BASELINE),
              str(TOOL_RECEIPT.relative_to(ROOT)): digest(TOOL_RECEIPT)}
    for path in capture_paths.values(): values[str(path.relative_to(ROOT))] = digest(path)
    values[SOURCE] = digest(ROOT / SOURCE)
    values[str(SDK.relative_to(ROOT)) + "/cix.h"] = digest(SDK / "cix.h")
    for path in sorted(NODE_HEADERS.glob("*.h")): values["external:" + str(path)] = digest(path)
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
    runtime = repair.load_module("node_napi_probe_signature_runtime", repair.HYGIENE / "run_scan.py")
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
        raise RuntimeError("refusing to overwrite a Node N-API probe attempt")
    repair = load("node_napi_probe_repair", ROOT / "tools/sonar-cxx/repair.py")
    row, mounts, proof, capture_paths, baseline, temporary, before = preflight(repair)
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    h = repair.load_module("node_napi_probe_runtime", repair.HYGIENE / "run_scan.py")
    budget = repair.EvidenceBudget(out); budget.mkdir(out); raw = out / "raw"; budget.mkdir(raw)
    repair.save(raw / "identities.json", before, budget)
    repair.save(raw / "baseline.json", {"parser_recovery": baseline}, budget)
    repair.save(raw / "context-proof.json", proof, budget)
    budget.mkdir(raw / "capture"); budget.mkdir(raw / "source")
    for name, path in capture_paths.items(): budget.write_bytes(raw / "capture" / name, path.read_bytes())
    destination = raw / "source" / SOURCE
    budget.mkdir(destination.parent)
    budget.write_bytes(destination, (ROOT / SOURCE).read_bytes())
    repair.save(raw / "temporary-accounting.json", temporary, budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    extensions = repair.prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, token, password, envfile = "http://127.0.0.1:9017", None, "Aa1!" + repair.secrets.token_urlsafe(32), raw / ".scanner-env"
    results = {"status": "STARTED", "kind": "NODE_NAPI_TRANSLATION_UNIT_CONTEXT_PROBE_V1", "sources": [SOURCE],
               "baseline_parser_recovery": baseline,
               "normalization": "captured analyzer-only __attribute__(...)=",
               "scope": "one Node C translation unit; no product build or full-scan qualification"}
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
        token = repair.request(h, base, password, "/api/user_tokens/generate", {"name": "cix-node-napi-probe-v1"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"; budget.admit(envfile, len(credentials.encode()))
        descriptor = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream: stream.write(credentials)
        target = out / "node-napi"; budget.mkdir(target)
        repair.save(target / "compile_commands.json", [row], budget)
        budget.write_text(target / "properties", "\n".join([
            "sonar.projectKey=cix-cxx-node-napi-probe-v1",
            "sonar.sources=" + SOURCE, "sonar.sourceEncoding=UTF-8",
            "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true", "sonar.working.directory=/tmp/.scannerwork",
            "sonar.cxx.file.suffixes=.c,.cc,.cpp,.cxx,.h,.hh,.hpp,.hxx", "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json", ""]))
        task = repair.bounded_scanner(h, base, password, token, envfile, "cix-cxx-hygiene.slice", target.name,
                                      ROOT, target, budget, mounts)
        repair.collect(h, base, "cix-cxx-node-napi-probe-v1", task, password, target, budget)
        components = repair.request(h, base, password, "/api/components/tree?component=cix-cxx-node-napi-probe-v1&qualifiers=FIL&ps=500&p=1")["components"]
        repair.save(target / "indexed-files.json", components, budget); repair.validate_indexed([SOURCE], components, (target / "scanner.log").read_text())
        issues = json.loads((target / "issues.json").read_text())["issues"]
        actual = {header: sum(row.get("rule") == "cxx:ParsingErrorRecovery" and row.get("component", "").endswith(header) for row in issues) for header in (SOURCE,)}
        results.update(status="PROBE_COMPLETED_NOT_FULL_SCAN_QUALIFICATION", actual_parser_recovery=actual,
                       rules=dict(collections.Counter(row["rule"] for row in issues)), issues=len(issues))
        if before != identities(repair, capture_paths): raise RuntimeError("capture, headers, tools, or plugin changed during probe")
    except Exception as error:
        results.update(status="FAILED", error=h.scrub(str(error), [password, token])); raise
    finally:
        try:
            if token:
                try: repair.request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-node-napi-probe-v1"})
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
    repair = load("node_napi_probe_entry", ROOT / "tools/sonar-cxx/repair.py")
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
        raise RuntimeError("refusing to overwrite a Node N-API probe attempt")
    # This parent performs only read-only gate checks before it reserves the
    # existing exclusive helper's slice. It never calls an ordinary scheduler.
    try:
        preflight(repair)
    except Exception as error:
        record_early_failure(out, repair, "parent-preflight", error)
        raise
    scheduler_module = repair.load_module("node_napi_probe_scheduler", repair.HYGIENE / "schedule_scan.py")
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
            if result.returncode: raise RuntimeError("Node N-API context probe failed; retained evidence explains the result")
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
