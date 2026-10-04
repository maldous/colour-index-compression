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
BRIDGE_CAPTURE = ROOT / "benchmark-work/native-rc-check-v1/bridge-header-context-v1"
BRIDGE_HEADERS = (
    "rust/cix-native/codecs/jxl/cix_jxl_bridge.h",
    "rust/cix-native/codecs/spatial/cix_spatial_bridge.h",
    "rust/cix-native/codecs/paq/v215/paq_v215_bridge.h",
    "rust/cix-native/codecs/paq/v216/paq_v216_bridge.h",
    "rust/cix-native/codecs/paq/joint_discount/paq_joint_discount_bridge.h",
    "rust/cix-native/codecs/paq/store_state/paq_store_state_bridge.h",
)
BRIDGE_PRIOR_RECOVERIES = {
    BRIDGE_HEADERS[0]: 13,
    BRIDGE_HEADERS[1]: 10,
    BRIDGE_HEADERS[2]: 4,
    BRIDGE_HEADERS[3]: 4,
    BRIDGE_HEADERS[4]: 4,
    BRIDGE_HEADERS[5]: 4,
}
BRIDGE_NAMES = {
    BRIDGE_HEADERS[0]: "jxl",
    BRIDGE_HEADERS[1]: "spatial",
    BRIDGE_HEADERS[2]: "paq-v215",
    BRIDGE_HEADERS[3]: "paq-v216",
    BRIDGE_HEADERS[4]: "paq-joint-discount",
    BRIDGE_HEADERS[5]: "paq-store-state",
}


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


def current_identities(repair, bridge_context_directory: Path | None = None) -> dict[str, str]:
    paths = (Path(__file__), Path(__file__).with_name("repair.py"), CONTEXT_PARSER,
             CONTEXT, CONTEXT.parent / "macros.txt", CONTEXT.parent / "compiler-verbose.txt",
             QUALIFIED, QUALIFIED.parent / "build/compile_commands.json", PRIOR_ISSUES, ROOT / HEADER,
             repair.TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar")
    if bridge_context_directory is not None:
        paths += (bridge_context_directory / "context.json", bridge_context_directory / "receipt.json",
                  bridge_context_directory / "include-mappings.json")
        for header in BRIDGE_HEADERS:
            paths += (ROOT / header,)
        for name in ("jxl", "spatial", "paq-v215", "paq-v216", "paq-joint-discount", "paq-store-state"):
            paths += (bridge_context_directory / "raw" / name / "macros.txt",
                      bridge_context_directory / "raw" / name / "compiler-verbose.txt")
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


def bridge_prior_recovery_counts() -> dict[str, int]:
    """Require the retained scan-v3 baseline for exactly the six bridge headers."""
    issues = json.loads(PRIOR_ISSUES.read_text())["issues"]
    counts = {
        header: sum(row.get("rule") == "cxx:ParsingErrorRecovery"
                    and row.get("component", "").endswith(header) for row in issues)
        for header in BRIDGE_HEADERS
    }
    if counts != BRIDGE_PRIOR_RECOVERIES:
        raise RuntimeError("retained scan-v3 bridge recovery counts changed: " + repr(counts))
    return counts


def measured_bridge_contexts(repair, directory: Path) -> tuple[list[dict], list[tuple[Path, str]], dict]:
    """Verify the completed six-bridge capture and construct its per-file rows."""
    directory = directory.resolve()
    files = {
        "context": directory / "context.json",
        "receipt": directory / "receipt.json",
        "include_mappings": directory / "include-mappings.json",
    }
    if not all(path.is_file() for path in files.values()):
        raise RuntimeError("bridge context directory lacks completed context, receipt, or include mappings")
    context, receipt, mappings = (json.loads(path.read_text()) for path in files.values())
    if receipt.get("status") != "captured_no_analyzer_run" or receipt.get("sonar_or_cppcheck_started") is not False:
        raise RuntimeError("bridge context receipt is not a completed capture-only receipt")
    before, after = receipt.get("input_sha256_before"), receipt.get("input_sha256_after")
    if not isinstance(before, dict) or before != after:
        raise RuntimeError("bridge context receipt does not prove unchanged capture inputs")
    if receipt.get("context_sha256") != sha256(files["context"]):
        raise RuntimeError("bridge context receipt does not bind context.json")
    if receipt.get("include_mappings_sha256") != sha256(files["include_mappings"]):
        raise RuntimeError("bridge context receipt does not bind include-mappings.json")
    if not isinstance(context.get("entries"), list) or not isinstance(mappings, list):
        raise RuntimeError("bridge context evidence has an invalid entry or mapping collection")
    entries = {entry.get("header"): entry for entry in context["entries"] if isinstance(entry, dict)}
    mapping_by_header = {entry.get("header"): entry for entry in mappings if isinstance(entry, dict)}
    if set(entries) != set(BRIDGE_HEADERS) or set(mapping_by_header) != set(BRIDGE_HEADERS):
        raise RuntimeError("bridge context evidence does not cover exactly the six owned headers")

    rows, mounts, context_records = [], [], []
    for header in BRIDGE_HEADERS:
        entry, mapping = entries[header], mapping_by_header[header]
        if entry.get("name") != BRIDGE_NAMES[header] or mapping.get("bridge") != BRIDGE_NAMES[header]:
            raise RuntimeError("bridge context entry has the wrong bridge identity: " + header)
        expected = entry.get("header_sha256")
        if not isinstance(expected, str) or repair.digest(ROOT / header) != expected:
            raise RuntimeError("current bridge header differs from the completed capture: " + header)
        if before.get(header) != expected:
            raise RuntimeError("bridge receipt does not bind the captured header: " + header)
        raw = directory / "raw" / entry.get("name", "")
        calls = [row for row in receipt.get("compiler_calls", [])
                 if isinstance(row, dict) and row.get("bridge") == entry.get("name")]
        if len(calls) != 1 or calls[0].get("returncode") != 0:
            raise RuntimeError("bridge receipt has no successful compiler call: " + header)
        macro, verbose = raw / "macros.txt", raw / "compiler-verbose.txt"
        if (not macro.is_file() or not verbose.is_file()
                or calls[0].get("macro_stdout_sha256") != sha256(macro)
                or calls[0].get("include_stderr_sha256") != sha256(verbose)):
            raise RuntimeError("bridge raw compiler output differs from its receipt: " + header)
        parsed = context_module().parse_compiler_output(macro.read_text(), verbose.read_text())
        captured = entry.get("compiler_context", {})
        if parsed["macros"] != captured.get("macros") or parsed["system_include_paths"] != captured.get("system_include_paths"):
            raise RuntimeError("bridge raw compiler output does not reproduce its context: " + header)
        guard = next((line.split()[1] for line in (ROOT / header).read_text().splitlines()
                      if line.startswith("#ifndef ")), None)
        if not guard or guard in {item["name"] for item in parsed["macros"]}:
            raise RuntimeError("bridge compiler context is polluted by its header guard: " + header)
        values = mapping.get("include_paths")
        expected_roots = parsed["system_include_paths"]
        if not isinstance(values, list) or len(values) != len(expected_roots):
            raise RuntimeError("bridge include mapping has the wrong root count: " + header)
        containers = []
        for index, (value, root) in enumerate(zip(values, expected_roots)):
            if not isinstance(value, dict):
                raise RuntimeError("bridge include mapping entry is not an object: " + header)
            host, container = value.get("host"), value.get("container")
            expected_container = f"/cix-context/{entry['name']}/{index}"
            if (host != root or container != expected_container or not Path(root).is_absolute()
                    or not Path(root).is_dir()):
                raise RuntimeError("bridge include mapping is not a readable exact root: " + header)
            mounts.append((Path(root), container))
            containers.append(container)
        row = entry.get("sonar_per_file")
        if (not isinstance(row, dict) or row.get("file") != "/usr/src/" + header
                or row.get("directory") != "/usr/src" or row.get("includes") != containers):
            raise RuntimeError("bridge context lacks its per-file Sonar row: " + header)
        normalized = row.get("defines", {})
        normalization = entry.get("analyzer_only_normalization", {})
        raw_defines = {item["name"]: item["value"] for item in parsed["macros"]}
        expected_defines = {**raw_defines, "__attribute__(...)": ""}
        source_visibility = [line.strip() for line in (ROOT / header).read_text().splitlines()
                             if "__attribute__" in line]
        api_define = normalization.get("api_define")
        expected_tokens = ["#", "define", api_define, '__attribute__((visibility("default")))']
        if (normalized != expected_defines or normalization.get("define") != "__attribute__(...)"
                or normalization.get("replacement") != "" or normalization.get("abi_or_layout_claim") != "none"
                or not isinstance(api_define, str) or len(source_visibility) != 1
                or normalization.get("source_definition") != "#define " + api_define
                + ' __attribute__((visibility("default")))'
                or normalization.get("source_header_sha256") != expected
                or source_visibility[0].split() != expected_tokens):
            raise RuntimeError("bridge context has an unapproved analyzer normalization: " + header)
        rows.append({**row, "includes": containers})
        context_records.append({
            "name": entry["name"], "header": header, "header_sha256": expected,
            "compile_database": entry.get("compile_database"),
            "include_mounts": values, "analyzer_only_normalization": normalization,
        })
    if len({container for _, container in mounts}) != len(mounts):
        raise RuntimeError("bridge include mappings reuse a container destination")
    return rows, mounts, {
        "capture_directory": str(directory),
        "capture_context_sha256": sha256(files["context"]),
        "capture_receipt_sha256": sha256(files["receipt"]),
        "capture_include_mappings_sha256": sha256(files["include_mappings"]),
        "previous_recovery_counts": bridge_prior_recovery_counts(),
        "entries": context_records,
    }


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


def scan_bridge_headers(repair, h, base: str, password: str, token: str, envfile: Path,
                        parent: str, out: Path, budget, directory: Path) -> dict:
    """Scan exactly the six captured CIX bridge headers with per-file context."""
    budget.mkdir(out)
    rows, mounts, context_record = measured_bridge_contexts(repair, directory)
    repair.save(out / "compile_commands.json", rows, budget)
    repair.save(out / "context.json", context_record, budget)
    key = "cix-cxx-header-context-bridges"
    budget.write_text(out / "properties", "\n".join([
        f"sonar.projectKey={key}", f"sonar.sources={','.join(BRIDGE_HEADERS)}", "sonar.sourceEncoding=UTF-8",
        "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true",
        "sonar.working.directory=/tmp/.scannerwork",
        "sonar.cxx.file.suffixes=.h,.hh,.hpp,.hxx",
        "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json", "",
    ]))
    task = repair.bounded_scanner(h, base, password, token, envfile, parent,
                                  "cxx-header-context-bridges", ROOT, out, budget, mounts)
    repair.collect(h, base, key, task, password, out, budget)
    components = repair.request(h, base, password,
        f"/api/components/tree?component={urllib.parse.quote(key)}&qualifiers=FIL&ps=500&p=1")["components"]
    repair.save(out / "indexed-files.json", components, budget)
    repair.validate_indexed(list(BRIDGE_HEADERS), components, (out / "scanner.log").read_text())
    issues = json.loads((out / "issues.json").read_text())["issues"]
    counts = {
        header: sum(row.get("rule") == "cxx:ParsingErrorRecovery"
                    and row.get("component", "").endswith(header) for row in issues)
        for header in BRIDGE_HEADERS
    }
    return {"status": "SCANNED_WITH_RECORDED_FINDINGS", "indexed_headers": list(BRIDGE_HEADERS),
            "previous_parsing_error_recovery": bridge_prior_recovery_counts(),
            "actual_parsing_error_recovery": counts,
            "actual_parsing_error_recovery_total": sum(counts.values()), "issues": len(issues),
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


def replay_bridge_input_copies(raw: Path, directory: Path, budget) -> None:
    """Retain six original headers and the completed capture's signed inputs."""
    for header in BRIDGE_HEADERS:
        destination = raw / "source" / header
        budget.mkdir(destination.parent)
        budget.write_bytes(destination, (ROOT / header).read_bytes())
    for name in ("context.json", "receipt.json", "include-mappings.json"):
        destination = raw / "bridge-capture" / name
        budget.mkdir(destination.parent)
        budget.write_bytes(destination, (directory / name).read_bytes())


def normalization_metadata(requested_single_header: bool,
                           bridge_context_record: dict | None = None) -> dict:
    """Describe requested and effective analyzer normalization without changing it."""
    if bridge_context_record is None:
        return {
            "requested_single_header_gnu_visibility": requested_single_header,
            "effective_mode": "single_header_gnu_visibility" if requested_single_header else "none",
            "headers": [HEADER] if requested_single_header else [],
        }
    headers = [entry["header"] for entry in bridge_context_record["entries"]]
    return {
        "requested_single_header_gnu_visibility": requested_single_header,
        "effective_mode": "captured_per_file_gnu_visibility",
        "headers": headers,
        "source": "completed_bridge_context_capture",
    }


def execute(out: Path, parent: str, normalize_gnu_visibility: bool = False,
            bridge_context_directory: Path | None = None) -> None:
    if normalize_gnu_visibility and bridge_context_directory is not None:
        raise RuntimeError("GNU visibility and six-bridge modes are mutually exclusive")
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
    bridge_context_record = None
    if bridge_context_directory is not None:
        bridge_context_directory = bridge_context_directory.resolve()
        _, _, bridge_context_record = measured_bridge_contexts(repair, bridge_context_directory)
    identities = current_identities(repair, bridge_context_directory)
    repair.save(raw / "identities.json", identities, budget)
    if bridge_context_directory is None:
        replay_input_copies(raw, budget)
    else:
        replay_bridge_input_copies(raw, bridge_context_directory, budget)
    repair.save(raw / "temporary-accounting.json", repair.probe_temporary_accounting(), budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    extensions = repair.prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, server, token = "http://127.0.0.1:9017", "cix-cxx-header-context-jxl", None
    password, envfile = "Aa1!" + repair.secrets.token_urlsafe(32), raw / ".scanner-env"
    results = {"status": "STARTED",
               "kind": "SIX_BRIDGE_HEADER_CONTEXT_PROBE" if bridge_context_directory else "ORIGINAL_JXL_HEADER_CONTEXT_PROBE",
               "normalize_gnu_visibility": normalize_gnu_visibility,
               "bridge_context_directory": str(bridge_context_directory) if bridge_context_directory else None,
               "normalization": normalization_metadata(normalize_gnu_visibility, bridge_context_record)}
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
        if bridge_context_directory is None:
            results["probe"] = scan_header(repair, h, base, password, token, envfile, parent,
                                           out / "header", budget, normalize_gnu_visibility)
        else:
            results["probe"] = scan_bridge_headers(repair, h, base, password, token, envfile,
                                                    parent, out / "headers", budget,
                                                    bridge_context_directory)
        if identities != current_identities(repair, bridge_context_directory):
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


def worker_arguments(out: Path, normalize_gnu_visibility: bool,
                     bridge_context_directory: Path | None = None) -> list[str]:
    arguments = [sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(out)]
    if normalize_gnu_visibility:
        arguments.append("--normalize-gnu-visibility")
    if bridge_context_directory is not None:
        arguments.extend(("--bridge-context-directory", str(bridge_context_directory)))
    return arguments


def run(out: Path, normalize_gnu_visibility: bool = False,
        bridge_context_directory: Path | None = None) -> None:
    if normalize_gnu_visibility and bridge_context_directory is not None:
        raise RuntimeError("GNU visibility and six-bridge modes are mutually exclusive")
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
            result = subprocess.run(["sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()), "--wait", "--pipe", "--collect", "--slice", parent, *worker_arguments(out, normalize_gnu_visibility, bridge_context_directory)], timeout=21600)
            if out.exists(): repair.EvidenceBudget(out).write_text(out / "slice-receipt.txt", receipt)
            if result.returncode: raise RuntimeError("header context probe failed; retained evidence explains the result")
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True)
            for lease in leases: lease.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("action", choices=("run", "worker")); parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--normalize-gnu-visibility", action="store_true",
                        help="normalize only the measured per-file GNU visibility attribute for this JXL header probe")
    parser.add_argument("--bridge-context-directory", type=Path,
                        help="scan only the six headers using a completed bridge-header-context capture")
    args = parser.parse_args()
    bridge_directory = args.bridge_context_directory.resolve() if args.bridge_context_directory else None
    if args.action == "run": run(args.out.resolve(), args.normalize_gnu_visibility, bridge_directory)
    else:
        if "cix-cxx-hygiene.slice" not in Path("/proc/self/cgroup").read_text(): raise RuntimeError("worker is outside the reserved aggregate slice")
        execute(args.out.resolve(), "cix-cxx-hygiene.slice", args.normalize_gnu_visibility, bridge_directory)


if __name__ == "__main__": main()
