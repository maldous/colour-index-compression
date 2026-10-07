"""Prepare per-header CXX contexts for the six CIX-owned codec bridges.

The caller, under its own resource lease, supplies the bounded empty-input
compiler runner.  This module neither invokes a compiler nor starts an
analyzer.  It verifies one retained, successful bridge translation-unit command
per header and returns the resulting per-file Sonar CXX JSON rows and receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
CONTEXT_PARSER = ROOT / "tools/sonar-cxx/compiler_context.py"


@dataclass(frozen=True)
class Bridge:
    """One first-party header and the exact bridge TU command that owns it."""

    name: str
    header: str
    source: str
    database: str
    receipt: str
    receipt_command: str | None = None
    receipt_source_key: str | None = None


BRIDGES = (
    Bridge(
        "jxl",
        "rust/cix-native/codecs/jxl/cix_jxl_bridge.h",
        "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1/source/cix_jxl_bridge.cpp",
        "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1/build/compile_commands.json",
        "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1/receipt.json",
        receipt_source_key="cix_jxl_bridge.cpp",
    ),
    Bridge(
        "spatial",
        "rust/cix-native/codecs/spatial/cix_spatial_bridge.h",
        "benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/source/cix_spatial_bridge.cpp",
        "benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/build/compile_commands.json",
        "benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/receipt.json",
        receipt_source_key="benchmark-work/native-rc-check-v1/spatial-stride-contract-v1/source/cix_spatial_bridge.cpp",
    ),
    Bridge(
        "paq-v215",
        "rust/cix-native/codecs/paq/v215/paq_v215_bridge.h",
        "rust/cix-native/codecs/paq/v215/paq_v215_bridge.cpp",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/compile_commands/paq-v215.json",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/receipt.json",
        receipt_command="paq-v215-build",
        receipt_source_key="rust/cix-native/codecs/paq/v215/paq_v215_bridge.cpp",
    ),
    Bridge(
        "paq-v216",
        "rust/cix-native/codecs/paq/v216/paq_v216_bridge.h",
        "rust/cix-native/codecs/paq/v216/paq_v216_bridge.cpp",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/compile_commands/paq-v216.json",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/receipt.json",
        receipt_command="paq-v216-build",
        receipt_source_key="rust/cix-native/codecs/paq/v216/paq_v216_bridge.cpp",
    ),
    Bridge(
        "paq-joint-discount",
        "rust/cix-native/codecs/paq/joint_discount/paq_joint_discount_bridge.h",
        "rust/cix-native/codecs/paq/joint_discount/paq_joint_discount_bridge.cpp",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/compile_commands/paq-joint-discount.json",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/receipt.json",
        receipt_command="paq-joint-discount-build",
        receipt_source_key="rust/cix-native/codecs/paq/joint_discount/paq_joint_discount_bridge.cpp",
    ),
    Bridge(
        "paq-store-state",
        "rust/cix-native/codecs/paq/store_state/paq_store_state_bridge.h",
        "rust/cix-native/codecs/paq/store_state/paq_store_state_bridge.cpp",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/compile_commands/paq-store-state.json",
        "benchmark-work/native-rc-check-v1/bridge-portability-v1/receipt.json",
        receipt_command="paq-store-state-build",
        receipt_source_key="rust/cix-native/codecs/paq/store_state/paq_store_state_bridge.cpp",
    ),
)


class BridgeContextError(ValueError):
    """A bridge cannot supply one receipt-bound analyzer context."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_module():
    spec = importlib.util.spec_from_file_location("cix_bridge_context", CONTEXT_PARSER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _arguments(row: dict) -> list[str]:
    arguments = row.get("arguments")
    if isinstance(arguments, list) and all(isinstance(value, str) for value in arguments):
        return list(arguments)
    command = row.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    raise BridgeContextError("compilation database row lacks an exact compiler command")


def _load_one_command(bridge: Bridge) -> tuple[dict, dict]:
    database, receipt = ROOT / bridge.database, ROOT / bridge.receipt
    if not database.is_file() or not receipt.is_file():
        raise BridgeContextError(f"{bridge.name}: retained command or receipt is absent")
    try:
        rows, receipt_value = json.loads(database.read_text()), json.loads(receipt.read_text())
    except json.JSONDecodeError as error:
        raise BridgeContextError(f"{bridge.name}: retained evidence is not JSON") from error
    if not isinstance(rows, list) or not isinstance(receipt_value, dict):
        raise BridgeContextError(f"{bridge.name}: retained evidence has the wrong JSON shape")
    source = (ROOT / bridge.source).resolve()
    matching = [row for row in rows if isinstance(row, dict)
                and isinstance(row.get("file"), str)
                and Path(row["file"]).resolve() == source]
    if len(matching) != 1:
        raise BridgeContextError(f"{bridge.name}: expected exactly one matching bridge TU command")
    row = dict(matching[0])
    row["arguments"] = _arguments(row)
    if row["arguments"].count(str(source)) != 1 or "-c" not in row["arguments"]:
        raise BridgeContextError(f"{bridge.name}: retained command is not one exact compile invocation")
    return row, receipt_value


def _verify_receipt(bridge: Bridge, receipt: dict, source: Path) -> dict:
    key = bridge.receipt_source_key
    source_hashes = receipt.get("source_sha256") or receipt.get("source_hashes")
    if not isinstance(key, str) or not isinstance(source_hashes, dict):
        raise BridgeContextError(f"{bridge.name}: receipt has no source hash binding")
    expected = source_hashes.get(key)
    if not isinstance(expected, str) or sha256(source) != expected:
        raise BridgeContextError(f"{bridge.name}: bridge TU differs from its retained command receipt")
    if bridge.receipt_command is None:
        if receipt.get("status") != "pass":
            raise BridgeContextError(f"{bridge.name}: qualification receipt did not pass")
    else:
        commands = receipt.get("commands")
        if not isinstance(commands, list) or not any(
                isinstance(row, dict) and row.get("label") == bridge.receipt_command
                and row.get("returncode") == 0 for row in commands):
            raise BridgeContextError(f"{bridge.name}: retained bridge build command did not pass")
        compiled = receipt.get("compile_commands", {}).get(bridge.name)
        if not isinstance(compiled, dict) or compiled.get("sha256") != sha256(ROOT / bridge.database):
            raise BridgeContextError(f"{bridge.name}: receipt does not bind this exact compilation database")
    return {"receipt": bridge.receipt, "receipt_sha256": sha256(ROOT / bridge.receipt),
            "database": bridge.database, "database_sha256": sha256(ROOT / bridge.database),
            "source": bridge.source, "source_sha256": expected}


def visibility_normalization(header: Path, defines: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Validate and add the only allowed per-file analyzer normalization."""
    text = header.read_text()
    matches = [line.strip() for line in text.splitlines() if "__attribute__" in line]
    if len(matches) != 1 or not matches[0].endswith('__attribute__((visibility("default")))'):
        raise BridgeContextError("header does not have exactly one GNU default-visibility definition")
    if "_WIN32" in defines or "__linux__" not in defines:
        raise BridgeContextError("retained bridge context is not the required non-Windows Linux context")
    api_define = matches[0].split()[2]
    if not api_define.startswith("CIX_") or not api_define.endswith("_API"):
        raise BridgeContextError("GNU visibility definition is not a CIX bridge API definition")
    normalized = dict(defines)
    normalized["__attribute__(...)"] = ""
    return api_define, normalized


Runner = Callable[[list[str], Path], tuple[bytes, bytes, int]]


def capture_contexts(runner: Runner) -> dict:
    """Capture six independent empty-input contexts through a caller-supplied runner.

    The runner must execute the supplied compiler argv in a bounded, read-only,
    network-isolated environment and return ``stdout, stderr, returncode``.
    No header is passed to the compiler, so no header guard macro is introduced.
    """
    parser = context_module()
    entries: list[dict] = []
    initial_header_hashes: dict[str, str] = {}
    for bridge in BRIDGES:
        header, source = ROOT / bridge.header, ROOT / bridge.source
        if not header.is_file() or not source.is_file():
            raise BridgeContextError(f"{bridge.name}: current header or bridge TU is absent")
        initial_header_hashes[bridge.header] = sha256(header)
        row, receipt = _load_one_command(bridge)
        binding = _verify_receipt(bridge, receipt, source)
        argv, provenance = parser.prepare_argv(row)
        stdout, stderr, returncode = runner(argv, Path(row["directory"]))
        if returncode != 0:
            raise BridgeContextError(f"{bridge.name}: empty-input compiler context failed")
        parsed = parser.parse_compiler_output(stdout.decode(), stderr.decode())
        defines = {item["name"]: item["value"] for item in parsed["macros"]}
        guard = next((line.split()[1] for line in header.read_text().splitlines()
                      if line.startswith("#ifndef ")), None)
        if not guard or guard in defines or "__cplusplus" not in defines:
            raise BridgeContextError(f"{bridge.name}: context is polluted or is not C++")
        api_define, normalized = visibility_normalization(header, defines)
        entries.append({
            "name": bridge.name,
            "header": bridge.header,
            "header_sha256": sha256(header),
            "source": bridge.source,
            "compile_database": binding,
            "compiler_context": {**parsed, "provenance": provenance},
            "sonar_per_file": {
                "file": "/usr/src/" + bridge.header,
                "directory": "/usr/src",
                "defines": normalized,
                "includes": list(parsed["system_include_paths"]),
                "include_paths_require_read_only_container_mapping": True,
            },
            "analyzer_only_normalization": {
                "define": "__attribute__(...)", "replacement": "", "api_define": api_define,
                "source_definition": '#define ' + api_define + ' __attribute__((visibility("default")))',
                "source_header_sha256": sha256(header), "abi_or_layout_claim": "none",
            },
        })
    for relative, expected in initial_header_hashes.items():
        if sha256(ROOT / relative) != expected:
            raise BridgeContextError("a bridge header changed during context capture: " + relative)
    return {"schema": "cix.bridge-header-context.v1", "entries": entries,
            "current_headers_unchanged_during_capture": initial_header_hashes,
            "tool_sha256": {"bridge_header_context.py": sha256(Path(__file__)),
                            "compiler_context.py": sha256(CONTEXT_PARSER)}}
