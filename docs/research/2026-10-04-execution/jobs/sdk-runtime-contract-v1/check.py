#!/usr/bin/env python3
"""Root-scheduled CMake layout checks for the SDK and native-only runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require_file(path: Path, name: str) -> Path:
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError(f"{name} must be an existing absolute file: {path}")
    return path


def run(command: list[str], receipt: dict, label: str, expect: int | None = 0) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    receipt["commands"].append({
        "label": label,
        "argv": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    })
    if expect is None:
        if result.returncode == 0:
            raise RuntimeError(f"{label} unexpectedly succeeded")
    elif result.returncode != expect:
        raise RuntimeError(f"{label} returned {result.returncode}, expected {expect}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-source", type=Path, required=True)
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--unix-shared", type=Path, required=True)
    parser.add_argument("--unix-static", type=Path, required=True)
    parser.add_argument("--cix", type=Path, required=True)
    parser.add_argument("--provider-closure", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, default=Path("/usr/bin/cmake"))
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    for label, path in (("SDK source", args.sdk_source), ("runtime source", args.runtime_source)):
        if not path.is_absolute() or not path.is_dir():
            raise RuntimeError(f"{label} must be an existing absolute directory: {path}")
    for label, path in (("Unix shared library", args.unix_shared),
                        ("Unix static library", args.unix_static), ("CIX executable", args.cix),
                        ("Provider closure", args.provider_closure), ("CMake", args.cmake)):
        require_file(path, label)
    if args.work.exists():
        raise RuntimeError(f"work directory already exists: {args.work}")
    args.work.mkdir(parents=True)
    receipt = {
        "schema": "cix-sdk-runtime-layout-contract-v1",
        "status": "running",
        "scope": "CMake layout checks only; no Windows runtime or platform qualification",
        "inputs": {
            "sdk_cmakelists_sha256": digest(args.sdk_source / "CMakeLists.txt"),
            "runtime_cmakelists_sha256": digest(args.runtime_source / "CMakeLists.txt"),
            "unix_shared_sha256": digest(args.unix_shared),
            "unix_static_sha256": digest(args.unix_static),
            "cix_sha256": digest(args.cix),
        },
        "commands": [],
    }
    try:
        unix_build = args.work / "unix-sdk-build"
        unix_prefix = args.work / "unix-sdk-prefix"
        run([str(args.cmake), "-S", str(args.sdk_source), "-B", str(unix_build),
             f"-DCIX_NATIVE_LIBRARY={args.unix_shared}",
             f"-DCIX_NATIVE_STATIC_LIBRARY={args.unix_static}",
             f"-DCMAKE_INSTALL_PREFIX={unix_prefix}"], receipt, "unix-sdk-configure")
        run([str(args.cmake), "--install", str(unix_build)], receipt, "unix-sdk-install")
        if not (unix_prefix / "lib/libcix_native.so").is_file():
            raise RuntimeError("Unix SDK install omitted libcix_native.so")
        if not (unix_prefix / "lib/libcix_native.a").is_file():
            raise RuntimeError("Unix SDK install omitted libcix_native.a")

        fixture = args.work / "windows-fixture"
        fixture.mkdir()
        dll = fixture / "cix_native.dll"
        implib = fixture / "cix_native.dll.lib"
        dll.write_bytes(b"CIX synthetic Windows DLL layout fixture\n")
        implib.write_bytes(b"CIX synthetic Windows import library layout fixture\n")
        toolchain = args.work / "windows-layout-toolchain.cmake"
        toolchain.write_text("set(CMAKE_SYSTEM_NAME Windows)\nset(CMAKE_SYSTEM_PROCESSOR AMD64)\n", encoding="utf-8")
        windows_build = args.work / "windows-sdk-build"
        windows_prefix = args.work / "windows-sdk-prefix"
        windows_common = [str(args.cmake), "-S", str(args.sdk_source),
                          f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", "-DCIX_SDK_LAYOUT_ONLY=ON"]
        run(windows_common + ["-B", str(windows_build), f"-DCIX_NATIVE_LIBRARY={dll}",
             f"-DCIX_NATIVE_IMPORT_LIBRARY={implib}",
             f"-DCMAKE_INSTALL_PREFIX={windows_prefix}"], receipt, "windows-sdk-layout-configure")
        run([str(args.cmake), "--install", str(windows_build)], receipt, "windows-sdk-layout-install")
        if not (windows_prefix / "bin/cix_native.dll").is_file():
            raise RuntimeError("Windows layout install omitted the DLL runtime artifact")
        if not (windows_prefix / "lib/cix_native.dll.lib").is_file():
            raise RuntimeError("Windows layout install omitted the import library")
        consumer_source = args.work / "windows-find-package-source"
        consumer_source.mkdir()
        (consumer_source / "CMakeLists.txt").write_text("""cmake_minimum_required(VERSION 3.21)
project(CIXWindowsLayoutConsumer LANGUAGES NONE)
find_package(CIX CONFIG REQUIRED)
get_target_property(cix_type CIX::native TYPE)
get_target_property(cix_location CIX::native IMPORTED_LOCATION)
get_target_property(cix_implib CIX::native IMPORTED_IMPLIB)
if(NOT cix_type STREQUAL "SHARED_LIBRARY")
  message(FATAL_ERROR "CIX::native must be a Windows SHARED imported target")
endif()
if(NOT EXISTS "${cix_location}" OR NOT EXISTS "${cix_implib}")
  message(FATAL_ERROR "CIX imported target does not bind both installed pair members")
endif()
""", encoding="utf-8")
        run([str(args.cmake), "-S", str(consumer_source), "-B", str(args.work / "windows-find-package-build"),
             f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", f"-DCMAKE_PREFIX_PATH={windows_prefix}"],
            receipt, "windows-sdk-find-package-layout")
        negative = windows_common + ["-B", str(args.work / "windows-partial-build"),
                                     f"-DCIX_NATIVE_LIBRARY={dll}",
                                     f"-DCMAKE_INSTALL_PREFIX={args.work / 'windows-partial-prefix'}"]
        run(negative, receipt, "windows-sdk-partial-pair-negative", expect=None)

        runtime_build = args.work / "runtime-build"
        runtime_stage = args.work / "runtime-stage"
        run([str(args.cmake), "-S", str(args.runtime_source), "-B", str(runtime_build),
             "-DCIX_RUNTIME_CAPABILITY=native-only", f"-DCIX_RUNTIME_CIX_EXECUTABLE={args.cix}",
             "-DCMAKE_INSTALL_PREFIX=/usr"], receipt, "native-runtime-configure")
        environment = os.environ.copy()
        environment["DESTDIR"] = str(runtime_stage)
        result = subprocess.run([str(args.cmake), "--install", str(runtime_build), "--prefix", "/usr"],
                                text=True, capture_output=True, env=environment, check=False)
        receipt["commands"].append({"label": "native-runtime-install", "argv": result.args,
                                    "returncode": result.returncode, "stdout": result.stdout,
                                    "stderr": result.stderr})
        if result.returncode != 0:
            raise RuntimeError("native-runtime-install failed")
        commands = runtime_stage / "usr/bin"
        if not (commands / "cix").is_file() or not (commands / "uncix").is_symlink() or not (commands / "cixcat").is_symlink():
            raise RuntimeError("native runtime install did not create cix and both Unix aliases")

        closure = json.loads(args.provider_closure.read_text(encoding="utf-8"))
        providers = closure.get("providers")
        readelf = closure.get("readelf")
        if not isinstance(providers, dict) or not isinstance(readelf, str):
            raise RuntimeError("provider closure lacks providers or readelf")
        full_build = args.work / "runtime-full-build"
        full_stage = args.work / "runtime-full-stage"
        full = [str(args.cmake), "-S", str(args.runtime_source), "-B", str(full_build),
                "-DCIX_RUNTIME_CAPABILITY=full-engine", f"-DCIX_RUNTIME_CIX_EXECUTABLE={args.cix}",
                f"-DCIX_RUNTIME_READELF={readelf}", "-DCMAKE_INSTALL_PREFIX=/usr"]
        for key, item in sorted(providers.items()):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise RuntimeError(f"invalid selected provider: {key}")
            full.append(f"-D{key}={item['path']}")
        run(full, receipt, "full-runtime-configure")
        full_env = os.environ.copy()
        full_env["DESTDIR"] = str(full_stage)
        full_result = subprocess.run([str(args.cmake), "--install", str(full_build), "--prefix", "/usr"],
                                     text=True, capture_output=True, env=full_env, check=False)
        receipt["commands"].append({"label": "full-runtime-install", "argv": full_result.args,
                                    "returncode": full_result.returncode, "stdout": full_result.stdout,
                                    "stderr": full_result.stderr})
        if full_result.returncode != 0:
            raise RuntimeError("full-runtime-install failed")
        full_lib = full_stage / "usr/lib/cix"
        if len([item for item in providers if (full_lib / Path(providers[item]["path"]).name).is_file()]) != len(providers):
            raise RuntimeError("full runtime install omitted one or more selected providers")
        receipt["status"] = "pass_layout_only"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        (args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
