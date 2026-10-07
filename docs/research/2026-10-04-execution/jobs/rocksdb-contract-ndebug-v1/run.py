import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess


if os.environ.get("CIX_RELEASE_LEASE") != "1":
    raise RuntimeError("CIX_RELEASE_LEASE=1 is required")

root = Path(__file__).resolve().parents[5]
work = root / "benchmark-work/native-rc-check-v1"
out = work / "rocksdb-contract-ndebug-v1"
if out.exists():
    raise RuntimeError(f"refusing to reuse existing output: {out}")
out.mkdir()

source = root / "rust/cix-native/adapters/rocksdb"
stage = out / "source"
stage.mkdir()
source_names = (
    "CMakeLists.txt",
    "cix_compression_manager.cc",
    "cix_compression_manager.h",
    "contract_test.cc",
)
for name in source_names:
    candidate = source / name
    if not candidate.is_file():
        raise RuntimeError(f"missing CIX-owned adapter source: {candidate}")
    shutil.copy2(candidate, stage / name)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


contract = (stage / "contract_test.cc").read_text()
required = (
    "create default CIX compression manager",
    "reject manager limit above 128 MiB",
    "create CIX database",
    "write repetitive value",
    "write random value",
    "flush CIX SST",
    "read table properties",
    "persist CIX compression identity",
    "open without manager returns database",
    "reject CIX block without manager",
    "failed open leaves no database",
    "reopen CIX database",
    "read repetitive value",
    "read random value",
    "read manager statistics",
    "record CIX and raw codec paths",
    "get default decompressor",
    "reject malformed CIX length header",
    "create bounded CIX compression manager",
    "get bounded decompressor",
    "reject length above manager cap",
)
for text in required:
    if text not in contract:
        raise RuntimeError(f"missing assertion-independent contract check: {text}")
if re.search(r"\bassert\s*\(", contract):
    raise RuntimeError("runtime assert remains in contract_test.cc")

sdk = work / "sdk-bindings-relocated-cli-bindings-v8"
rocksdb_source = work / "rocksdb-source-v1"
rocksdb_build = work / "rocksdb-host-v1/upstream-build"
inputs = {
    "sdk_library": sdk / "lib/libcix_native.so",
    "rocksdb_library": rocksdb_build / "librocksdb.so",
    "rocksdb_version_header": rocksdb_source / "include/rocksdb/version.h",
    "rocksdb_advanced_compression_header": rocksdb_source / "include/rocksdb/advanced_compression.h",
    "rocksdb_compression_type_header": rocksdb_source / "include/rocksdb/compression_type.h",
}
for name, path in inputs.items():
    if not path.is_file():
        raise RuntimeError(f"missing pinned input {name}: {path}")

rows = []


def write_receipt(extra=None):
    record = {
        "job": "execution-rocksdb-contract-ndebug-v1",
        "source_sha256": {name: sha256(stage / name) for name in source_names},
        "pinned_input_sha256": {name: sha256(path) for name, path in inputs.items()},
        "commands": rows,
    }
    if extra:
        record.update(extra)
    (out / "receipt.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


def run(argv, env=None):
    command = [str(value) for value in argv]
    child_env = {**os.environ, **(env or {})}
    completed = subprocess.run(command, cwd=out, env=child_env, capture_output=True, text=True)
    rows.append({
        "argv": command,
        "env_extra": env or {},
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    })
    write_receipt()
    if completed.returncode:
        raise RuntimeError(completed.stderr[-7000:] or completed.stdout[-7000:])


build = out / "build"
run([
    "cmake", "-S", stage, "-B", build,
    "-DCMAKE_BUILD_TYPE=Release",
    "-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG",
    "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    "-DCIX_NATIVE_INCLUDE_DIR=" + str(sdk / "include"),
    "-DCIX_NATIVE_LIBRARY=" + str(inputs["sdk_library"]),
    "-DROCKSDB_INCLUDE_DIR=" + str(rocksdb_source / "include"),
    "-DROCKSDB_LIBRARY=" + str(inputs["rocksdb_library"]),
])
run(["cmake", "--build", build, "--target", "cix_rocksdb_contract", "-j2"])

compile_commands = json.loads((build / "compile_commands.json").read_text())
contract_commands = [entry for entry in compile_commands if Path(entry["file"]).name == "contract_test.cc"]
if len(contract_commands) != 1:
    raise RuntimeError("expected exactly one contract_test.cc compile command")
compile_command = contract_commands[0]["command"]
if "-DNDEBUG" not in compile_command or "-UNDEBUG" in compile_command:
    raise RuntimeError("contract target did not compile with exactly the required NDEBUG state")

runtime_paths = f"{sdk / 'lib'}:{rocksdb_build}"
run(["ctest", "--test-dir", build, "--output-on-failure"], {
    "TMPDIR": str(out),
    "LD_LIBRARY_PATH": runtime_paths,
})
write_receipt({
    "qualification": {
        "configuration": "Release with explicit -DNDEBUG and no -UNDEBUG in the actual contract compile command",
        "assertion_independent_checks": "all contract runtime checks; source validation rejects every assert( call",
    },
    "contract_compile_command": compile_command,
})
