#!/usr/bin/env python3
"""Run the prepared Node-only unwrap qualification after root applies its patch."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/node-unwrap-v1"
SDK = ROOT / "benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8"
NODE_SOURCE = ROOT / "rust/cix-native/bindings/node"
PATCH = ROOT / "docs/research/2026-10-04-execution/reviews/node-unwrap-v1.patch"
PATCH_SHA256 = "9edd25e9ddfb98ed07c38c8a25daee59a9a6d2674404ab2c92c93f3431aa2192"
NODE_API = Path("/usr/include/node")
HOST_TOOLS = (Path("/usr/bin/cmake"), Path("/usr/bin/cc"), Path("/usr/bin/node"))
LOG_LIMIT_BYTES = 1024 * 1024
EXPECTED = {
    NODE_SOURCE / "src/cix_node.c": "2556b1c33b93ce7bc4d15ac95b1449c6e35dfae56158f909172af33d1adff35b",
    NODE_SOURCE / "test/contract.js": "8f6a1e8195e270c90c27335bc03e0333b5965ba0fb39b215d42ec6a0ab9d5366",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_paths(native: Path) -> tuple[Path, ...]:
    """Return every source, SDK, and host file that influences this add-on."""
    return (
        PATCH,
        native,
        NODE_SOURCE / "CMakeLists.txt",
        *EXPECTED,
        SDK / "include/cix.h",
        SDK / "include/cix_stream.h",
        NODE_API / "node_api.h",
        NODE_API / "js_native_api.h",
        *HOST_TOOLS,
    )


def capped_file_limit() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (LOG_LIMIT_BYTES, LOG_LIMIT_BYTES))


def main() -> int:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError("refusing to reuse Node unwrap work directory")
    native = SDK / "lib/libcix_native.so"
    inputs = input_paths(native)
    for path in inputs:
        if not path.is_file():
            raise RuntimeError("required retained input is missing: " + str(path))
    if digest(PATCH) != PATCH_SHA256:
        raise RuntimeError("prepared patch artifact identity changed")
    def identity_key(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    identities = {identity_key(path): digest(path) for path in inputs}
    for path, expected in EXPECTED.items():
        if identities[identity_key(path)] != expected:
            raise RuntimeError("prepared patch was not applied exactly: " + str(path))

    WORK.mkdir(parents=True)
    receipt: dict[str, object] = {
        "status": "started",
        "scope": "Node add-on only; retained native SDK is linked, never rebuilt",
        "input_sha256": identities,
        "loaded_javascript_entrypoints": [str(NODE_SOURCE / "test/contract.js")],
        "log_cap_bytes_per_stream": LOG_LIMIT_BYTES,
        "commands": [],
    }

    def save() -> None:
        (JOB / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    def run(label: str, argv: list[str], env: dict[str, str]) -> None:
        stdout_path = JOB / (label + ".stdout.log")
        stderr_path = JOB / (label + ".stderr.log")
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            result = subprocess.run(argv, cwd=WORK, env=env, stdout=stdout,
                                    stderr=stderr, timeout=300,
                                    preexec_fn=capped_file_limit)
        receipt["commands"].append({"label": label, "argv": argv,
                                    "returncode": result.returncode,
                                    "stdout": str(stdout_path.relative_to(ROOT)),
                                    "stderr": str(stderr_path.relative_to(ROOT))})
        save()
        if result.returncode:
            raise RuntimeError(label + " failed; inspect retained job log")

    environment = {**os.environ, "PATH": "/usr/bin:/bin",
                   "LD_LIBRARY_PATH": str(SDK / "lib"),
                   "CIX_NODE_ADDON": str(WORK / "build/cix_node.node")}
    try:
        run("node-runtime-identity", ["/usr/bin/node", "-p", "JSON.stringify(process.versions)"], environment)
        run("configure", ["/usr/bin/cmake", "-S", str(NODE_SOURCE), "-B", str(WORK / "build"),
                          "-DCIX_SDK_INCLUDE_DIR=" + str(SDK / "include"),
                          "-DCIX_SDK_LIBRARY=" + str(native),
                          "-DNODE_API_INCLUDE_DIR=" + str(NODE_API),
                          "-DCMAKE_C_COMPILER=/usr/bin/cc",
                          "-DCMAKE_BUILD_TYPE=Release"], environment)
        run("build-addon-only", ["/usr/bin/cmake", "--build", str(WORK / "build"), "--parallel", "2"], environment)
        run("node-contract", ["/usr/bin/node", str(NODE_SOURCE / "test/contract.js")], environment)
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        receipt["inputs_unchanged"] = identities == {
            identity_key(path): digest(path) for path in inputs
        }
        if not receipt["inputs_unchanged"]:
            receipt["status"] = "fail_input_changed"
        save()
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
