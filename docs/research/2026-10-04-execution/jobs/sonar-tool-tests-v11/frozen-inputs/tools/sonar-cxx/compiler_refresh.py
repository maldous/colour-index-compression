"""Fail-closed reuse of the current qualified C++ boundary commands.

This module deliberately has no dependency on ``repair.py`` so that its small
receipt closure can be tested before the larger preparation tool imports it.
It reads evidence only; it never configures, builds, or invokes a compiler.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "benchmark-work/native-rc-check-v1"
JOBS = ROOT / "docs/research/2026-10-04-execution/jobs"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class _CmakeReceipt:
    name: str
    job: str
    current_relative: str
    units: tuple[str, ...]
    local_files: tuple[str, ...]
    dependency_targets: tuple[str, ...]
    dependency_files_required: bool = True
    dependency_manifest_required: bool = False


@dataclass(frozen=True)
class _DirectReceipt:
    name: str
    job: str
    current_relative: str
    test_relative: str
    header_relative: str
    installed_header_relative: str
    require_recorded_cwd: bool


_CMAKE_RECEIPTS = (
    _CmakeReceipt(
        name="rocksdb-contract-ndebug-v1",
        job="rocksdb-contract-ndebug-v1",
        current_relative="rust/cix-native/adapters/rocksdb",
        units=("cix_compression_manager.cc", "contract_test.cc"),
        local_files=(
            "CMakeLists.txt",
            "cix_compression_manager.cc",
            "cix_compression_manager.h",
            "contract_test.cc",
        ),
        dependency_targets=("cix_rocksdb_compression_manager", "cix_rocksdb_contract"),
    ),
    _CmakeReceipt(
        name="spatial-stride-contract-v1-bridge",
        job="spatial-stride-contract-v1",
        current_relative="rust/cix-native/codecs/spatial",
        units=("cix_spatial_bridge.cpp",),
        local_files=("CMakeLists.txt", "cix_spatial_bridge.cpp", "cix_spatial_bridge.h"),
        dependency_targets=("cix_spatial_bridge",),
    ),
    _CmakeReceipt(
        name="jxl-drain-contract-v1-bridge",
        job="jxl-drain-contract-v1",
        current_relative="rust/cix-native/codecs/jxl",
        units=("cix_jxl_bridge.cpp",),
        local_files=("CMakeLists.txt", "README.md", "cix_jxl_bridge.cpp",
                     "cix_jxl_bridge.h", "tests/jxl_drain_contract.cpp"),
        dependency_targets=("cix_jxl_bridge",),
        dependency_files_required=False,
        dependency_manifest_required=True,
    ),
)

_DIRECT_RECEIPTS = (
    _DirectReceipt("spatial-stride-contract-v1-direct", "spatial-stride-contract-v1",
                   "rust/cix-native/codecs/spatial", "tests/spatial_stride_contract.cpp",
                   "cix_spatial_bridge.h", "include/cix/cix_spatial_bridge.h", False),
    _DirectReceipt("jxl-drain-contract-v1-direct", "jxl-drain-contract-v1",
                   "rust/cix-native/codecs/jxl", "tests/jxl_drain_contract.cpp",
                   "cix_jxl_bridge.h", "include/cix/cix_jxl_bridge.h", True),
)


def _successful(receipt: dict[str, Any]) -> bool:
    commands = receipt.get("commands")
    return isinstance(commands, list) and bool(commands) and all(
        isinstance(command, dict) and command.get("returncode") == 0 for command in commands
    ) and receipt.get("status", "pass") == "pass"


def _read_same_json(documented: Path, retained: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not documented.is_file() or not retained.is_file():
        return None, "documented or retained receipt is absent"
    if _digest(documented) != _digest(retained):
        return None, "documented and retained receipt bytes differ"
    try:
        value = json.loads(documented.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "receipt is not readable JSON"
    return value if isinstance(value, dict) else None, None if isinstance(value, dict) else "receipt is not an object"


def _read_same_database(documented: Path, retained: Path) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not documented.is_file() or not retained.is_file():
        return None, "documented or retained compilation database is absent"
    if _digest(documented) != _digest(retained):
        return None, "documented and retained compilation database bytes differ"
    try:
        value = json.loads(documented.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "compilation database is not readable JSON"
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        return None, "compilation database is not an object list"
    return value, None


def _expected_source_hash(receipt: dict[str, Any], snapshot: Path, relative: str) -> str | None:
    values = receipt.get("source_sha256")
    if not isinstance(values, dict):
        return None
    # RocksDB uses file names while spatial records project-relative paths.
    candidates = (relative, snapshot.name, str(snapshot.relative_to(ROOT)) if snapshot.is_relative_to(ROOT) else "")
    for candidate in candidates:
        value = values.get(candidate)
        if isinstance(value, str):
            return value
    return None


def _verify_local_files(receipt: dict[str, Any], snapshot_root: Path, current_root: Path,
                        files: tuple[str, ...]) -> tuple[dict[str, str] | None, dict[str, str]]:
    hashes: dict[str, str] = {}
    mismatches: dict[str, str] = {}
    for relative in files:
        snapshot, current = snapshot_root / relative, current_root / relative
        expected = _expected_source_hash(receipt, snapshot, relative)
        if expected is None:
            mismatches[relative] = "receipt has no source hash"
        elif not snapshot.is_file() or not current.is_file():
            mismatches[relative] = "snapshot or current file is absent"
        elif _digest(snapshot) != expected:
            mismatches[relative] = "snapshot differs from receipt source hash"
        elif _digest(current) != expected:
            mismatches[relative] = "current differs from qualified snapshot"
        else:
            hashes[relative] = expected
    return (hashes if not mismatches else None), mismatches


def _arguments(row: dict[str, Any]) -> list[str] | None:
    raw = row.get("arguments")
    if isinstance(raw, list) and all(isinstance(value, str) for value in raw):
        return list(raw)
    command = row.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    return None


def _map_source_operand(arguments: list[str], frozen: Path, current: Path) -> list[str] | None:
    frozen_text, current_text = str(frozen), str(current)
    if arguments.count(frozen_text) != 1:
        return None
    mapped = list(arguments)
    mapped[mapped.index(frozen_text)] = current_text
    return mapped


def _dependency_paths(path: Path) -> list[Path] | None:
    """Read a GNU Make dependency file without treating it as a shell command."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        _, dependencies = text.replace("\\\n", " ").split(":", 1)
        return [Path(value).resolve() for value in shlex.split(dependencies)]
    except (OSError, ValueError):
        return None


def _dependency_provenance(build: Path, snapshot_root: Path, current_root: Path,
                           units: tuple[str, ...], targets: tuple[str, ...],
                           required: bool) -> tuple[dict[str, Any] | None, str | None]:
    if len(units) != len(targets):
        return None, "receipt dependency target closure is malformed"
    local: dict[str, dict[str, str]] = {}
    external: dict[str, str] = {}
    for unit, target in zip(units, targets):
        dependencies = _dependency_paths(build / "CMakeFiles" / f"{target}.dir" / f"{unit}.o.d")
        if dependencies is None:
            if required:
                return None, f"dependency file is absent or malformed for {unit}"
            return {"local": local, "external_header_inputs": external,
                    "mode": "receipt-source-manifest; retained Ninja dependency file absent"}, None
        for frozen in dependencies:
            if not frozen.is_file():
                return None, f"dependency path is absent: {frozen}"
            if frozen.is_relative_to(snapshot_root):
                relative = frozen.relative_to(snapshot_root)
                current = (current_root / relative).resolve()
                if not current.is_relative_to(current_root) or not current.is_file():
                    return None, f"current dependency is absent or escapes root: {relative}"
                frozen_hash, current_hash = _digest(frozen), _digest(current)
                if frozen_hash != current_hash:
                    return None, f"current dependency differs: {relative}"
                local[str(relative)] = {
                    "snapshot": str(frozen), "current": str(current), "sha256": frozen_hash,
                }
            else:
                external[str(frozen)] = _digest(frozen)
    return {"local": local, "external_header_inputs": external,
            "mode": "retained-dependency-files"}, None


def _receipt_dependency_manifest(receipt: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Verify a receipt-pinned SDK closure when a retained depfile is absent."""
    root_value, recorded = receipt.get("dependency_root"), receipt.get("dependency_sha256")
    if (not isinstance(root_value, str) or not isinstance(recorded, dict)
            or receipt.get("dependencies_unchanged") is not True):
        return None, "receipt has no dependency manifest"
    root = Path(root_value)
    if not root.is_absolute() or not root.is_dir():
        return None, "receipt dependency root is absent or not absolute"
    verified: dict[str, str] = {}
    for relative, expected in recorded.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            return None, "receipt dependency manifest is malformed"
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
            return None, f"receipt dependency input is absent or escapes root: {relative}"
        if _digest(candidate) != expected:
            return None, f"receipt dependency input differs: {relative}"
        verified[relative] = expected
    if not verified:
        return None, "receipt dependency manifest is empty"
    return {
        "mode": "receipt-dependency-sha256-manifest",
        "dependency_root": str(root),
        "inputs": verified,
    }, None


def _normalised_cmake_rows(rows: list[dict[str, Any]], snapshot_root: Path, current_root: Path,
                           units: tuple[str, ...]) -> tuple[list[dict[str, Any]] | None, str | None]:
    wanted = {(snapshot_root / unit).resolve(): (current_root / unit).resolve() for unit in units}
    selected: list[dict[str, Any]] = []
    for row in rows:
        file = row.get("file")
        directory = row.get("directory")
        if not isinstance(file, str) or not isinstance(directory, str):
            return None, "database row lacks file or directory"
        frozen = Path(file).resolve()
        current = wanted.get(frozen)
        if current is None:
            continue
        arguments = _arguments(row)
        if arguments is None or "-c" not in arguments:
            return None, f"CMake row is not an exact compile invocation: {frozen.name}"
        mapped = _map_source_operand(arguments, frozen, current)
        if mapped is None:
            return None, f"CMake source operand is absent or duplicated: {frozen.name}"
        selected.append({"file": str(current), "directory": directory, "arguments": mapped})
    expected = {str(value) for value in wanted.values()}
    if len(selected) != len(expected) or {row["file"] for row in selected} != expected:
        return None, "database does not contain each requested translation unit exactly once"
    return selected, None


def _direct_contract_row(receipt: dict[str, Any], snapshot_root: Path,
                         current_root: Path, prefix: Path,
                         spec: _DirectReceipt) -> tuple[dict[str, Any] | None, str | None]:
    frozen_test = (snapshot_root / spec.test_relative).resolve()
    current_test = (current_root / spec.test_relative).resolve()
    candidates = [
        item for item in receipt.get("commands", []) if isinstance(item, dict)
        and item.get("label") == "compile-contract" and item.get("returncode") == 0
    ]
    if len(candidates) != 1 or not current_test.is_file():
        return None, "expected one successful direct compiler receipt"
    expected_test_hash = _expected_source_hash(receipt, frozen_test, spec.test_relative)
    if (expected_test_hash is None or not frozen_test.is_file()
            or _digest(frozen_test) != expected_test_hash
            or _digest(current_test) != expected_test_hash):
        return None, "direct-test source differs from qualified snapshot"
    arguments = candidates[0].get("argv")
    if not isinstance(arguments, list) or not all(isinstance(value, str) for value in arguments):
        return None, "direct compiler argv is malformed"
    mapped = _map_source_operand(arguments, frozen_test, current_test)
    if mapped is None:
        return None, "direct compiler source operand is absent or duplicated"
    # The direct contract deliberately linked its executable; preserve that
    # complete argv and reject an accidental conversion to a synthetic compile.
    if "-c" in arguments:
        return None, "direct contract unexpectedly contains synthetic -c"
    frozen_header = snapshot_root / spec.header_relative
    current_header = current_root / spec.header_relative
    installed_header = prefix / spec.installed_header_relative
    if not all(path.is_file() for path in (frozen_header, current_header, installed_header)):
        return None, "direct-test header is absent"
    header_hash = _digest(frozen_header)
    if _digest(current_header) != header_hash or _digest(installed_header) != header_hash:
        return None, "direct-test header identity differs"
    # Every direct-argv path that influences compilation is absolute.  Some
    # receipts also retain their qualification cwd; preserve it when present.
    include_root, library_root = prefix / "include/cix", prefix / "lib"
    if (str(frozen_test) not in arguments or str(include_root) not in arguments or
            str(library_root) not in arguments or "-o" not in arguments or
            not any(argument.startswith("-Wl,-rpath,") and str(library_root) in argument
                    for argument in arguments)):
        return None, "direct compiler argv is not the retained absolute-path closure"
    command_cwd = candidates[0].get("cwd")
    if spec.require_recorded_cwd:
        if not isinstance(command_cwd, str) or not Path(command_cwd).is_absolute():
            return None, "direct compiler receipt has no absolute recorded cwd"
        directory, directory_origin = command_cwd, "recorded-qualified-cwd"
    else:
        directory = str(current_root)
        directory_origin = "normalised-no-recorded-cwd-all-semantic-operands-absolute"
    return {
        "file": str(current_test),
        "directory": directory,
        "arguments": mapped,
        "directory_origin": directory_origin,
        "installed_header": {"snapshot": str(frozen_header), "current": str(current_header),
                             "installed": str(installed_header), "sha256": header_hash},
    }, None


def _completed_boundary_commands(
        source: Path, specs: tuple[_CmakeReceipt, ...],
        direct_specs: tuple[_DirectReceipt, ...] = _DIRECT_RECEIPTS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    database: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}
    direct_contexts: dict[str, tuple[dict[str, Any], Path, Path, Path]] = {}
    for spec in specs:
        documented = JOBS / spec.job
        retained = WORK / spec.job
        receipt, error = _read_same_json(documented / "receipt.json", retained / "receipt.json")
        if error or receipt is None or not _successful(receipt):
            provenance[spec.name] = {"status": "unavailable", "reason": error or "receipt did not pass"}
            continue
        rows, error = _read_same_database(documented / "compile_commands.json", retained / "build/compile_commands.json")
        if error or rows is None:
            provenance[spec.name] = {"status": "unavailable", "reason": error}
            continue
        snapshot_root = retained / "source"
        current_root = source / spec.current_relative
        hashes, mismatches = _verify_local_files(receipt, snapshot_root, current_root, spec.local_files)
        if hashes is None:
            provenance[spec.name] = {"status": "stale_source_or_header", "mismatches": mismatches}
            continue
        dependencies, error = _dependency_provenance(
            retained / "build", snapshot_root, current_root, spec.units,
            spec.dependency_targets, spec.dependency_files_required)
        if error or dependencies is None:
            provenance[spec.name] = {"status": "unavailable", "reason": error}
            continue
        if spec.dependency_manifest_required:
            manifest, error = _receipt_dependency_manifest(receipt)
            if error or manifest is None:
                provenance[spec.name] = {"status": "unavailable", "reason": error}
                continue
            dependencies["receipt_dependency_manifest"] = manifest
        selected, error = _normalised_cmake_rows(rows, snapshot_root, current_root, spec.units)
        if error or selected is None:
            provenance[spec.name] = {"status": "unavailable", "reason": error}
            continue
        database.extend(selected)
        provenance[spec.name] = {
            "status": "qualified_cmake_database_reused",
            "receipt_sha256": _digest(documented / "receipt.json"),
            "database_sha256": _digest(documented / "compile_commands.json"),
            "source_header_hashes": hashes,
            "header_bindings": dependencies,
        }
        direct_contexts[spec.job] = (receipt, snapshot_root, current_root, retained / "prefix")
    for direct_spec in direct_specs:
        context = direct_contexts.get(direct_spec.job)
        if context is None:
            provenance[direct_spec.name] = {
                "status": "unavailable", "reason": "matching CMake receipt is unavailable",
            }
            continue
        receipt, snapshot_root, current_root, prefix = context
        if current_root != (source / direct_spec.current_relative).resolve():
            provenance[direct_spec.name] = {
                "status": "unavailable", "reason": "direct receipt root does not match its CMake closure",
            }
            continue
        direct, error = _direct_contract_row(
            receipt, snapshot_root, current_root, prefix, direct_spec)
        if error or direct is None:
            provenance[direct_spec.name] = {"status": "unavailable", "reason": error}
        else:
            database.append({key: value for key, value in direct.items() if key in {"file", "directory", "arguments"}})
            provenance[direct_spec.name] = {
                "status": "qualified_direct_compiler_argv_reused",
                "receipt_sha256": _digest(JOBS / direct_spec.job / "receipt.json"),
                "directory_origin": direct["directory_origin"],
                "installed_header": direct["installed_header"],
            }
    return database, provenance


def completed_boundary_commands(source: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return only current qualified RocksDB, spatial, and JXL commands.

    A failed closure is reported per receipt and contributes no command.  This
    makes callers able to retain existing coverage while leaving changed or
    incomplete boundary units explicitly unconfigured.
    """
    return _completed_boundary_commands(source.resolve(), _CMAKE_RECEIPTS)
