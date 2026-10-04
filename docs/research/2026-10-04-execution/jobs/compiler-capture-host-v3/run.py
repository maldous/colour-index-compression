"""Leased, fresh-build capture for CIX SquashFS host translation units.

This records new argv under the current source identity.  It deliberately does
not recast output from a historical qualification as an invocation record.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
ROOT = Path(__file__).resolve().parents[5]
WORK = ROOT / "benchmark-work/native-rc-check-v1"
OUT = WORK / "compiler-capture-host-v3"
OUT.mkdir(exist_ok=False)
LOG = OUT / "compiler-invocations.jsonl"
REAL_CC = shutil.which("cc")
if REAL_CC is None:
    raise SystemExit("missing required host compiler: cc")

TARGETS = {
    "tools-compressor-table": ROOT / "rust/cix-native/adapters/squashfs/tools/cix_compressor_table.c",
    "tools-wrapper": ROOT / "rust/cix-native/adapters/squashfs/tools/cix_wrapper.c",
    "sqfsng-compressor": ROOT / "rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_compressor.c",
    "sqfsng-decode-bridge": ROOT / "rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_decode.c",
    "sqfsng-read-super": ROOT / "rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_read_super.c",
    "squashfuse-library-fixture-contract": ROOT / "rust/cix-native/adapters/squashfs/userspace/tests/squashfuse_library_fixture_contract.c",
    "squashfuse-xattr-contract": ROOT / "rust/cix-native/adapters/squashfs/userspace/tests/squashfuse_xattr_contract.c",
    "kernel-xattr-helper": ROOT / "rust/cix-native/adapters/squashfs/kernel/tests/xattr_check.c",
    "squash-compatibility-plugin": ROOT / "rust/cix-native/packaging/squash/squash-cix.c",
}

PINS = {
    "squashfs_tools": WORK / "squashfs-tools-source-v1/squashfs-tools",
    "tools_overlay_pass_snapshot": WORK / "squashfs-tools-adapter-source-v3",
    "sqfsng": WORK / "squashfs-readers-v3/sqfsng-src",
    "squashfuse": WORK / "squashfs-readers-v3/squashfuse-src",
    "readers_pass_snapshot": WORK / "squashfs-readers-source-v5",
    "fuse_sdk": WORK / "fuse-sdk-v1",
    "squash_sdk": WORK / "codec-hosts-v2/squash-prefix",
    "squash_sdk_source": WORK / "codec-hosts-v2/squash-source",
    "cix_sdk": WORK / "sdk-bindings-relocated-cli-bindings-v8",
    "kernel_vm_pass_snapshot": WORK / "kernel-vm-source-v1",
    "squash_plugin_pass_snapshot": WORK / "codec-hosts-source-v8",
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(path, description):
    if not path.exists():
        raise RuntimeError("missing %s: %s" % (description, path))
    return path

def same_current(label, current, snapshot):
    current, snapshot = require(current, label + " current source"), require(snapshot, label + " passed snapshot")
    now, then = digest(current), digest(snapshot)
    if now != then:
        raise RuntimeError("current bytes differ from passed source for %s" % label)
    return {"current": str(current), "snapshot": str(snapshot), "sha256": now}

IDENTITY = {
    "tools-compressor-table": same_current("tools compressor table", TARGETS["tools-compressor-table"], PINS["tools_overlay_pass_snapshot"] / "cix_compressor_table.c"),
    "tools-wrapper": same_current("tools wrapper", TARGETS["tools-wrapper"], PINS["tools_overlay_pass_snapshot"] / "cix_wrapper.c"),
    "sqfsng-compressor": same_current("sqfsng compressor", TARGETS["sqfsng-compressor"], PINS["readers_pass_snapshot"] / "userspace/libsquashfs/cix_sqfsng_compressor.c"),
    "sqfsng-decode-bridge": same_current("sqfsng decode bridge", TARGETS["sqfsng-decode-bridge"], PINS["readers_pass_snapshot"] / "userspace/libsquashfs/cix_sqfsng_decode.c"),
    "sqfsng-read-super": same_current("sqfsng read super", TARGETS["sqfsng-read-super"], PINS["readers_pass_snapshot"] / "userspace/libsquashfs/cix_sqfsng_read_super.c"),
    "squashfuse-library-fixture-contract": same_current("Squashfuse fixture contract", TARGETS["squashfuse-library-fixture-contract"], PINS["readers_pass_snapshot"] / "userspace/tests/squashfuse_library_fixture_contract.c"),
    "squashfuse-xattr-contract": same_current("Squashfuse xattr contract", TARGETS["squashfuse-xattr-contract"], PINS["readers_pass_snapshot"] / "userspace/tests/squashfuse_xattr_contract.c"),
    "kernel-xattr-helper": same_current("kernel VM xattr helper", TARGETS["kernel-xattr-helper"], PINS["kernel_vm_pass_snapshot"] / "tests/xattr_check.c"),
    "squash-compatibility-plugin": same_current("Squash compatibility plugin", TARGETS["squash-compatibility-plugin"], PINS["squash_plugin_pass_snapshot"] / "packaging/squash/squash-cix.c"),
}
for name, path in PINS.items():
    require(path, "pinned host input " + name)

WRAPPER = OUT / "bin/cc"
WRAPPER.parent.mkdir()
WRAPPER.write_text("""#!/usr/bin/env python3
import json, os, subprocess, sys
with open(os.environ['CIX_CC_CAPTURE_LOG'], 'a', encoding='utf-8') as out:
    out.write(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}) + '\\n')
raise SystemExit(subprocess.call([os.environ['CIX_REAL_CC'], *sys.argv[1:]]))
""")
WRAPPER.chmod(0o755)

RUNS = []
def receipt():
    captured = []
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            captured.append(json.loads(line))
    selected = {}
    for label, source in TARGETS.items():
        needle = str(source)
        matches = [row for row in captured if needle in row["argv"]]
        selected[label] = matches
    (OUT / "receipt.json").write_text(json.dumps({
        "schema": "cix.compiler-capture-host.v3",
        "kind": "NEW_ANALYSIS_CONFIGURATION",
        "restrictions": ["fresh output directory", "no vendor tree writes", "no runtime qualification"],
        "pinned_inputs": {name: str(path) for name, path in PINS.items()},
        "source_identity": IDENTITY,
        "commands": RUNS,
        "compiler_invocations": captured,
        "selected_translation_units": selected,
    }, indent=2) + "\n")

def run(label, argv, cwd, extra=None):
    env = {**os.environ, "CC": str(WRAPPER), "CIX_REAL_CC": REAL_CC,
           "CIX_CC_CAPTURE_LOG": str(LOG), "PATH": str(WRAPPER.parent) + ":/usr/bin:/bin", **(extra or {})}
    result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env,
                            text=True, capture_output=True)
    RUNS.append({"label": label, "argv": [str(x) for x in argv], "cwd": str(cwd),
                 "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    receipt()
    if result.returncode:
        raise RuntimeError(label + " failed: " + (result.stderr[-4000:] or result.stdout[-4000:]))

try:
    # Reproduce the complete successful out-of-tree make setup recorded in
    # squashfs-host-v2: GNU make's include search path is required for the
    # source-owned version.mk, while the generated static_deps belongs in this
    # fresh build directory.
    tools_build = OUT / "squashfs-tools"
    tools_build.mkdir()
    # This upstream Makefile includes a cwd-local capability result before it
    # can build any target.  Reuse the exact successful result from the prior
    # qualifying out-of-tree build; it is a generated build input, never a
    # vendor-tree edit.  The earlier capture receipts record why it is needed.
    prior_static_deps = WORK / "squashfs-host-v2/tools-build/static_deps"
    require(prior_static_deps, "passed squashfs-tools static dependency capability result")
    if prior_static_deps.read_bytes() != b"STATIC_DEPS := N\n":
        raise RuntimeError("unexpected passed squashfs-tools static dependency capability result")
    shutil.copyfile(prior_static_deps, tools_build / "static_deps")
    RUNS.append({"label": "tools-static-deps-setup", "kind": "copied passed generated capability result",
                 "source": str(prior_static_deps), "sha256": digest(prior_static_deps)})
    receipt()
    run("tools-replacement-objects", ["make", "-I", PINS["squashfs_tools"], "-f", ROOT / "rust/cix-native/adapters/squashfs/tools/cix-tools.mk",
        "UPSTREAM=" + str(PINS["squashfs_tools"]), "PROFILE=" + str(ROOT / "rust/cix-native/adapters/squashfs/profile"),
        "GZIP_SUPPORT=1", "XZ_SUPPORT=0", "LZO_SUPPORT=0", "LZ4_SUPPORT=0", "ZSTD_SUPPORT=0", "XATTR_SUPPORT=1",
        "V=1", "cix_wrapper.o", "cix_compressor_table.o"], tools_build)

    # Use the exact v3 configuration modes in fresh output builds.  The vendor
    # source remains read-only; the overlay selects CIX-owned replacement TUs.
    sqfsng_build = OUT / "sqfsng-build"
    sqfsng_build.mkdir()
    run("sqfsng-configure", [PINS["sqfsng"] / "configure", "--disable-shared"], sqfsng_build)
    overlay = ROOT / "rust/cix-native/adapters/squashfs/userspace/overlay.mk"
    run("sqfsng-replacement-objects", ["make", "-f", "Makefile", "-f", overlay, "V=1",
        "CIX_READER=sqfsng", "SQFSNG_SRC=" + str(PINS["sqfsng"]),
        "lib/sqfs/comp/libsquashfs_la-compressor.lo", "lib/sqfs/libsquashfs_la-read_super.lo"], sqfsng_build)
    run("sqfsng-decode-bridge", ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-c",
        "-I" + str(ROOT / "rust/cix-native/adapters/squashfs/userspace/include"),
        TARGETS["sqfsng-decode-bridge"], "-o", OUT / "cix_sqfsng_decode.o"], OUT)

    squashfuse_build = OUT / "squashfuse-build"
    squashfuse_build.mkdir()
    fuse_env = {"PKG_CONFIG_PATH": str(PINS["fuse_sdk"] / "cix-pkgconfig")}
    run("squashfuse-configure", [PINS["squashfuse"] / "configure", "--disable-shared", "--disable-demo"], squashfuse_build, fuse_env)
    run("squashfuse-contract-objects", ["make", "-f", "Makefile", "-f", overlay, "V=1",
        "CIX_READER=squashfuse", "SQUASHFUSE_SRC=" + str(PINS["squashfuse"]),
        "squashfuse-library-fixture-contract", "squashfuse-xattr-contract"], squashfuse_build, fuse_env)

    # This helper is a guest userspace program despite its kernel qualification
    # location; it has no Linux generated-header dependency.
    run("kernel-xattr-helper", ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-c",
        TARGETS["kernel-xattr-helper"], "-o", OUT / "xattr_check.o"], OUT)

    # Preserve the passed SDK contract and capture the real command via CC.
    plugin_env = {
        "PKG_CONFIG_PATH": str(PINS["squash_sdk"] / "lib/pkgconfig"),
        "LD_LIBRARY_PATH": str(PINS["squash_sdk"] / "lib"),
        "SQUASH_SOURCE_REVISION": "713eeca85cccadde39bf57f8b59ea663a085a347",
        "CIX_NATIVE_LIBRARY": str(PINS["cix_sdk"] / "lib/libcix_native.so"),
        "CIX_INCLUDE_DIR": str(PINS["cix_sdk"] / "include"),
        "SQUASH_PLUGIN_ROOT": str(OUT / "squash-plugins"),
    }
    run("squash-compatibility-plugin", ["sh", ROOT / "rust/cix-native/packaging/squash/build-plugin.sh"], ROOT / "rust/cix-native", plugin_env)
    receipt()
except Exception as error:
    RUNS.append({"status": "failed", "error": str(error)})
    receipt()
    raise

missing = [label for label, rows in json.loads((OUT / "receipt.json").read_text())["selected_translation_units"].items() if not rows]
if missing:
    raise RuntimeError("compiler wrapper did not observe: " + ", ".join(missing))
