#!/usr/bin/env python3
"""Bounded Sonar CXX probe for one original header with measured JXL context."""
from __future__ import annotations

import argparse
import collections
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse


ROOT = Path(__file__).resolve().parents[2]
HEADER = "rust/cix-native/codecs/jxl/cix_jxl_bridge.h"
CONTEXT = ROOT / "docs/research/2026-10-04-execution/jobs/compiler-context-capture-v1/context.json"
QUALIFIED = ROOT / "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1/receipt.json"
PRIOR_ISSUES = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/scan-v3/cix-native-core/issues.json"
PRIOR_RECOVERIES = 13
CONTEXT_PARSER = ROOT / "tools/sonar-cxx/compiler_context.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repair_module():
    path = Path(__file__).with_name("repair.py")
    spec = importlib.util.spec_from_file_location("cix_header_repair", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def context_module():
    spec = importlib.util.spec_from_file_location("cix_header_context", CONTEXT_PARSER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def identity_key(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def current_identities(repair) -> dict[str, str]:
    paths = (Path(__file__), Path(__file__).with_name("repair.py"), CONTEXT_PARSER,
             CONTEXT, CONTEXT.parent / "macros.txt", CONTEXT.parent / "compiler-verbose.txt",
             QUALIFIED, QUALIFIED.parent / "build/compile_commands.json", PRIOR_ISSUES, ROOT / HEADER,
             repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar")
    return {identity_key(path): sha256(path) for path in paths}


def gnu_visibility_normalization(header_text: str, defines: dict[str, str]) -> dict[str, str]:
    """Return the one allowed analyzer-only GNU visibility normalization.

    This does not alter a header or describe an ABI.  It is deliberately
    restricted to the exact Linux spelling in the retained JXL header so that
    a probe cannot silently grow into general compiler-extension handling.
    """
    expected = '#  define CIX_JXL_API __attribute__((visibility("default")))'
    if header_text.count("__attribute__") != 1 or expected not in header_text:
        raise RuntimeError("JXL header no longer has exactly the measured GNU visibility definition")
    if "_WIN32" in defines or "__linux__" not in defines:
        raise RuntimeError("GNU visibility normalization requires the captured non-Windows Linux context")
    normalized = dict(defines)
    normalized["__attribute__(...)"] = ""
    return normalized


def measured_context(repair, normalize_gnu_visibility: bool = False) -> tuple[dict, list[tuple[Path, str]], dict]:
    context = json.loads(CONTEXT.read_text())
    receipt = json.loads(QUALIFIED.read_text())
    provenance = context["provenance"]
    header = ROOT / HEADER
    expected = receipt["source_sha256"]["cix_jxl_bridge.h"]
    if receipt["status"] != "pass" or not receipt["source_unchanged"]:
        raise RuntimeError("qualified JXL receipt is not a successful immutable source receipt")
    if repair.digest(header) != expected:
        raise RuntimeError("original JXL header differs from the qualified receipt")
    if provenance.get("qualified_receipt_sha256") != sha256(QUALIFIED):
        raise RuntimeError("captured context is not bound to this qualified JXL receipt")
    database = QUALIFIED.parent / "build/compile_commands.json"
    if provenance.get("compile_database_sha256") != sha256(database):
        raise RuntimeError("captured context is not bound to the qualified JXL compile database")
    macro_file, verbose_file = CONTEXT.parent / "macros.txt", CONTEXT.parent / "compiler-verbose.txt"
    if (provenance.get("macro_stdout_sha256") != sha256(macro_file)
            or provenance.get("include_stderr_sha256") != sha256(verbose_file)):
        raise RuntimeError("captured macro or include evidence differs from its recorded hash")
    parsed = context_module().parse_compiler_output(macro_file.read_text(), verbose_file.read_text())
    if parsed["macros"] != context.get("macros") or parsed["system_include_paths"] != context.get("system_include_paths"):
        raise RuntimeError("context JSON does not reproduce its retained compiler output")
    if not context.get("preserves_compiler_macros") or not context.get("does_not_infer_header_guard_macros"):
        raise RuntimeError("compiler context does not preserve the required capture contract")
    defines = {row["name"]: row["value"] for row in context.get("macros", [])}
    if len(defines) != context.get("raw_macro_count") or "__cplusplus" not in defines:
        raise RuntimeError("captured C++ macro context is incomplete")
    if "CIX_JXL_BRIDGE_H" in defines:
        raise RuntimeError("captured empty-input context contains the target header guard")
    roots = [Path(value) for value in context.get("system_include_paths", [])]
    if len(roots) != 8 or any(not root.is_absolute() or not root.is_dir() for root in roots):
        raise RuntimeError("captured include roots are not the eight readable absolute JXL roots")
    mounts = [(root, f"/cix-context/{index}") for index, root in enumerate(roots)]
    normalization = None
    if normalize_gnu_visibility:
        defines = gnu_visibility_normalization(header.read_text(), defines)
        normalization = {
            "enabled": True,
            "kind": "analyzer_only_per_file_preprocessor_normalization",
            "define": "__attribute__(...)",
            "replacement": "",
            "source_header_sha256": expected,
            "validated_source_definition": '#  define CIX_JXL_API __attribute__((visibility("default")))',
            "validated_linux_context": True,
            "abi_or_layout_claim": "none",
        }
    row = {
        "file": "/usr/src/" + HEADER,
        "directory": "/usr/src",
        # This is a context carrier, not a fictional compiler command for a header.
        "defines": defines,
        "includes": [destination for _, destination in mounts],
    }
    record = {
        "context_sha256": sha256(CONTEXT),
        "qualified_receipt_sha256": sha256(QUALIFIED),
        "header_sha256": expected,
        "previous_recovery_count": prior_recovery_count(),
        "context_provenance": provenance,
        "macro_count": len(defines),
        "include_mounts": [{"host": str(root), "container": destination} for root, destination in mounts],
        "analyzer_only_normalization": normalization,
    }
    return row, mounts, record


def prior_recovery_count() -> int:
    issues = json.loads(PRIOR_ISSUES.read_text())["issues"]
    count = sum(row.get("rule") == "cxx:ParsingErrorRecovery" and row.get("component", "").endswith(HEADER)
                for row in issues)
    if count != PRIOR_RECOVERIES:
        raise RuntimeError(f"retained scan-v3 JXL recovery count changed: {count}")
    return count


def scan_header(repair, h, base: str, password: str, token: str, envfile: Path,
                parent: str, out: Path, budget, normalize_gnu_visibility: bool = False) -> dict:
    budget.mkdir(out)
    row, mounts, context_record = measured_context(repair, normalize_gnu_visibility)
    repair.save(out / "compile_commands.json", [row], budget)
    repair.save(out / "context.json", context_record, budget)
    key = "cix-cxx-header-context-jxl"
    budget.write_text(out / "properties", "\n".join([
        f"sonar.projectKey={key}", f"sonar.sources={HEADER}", "sonar.sourceEncoding=UTF-8",
        "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true",
        "sonar.working.directory=/tmp/.scannerwork",
        "sonar.cxx.file.suffixes=.h,.hh,.hpp,.hxx",
        "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json", "",
    ]))
    task = repair.bounded_scanner(h, base, password, token, envfile, parent,
                                  "cxx-header-context-jxl", ROOT, out, budget, mounts)
    repair.collect(h, base, key, task, password, out, budget)
    components = repair.request(h, base, password,
        f"/api/components/tree?component={urllib.parse.quote(key)}&qualifiers=FIL&ps=500&p=1")["components"]
    repair.save(out / "indexed-files.json", components, budget)
    repair.validate_indexed([HEADER], components, (out / "scanner.log").read_text())
    issues = json.loads((out / "issues.json").read_text())["issues"]
    current = sum(row.get("rule") == "cxx:ParsingErrorRecovery" for row in issues)
    return {"status": "SCANNED_WITH_RECORDED_FINDINGS", "indexed_header": HEADER,
            "normalize_gnu_visibility": normalize_gnu_visibility,
            "previous_parsing_error_recovery": PRIOR_RECOVERIES,
            "actual_parsing_error_recovery": current, "issues": len(issues),
            "rules": dict(collections.Counter(row["rule"] for row in issues)),
            "quality_gate": json.loads((out / "quality-gate.json").read_text())}


def replay_input_copies(raw: Path, budget) -> None:
    """Retain the executing tool and exact header for later identity replay."""
    tool = Path(__file__)
    tool_copy = raw / "tool" / tool.name
    source_copy = raw / "source" / HEADER
    budget.mkdir(tool_copy.parent)
    budget.mkdir(source_copy.parent)
    budget.write_bytes(tool_copy, tool.read_bytes())
    budget.write_bytes(source_copy, (ROOT / HEADER).read_bytes())


def execute(out: Path, parent: str, normalize_gnu_visibility: bool = False) -> None:
    repair = repair_module()
    h = repair.load_module("cix_header_runtime", repair.HYGIENE / "run_scan.py")
    repair.require_stopped_confirmation(repair.SUMMARY)
    repair.probe_temporary_accounting()
    budget = repair.EvidenceBudget(out)
    budget.mkdir(out); raw = out / "raw"; budget.mkdir(raw)
    plugin = repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar"
    expected_plugin = repair.PACKAGES[plugin.name][1]
    if sha256(plugin) != expected_plugin:
        raise RuntimeError("pinned Sonar CXX plugin changed")
    identities = current_identities(repair)
    repair.save(raw / "identities.json", identities, budget)
    replay_input_copies(raw, budget)
    repair.save(raw / "temporary-accounting.json", repair.probe_temporary_accounting(), budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    extensions = repair.prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, server, token = "http://127.0.0.1:9017", "cix-cxx-header-context-jxl", None
    password, envfile = "Aa1!" + repair.secrets.token_urlsafe(32), raw / ".scanner-env"
    results = {"status": "STARTED", "kind": "ORIGINAL_JXL_HEADER_CONTEXT_PROBE",
               "normalize_gnu_visibility": normalize_gnu_visibility}
    options, command, contract = repair.server_start_contract(); repair.save(raw / "server-start-contract.json", contract, budget)
    try:
        h.docker_run(server, h.SERVER_IMAGE, h.SERVER_MEMORY, parent, [
            "-p", "127.0.0.1:9017:9000", *options,
            "-v", f"{extensions}:/opt/sonarqube/lib/extensions:ro",
            "-v", f"{repair.TOOLS / 'sonar-cxx-plugin-2.3.0.1496.jar'}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"], command)
        repair.wait_server_or_exit(h, base, password, server)
        if "cxx" not in {row["key"] for row in repair.request(h, base, password, "/api/languages/list")["languages"]}:
            raise RuntimeError("CXX sensor is unavailable")
        repair.profile(h, base, password, raw, budget)
        token = repair.request(h, base, password, "/api/user_tokens/generate", {"name": "cix-header-context"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"
        budget.admit(envfile, len(credentials.encode()))
        descriptor = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(credentials)
        results["probe"] = scan_header(repair, h, base, password, token, envfile, parent,
                                       out / "header", budget, normalize_gnu_visibility)
        if identities != current_identities(repair):
            raise RuntimeError("header, context, tool, or plugin changed during the canary")
        results["status"] = "PROBE_COMPLETED_NOT_QUALIFICATION"
    except Exception as error:
        results.update(status="FAILED", error=h.scrub(str(error), [password, token])); raise
    finally:
        try:
            if token:
                try: repair.request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-header-context"})
                except Exception: results["token_revocation"] = "failed; ephemeral server removed"
            if envfile.exists(): envfile.unlink()
            budget.write_text(raw / "server.log", repair.bounded_server_log(server, budget, h, [password, token]), failure=True)
        finally:
            try: h.stop(server)
            finally: repair.save_terminal_result(out / "result.json", results, budget)


def worker_arguments(out: Path, normalize_gnu_visibility: bool) -> list[str]:
    arguments = [sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(out)]
    if normalize_gnu_visibility:
        arguments.append("--normalize-gnu-visibility")
    return arguments


def run(out: Path, normalize_gnu_visibility: bool = False) -> None:
    repair = repair_module(); repair.require_stopped_confirmation(repair.SUMMARY)
    if out.exists(): raise RuntimeError("refusing to overwrite a probe attempt")
    scheduler_module = repair.load_module("cix_header_scheduler", repair.HYGIENE / "schedule_scan.py")
    scheduler = scheduler_module.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=12_000_000_000,
                                                max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True); parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [scheduler_module._core(cpu)
                                                               for cpu in scheduler_module.CPUS]}])
        try:
            repair.assert_benchmark_idle()
            scheduler_module._make_slice(parent, anchor)
            receipt = scheduler_module._slice_receipt(parent)
            scheduler_module._verify_slice(receipt)
            result = subprocess.run(["sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()), "--wait", "--pipe", "--collect", "--slice", parent, *worker_arguments(out, normalize_gnu_visibility)], timeout=21600)
            if out.exists(): repair.EvidenceBudget(out).write_text(out / "slice-receipt.txt", receipt)
            if result.returncode: raise RuntimeError("header context probe failed; retained evidence explains the result")
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True)
            for lease in leases: lease.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("run", "worker")); parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--normalize-gnu-visibility", action="store_true",
                        help="normalize only the measured per-file GNU visibility attribute for this JXL header probe")
    args = parser.parse_args()
    if args.action == "run": run(args.out.resolve(), args.normalize_gnu_visibility)
    else:
        if "cix-cxx-hygiene.slice" not in Path("/proc/self/cgroup").read_text(): raise RuntimeError("worker is outside the reserved aggregate slice")
        execute(args.out.resolve(), "cix-cxx-hygiene.slice", args.normalize_gnu_visibility)


if __name__ == "__main__": main()
