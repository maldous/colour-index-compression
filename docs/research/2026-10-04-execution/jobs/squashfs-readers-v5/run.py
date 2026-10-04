"""Deferred RC40 public-libsquashfuse qualification without a library rebuild."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
REPO = Path(__file__).resolve().parents[5]
WORK = REPO / "benchmark-work/native-rc-check-v1"
OUT = WORK / "squashfs-readers-v5"
OUT.mkdir(exist_ok=False)
BUILD = WORK / "squashfs-readers-v4/squashfuse-build"
SNAPSHOT = WORK / "squashfs-readers-source-v4"
VENDOR = WORK / "squashfs-readers-v3/squashfuse-src"
FIXTURE = WORK / "squashfs-host-v3/fixture"
ROWS = []

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def receipt():
    (OUT / "receipt.json").write_text(json.dumps(ROWS, indent=2) + "\n")

def run(args, cwd, env, timeout=120):
    process = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=timeout)
    ROWS.append({"argv": [str(arg) for arg in args], "cwd": str(cwd),
                 "returncode": process.returncode, "stdout": process.stdout,
                 "stderr": process.stderr})
    receipt()
    if process.returncode:
        raise RuntimeError(process.stderr[-6000:] or process.stdout[-6000:])

def binary(name):
    for path in (BUILD / ".libs" / name, BUILD / name):
        if path.is_file():
            return path
    raise RuntimeError("missing contract binary " + name)

require((BUILD / ".libs/libsquashfuse.a").is_file(), "v4 static libsquashfuse SDK is unavailable")
require((BUILD / "Makefile").is_file(), "v4 generated Makefile is unavailable")
require((SNAPSHOT / "userspace/overlay.mk").is_file(), "fresh frozen adapter snapshot is unavailable")
require((VENDOR / "configure").is_file(), "pinned v3 Squashfuse source is unavailable")
fixture_receipt = json.loads((FIXTURE / "receipt.json").read_text())
require(len(fixture_receipt["entries"]) == 304, "fixture must contain exactly 304 files")

env = {**os.environ, "CFLAGS": "-O2 -Wall -Wextra", "CPPFLAGS": "", "TMPDIR": str(OUT / "tmp")}
Path(env["TMPDIR"]).mkdir()
# This target's only new object is the CIX-owned verifier. It links directly to
# the existing static archive and does not name a library target as a make
# prerequisite, so no v4 SDK/library object can be rebuilt in this retry.
make = ["make", "-f", "Makefile", "-f", SNAPSHOT / "userspace/overlay.mk",
        "CIX_READER=squashfuse", "SQUASHFUSE_SRC=" + str(VENDOR),
        "squashfuse-library-fixture-contract-static", "squashfuse-xattr-contract-static"]
run(make, BUILD, env)
library_contract = binary("squashfuse-library-fixture-contract-static")
run([library_contract, FIXTURE / "image.sqfs", FIXTURE / "root", "304", "1"], OUT, env)

# Recompile the CIX-owned API contract against the same retained static SDK,
# then verify both retained fixture xattrs.
xattr_contract = binary("squashfuse-xattr-contract-static")
for path, name, value in (("repeated", "user.cix.fixture", "6578706572696d656e74616c"),
                          ("tiny/0", "user.cix.tiny", "796573")):
    run([xattr_contract, FIXTURE / "image.sqfs", path, name, value], OUT, env)

for bad in ("unknown-method.sqfs", "malformed-inode-profile-version.sqfs"):
    result = subprocess.run([str(library_contract), str(FIXTURE / bad), str(FIXTURE / "root"), "304", "1"],
                            cwd=OUT, env=env, capture_output=True, timeout=120)
    ROWS.append({"negative": bad, "returncode": result.returncode})
    receipt()
    require(result.returncode != 0, "library verifier accepted " + bad)

final = OUT / "final"
final.mkdir()
shutil.copy2(library_contract, final / "squashfuse-library-fixture-contract")
shutil.copy2(xattr_contract, final / "squashfuse-xattr-contract-static")
(OUT / "final-binaries.sha256.json").write_text(json.dumps(
    {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(final.iterdir())}, indent=2) + "\n")
ROWS.append({"status": "passed", "fixture_files": 304, "fixture_directories": 1, "xattr_api_checks": 2, "library_rebuilt": False})
receipt()
