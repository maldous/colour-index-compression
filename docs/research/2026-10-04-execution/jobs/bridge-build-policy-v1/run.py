#!/usr/bin/env python3
"""Lease-gated policy check for current PAQ and spatial CMake bridge inputs.

PAQ is configured only: no PAQ bridge objects or libraries are built.  The
spatial bridge is built in this job to exercise its current dependency-root
policy and the existing row-stride contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
from collections import Counter
from pathlib import Path

PROJECT = Path("/home/user/src/colour-index-compression")
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/bridge-build-policy-v1"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/bridge-build-policy-v1"
PROVENANCE = PROJECT / "rust/cix-native/packaging/notices/provider-provenance-v3.json"
PRIOR_COMMANDS = PROJECT / "docs/research/2026-10-04-execution/jobs/bridge-portability-v1/compile_commands"
RETAINED_SDK = PROJECT / "benchmark-work/native-rc-check-v1/codec-sdk-v1/prefix"
WORK_LIMIT_BYTES = 4_000_000_000
PAQ = {
    "paq-v215": ("CIX_RUNTIME_PAQ_V215_BRIDGE", "v215"),
    "paq-v216": ("CIX_RUNTIME_PAQ_V216_BRIDGE", "v216"),
    "paq-joint-discount": ("CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE", "joint_discount"),
    "paq-store-state": ("CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE", "store_state"),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def work_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file() and not item.is_symlink())


def check_work_budget() -> int:
    used = work_size(WORK)
    if used > WORK_LIMIT_BYTES:
        raise RuntimeError(f"work limit exceeded: {used} > {WORK_LIMIT_BYTES}")
    return used


def run(command: list[str], receipt: dict, label: str, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False, env=env, timeout=120)
    receipt["commands"].append({"label": label, "argv": command, "returncode": result.returncode,
                                "stdout": result.stdout, "stderr": result.stderr,
                                "work_bytes_after": check_work_budget()})
    if result.returncode:
        raise RuntimeError(f"{label} failed")


def source_inputs() -> dict[str, str]:
    paths: list[Path] = [
        PROJECT / "rust/cix-native/codecs/spatial/CMakeLists.txt",
        PROJECT / "rust/cix-native/codecs/spatial/cix_spatial_bridge.cpp",
        PROJECT / "rust/cix-native/codecs/spatial/cix_spatial_bridge.h",
        PROJECT / "rust/cix-native/codecs/spatial/tests/spatial_stride_contract.cpp",
    ]
    for _, (_, directory) in PAQ.items():
        root = PROJECT / "rust/cix-native/codecs/paq" / directory
        paths.extend((root / "CMakeLists.txt", root / f"paq_{directory}_bridge.cpp",
                      root / f"paq_{directory}_bridge.h", root / "exports.map"))
    if not all(path.is_file() for path in paths):
        missing = [str(path) for path in paths if not path.is_file()]
        raise RuntimeError(f"missing frozen bridge input: {missing}")
    return {str(path.relative_to(PROJECT)): digest(path) for path in paths}


def command_tokens(entry: dict) -> list[str]:
    arguments = entry.get("arguments")
    if isinstance(arguments, list) and all(isinstance(value, str) for value in arguments):
        return arguments
    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    raise RuntimeError("compile command has neither string arguments nor command")


def source_or_object(token: str) -> str | None:
    suffix = Path(token).suffix.lower()
    if suffix in {".c", ".cc", ".cpp", ".cxx"}:
        return "<source>"
    if suffix in {".o", ".obj"}:
        return "<object>"
    return None


def semantic_tokens(entry: dict) -> tuple[str, ...]:
    """Retain all flags and paths except actual source and object operands."""
    result: list[str] = []
    expect: str | None = None
    for token in command_tokens(entry):
        if expect is not None:
            result.append(expect)
            expect = None
            continue
        if token == "-c":
            result.append(token)
            expect = "<source>"
            continue
        if token == "-o":
            result.append(token)
            expect = "<object>"
            continue
        if token.startswith("-o") and len(token) > 2:
            result.append("-o<object>")
            continue
        result.append(source_or_object(token) or token)
    if expect is not None:
        raise RuntimeError("compile command ended after source/object flag")
    return tuple(result)


def semantic_counter(path: Path) -> Counter[tuple[str, ...]]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise RuntimeError(f"compile command manifest is not a list: {path}")
    return Counter(semantic_tokens(entry) for entry in entries)


def counter_digest(counter: Counter[tuple[str, ...]]) -> str:
    material = [[list(tokens), count] for tokens, count in sorted(counter.items())]
    return hashlib.sha256(json.dumps(material, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def configure_paq(name: str, source: Path, upstream: Path, receipt: dict) -> None:
    build = WORK / "paq-configure" / name
    command = ["/usr/bin/cmake", "-S", str(source), "-B", str(build),
               "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
               f"-DCIX_PAQ_SOURCE_ROOT={upstream}"]
    run(command, receipt, f"{name}-configure-only")
    generated = build / "compile_commands.json"
    prior = PRIOR_COMMANDS / f"{name}.json"
    if not generated.is_file() or not prior.is_file():
        raise RuntimeError(f"missing generated or retained compile commands for {name}")
    copied = WORK / "compile_commands" / f"{name}.json"
    copied.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated, copied)
    before, after = semantic_counter(prior), semantic_counter(copied)
    comparison = {
        "retained_path": str(prior), "retained_sha256": digest(prior),
        "generated_path": str(copied), "generated_sha256": digest(copied),
        "normalization": "only C/C++ source operands and object-output operands are replaced; compiler, include, define and other compilation flags remain exact; linker flags are not compared",
        "before_semantic_sha256": counter_digest(before), "after_semantic_sha256": counter_digest(after),
        "equal": before == after,
    }
    receipt["paq_configure_comparisons"][name] = comparison
    if not comparison["equal"]:
        raise RuntimeError(f"{name} generated compiler semantics differ from bridge-portability-v1")


def find_retained(relative: str) -> Path:
    path = RETAINED_SDK / relative
    if not path.is_file():
        raise RuntimeError(f"retained SDK file missing: {path}")
    return path


def link_readonly(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    if not link.is_symlink() or link.resolve() != target.resolve():
        raise RuntimeError(f"SDK symlink did not resolve to retained input: {link}")


def split_sdk(receipt: dict) -> tuple[Path, Path, list[str]]:
    charls_header = find_retained("usr/include/charls/charls.h")
    charls_library = find_retained("usr/lib/x86_64-linux-gnu/libcharls.so")
    openjpeg_header = find_retained("usr/include/openjpeg-2.5/openjpeg.h")
    openjpeg_library = find_retained("usr/lib/x86_64-linux-gnu/libopenjp2.so")
    charls_root, openjpeg_root = WORK / "sdk/charls", WORK / "sdk/openjpeg"
    link_readonly(charls_root / "include/charls", charls_header.parent)
    link_readonly(charls_root / "lib/libcharls.so", charls_library)
    link_readonly(openjpeg_root / "include/openjpeg-2.5", openjpeg_header.parent)
    link_readonly(openjpeg_root / "lib/libopenjp2.so", openjpeg_library)
    for root in (charls_root, charls_root / "include", charls_root / "lib", openjpeg_root, openjpeg_root / "include", openjpeg_root / "lib"):
        root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    dependency_files = sorted(set([charls_library, openjpeg_library,
        *[path for directory in (charls_header.parent, openjpeg_header.parent)
          for path in directory.rglob("*") if path.is_file()]]))
    receipt["spatial_dependencies"] = {
        "policy": "two separate job-owned, read-only symlink roots; no host discovery root is passed",
        "before": {str(path.relative_to(PROJECT)): digest(path) for path in dependency_files},
        "roots": [str(charls_root), str(openjpeg_root)],
        "after": {str(link.relative_to(WORK)): str(link.resolve()) for link in
                  (charls_root / "include/charls", charls_root / "lib/libcharls.so",
                   openjpeg_root / "include/openjpeg-2.5", openjpeg_root / "lib/libopenjp2.so")},
    }
    return charls_root, openjpeg_root, [str(charls_library.parent), str(openjpeg_library.parent)]


def build_spatial(receipt: dict) -> None:
    charls_root, openjpeg_root, runtime_libraries = split_sdk(receipt)
    source, build, prefix = (WORK / "source/rust/cix-native/codecs/spatial", WORK / "spatial/build", WORK / "spatial/prefix")
    roots = f"{charls_root};{openjpeg_root}"
    run(["/usr/bin/cmake", "-S", str(source), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
         "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", f"-DCMAKE_INSTALL_PREFIX={prefix}",
         f"-DCIX_SPATIAL_DEPENDENCY_ROOTS={roots}"], receipt, "spatial-configure")
    run(["/usr/bin/cmake", "--build", str(build), "--parallel", "4"], receipt, "spatial-build")
    run(["/usr/bin/cmake", "--install", str(build)], receipt, "spatial-install")
    bridge = prefix / "lib/libcix_spatial_bridge.so"
    if not bridge.is_file():
        raise RuntimeError("spatial install did not produce bridge library")
    executable = WORK / "spatial/spatial_stride_contract"
    run(["/usr/bin/c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O3", "-DNDEBUG", str(source / "tests/spatial_stride_contract.cpp"),
         "-I", str(prefix / "include/cix"), "-L", str(prefix / "lib"),
         "-Wl,-rpath," + str(prefix / "lib"), "-lcix_spatial_bridge", "-o", str(executable)], receipt,
        "spatial-compile-stride-contract")
    run([str(executable)], receipt, "spatial-run-stride-contract",
        {**os.environ, "LD_LIBRARY_PATH": ":".join(runtime_libraries)})
    receipt["spatial_artifacts"] = {"bridge": {"path": str(bridge), "sha256": digest(bridge)},
                                    "stride_contract": {"path": str(executable), "sha256": digest(executable)}}


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse work root: {WORK}")
    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    if provenance.get("schema") != "cix-selected-runtime-provider-provenance-v3":
        raise RuntimeError("unexpected provider provenance schema")
    frozen_before = source_inputs()
    receipt = {"schema": "cix-bridge-build-policy-v1", "status": "running",
               "scope": "PAQ configure-only semantic compiler-flag comparison plus current spatial bridge build and existing stride contract; Linux host evidence only",
               "non_claims": ["no PAQ bridge build or runtime qualification", "no target-platform or package-manager qualification"],
               "work_limit_bytes": WORK_LIMIT_BYTES, "source_hashes_before": frozen_before,
               "provider_provenance_sha256": digest(PROVENANCE), "commands": [],
               "paq_configure_comparisons": {}}
    try:
        WORK.mkdir(parents=True)
        for relative, expected in frozen_before.items():
            frozen = WORK / "source" / relative
            frozen.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PROJECT / relative, frozen)
            if digest(frozen) != expected:
                raise RuntimeError("source changed while freezing: " + relative)
        for name, (key, directory) in PAQ.items():
            source = WORK / "source/rust/cix-native/codecs/paq" / directory
            binding = provenance["providers"].get(key, {}).get("source", {})
            upstream = PROJECT / str(binding.get("local_root", ""))
            receipt_name, expected = binding.get("receipt"), binding.get("receipt_sha256")
            if not upstream.is_dir() or not isinstance(receipt_name, str) or not isinstance(expected, str):
                raise RuntimeError(f"invalid provider provenance for {key}")
            actual = digest(PROJECT / receipt_name)
            if actual != expected:
                raise RuntimeError(f"provider source receipt hash mismatch for {key}")
            receipt.setdefault("provider_sources", {})[key] = {"local_root": str(upstream),
                "receipt": receipt_name, "receipt_sha256": actual}
            configure_paq(name, source, upstream, receipt)
        build_spatial(receipt)
        frozen_after = source_inputs()
        receipt["source_hashes_after"] = frozen_after
        if frozen_before != frozen_after:
            raise RuntimeError("frozen current bridge inputs changed during job")
        dependency_before = receipt["spatial_dependencies"]["before"]
        receipt["spatial_dependencies"]["hashes_after"] = {
            name: digest(PROJECT / name) for name in dependency_before}
        if receipt["spatial_dependencies"]["hashes_after"] != dependency_before:
            raise RuntimeError("retained spatial SDK inputs changed during job")
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        receipt["work_bytes_final"] = work_size(WORK) if WORK.exists() else 0
        atomic_json(JOB / "source-hashes.json", {"schema": "cix-bridge-build-policy-v1-source-hashes",
                    "inputs": frozen_before, "provider_provenance_sha256": receipt["provider_provenance_sha256"]})
        atomic_json(JOB / "receipt.json", receipt)


if __name__ == "__main__":
    main()
