"""Deferred RC40 v4: reuse the passed v3 sqfsng build; rebuild Squashfuse only."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
REPO = Path(__file__).resolve().parents[5]
WORK = REPO / "benchmark-work/native-rc-check-v1"
V3 = WORK / "squashfs-readers-v3"
OUT = WORK / "squashfs-readers-v4"
OUT.mkdir(exist_ok=False)
FIXTURE = WORK / "squashfs-host-v3/fixture"
SNAPSHOT = WORK / "squashfs-readers-source-v3"
FUSE_SOURCE = V3 / "squashfuse-src"
SQFSNG = V3 / "sqfsng-build/rdsquashfs"
ROWS = []

def digest_tree(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}

def receipt():
    (OUT / "receipt.json").write_text(json.dumps(ROWS, indent=2) + "\n")

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def run(args, cwd, env, timeout=600):
    process = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=timeout)
    ROWS.append({"argv": [str(arg) for arg in args], "cwd": str(cwd),
                 "returncode": process.returncode, "stdout": process.stdout,
                 "stderr": process.stderr})
    receipt()
    if process.returncode:
        raise RuntimeError(process.stderr[-6000:] or process.stdout[-6000:])

def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}

def final_binary(build, name):
    for candidate in (build / ".libs" / name, build / name):
        if candidate.is_file():
            return candidate
    raise RuntimeError("missing final binary " + name)

def cleanup_object_cache(build):
    candidates = [p for p in build.rglob("*") if p.suffix in {".o", ".lo", ".la"} or p.name == ".libs"]
    manifest = {p.relative_to(build).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in candidates if p.is_file()}
    (OUT / "squashfuse-object-cache.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for path in sorted(candidates, key=lambda p: len(p.parts), reverse=True):
        if path.is_dir(): shutil.rmtree(path)
        elif path.exists(): path.unlink()

# v3 remains immutable evidence. Its seed manifest proves the source used by
# both v3 and this retry was not edited. The retry runs no autogen step.
v3_seed_manifest = json.loads((V3 / "pinned-source-before.sha256.json").read_text())
current_seeds = {"sqfsng": digest_tree(WORK / "sqfsng-source-v1"),
                 "squashfuse": digest_tree(WORK / "squashfuse-source-v1")}
require(current_seeds == v3_seed_manifest, "pinned source bytes differ from v3 receipt")
require(SQFSNG.is_file(), "passed v3 sqfsng binary is unavailable")
require((FUSE_SOURCE / "configure").is_file(), "v3 autogen Squashfuse source is unavailable")
require((SNAPSHOT / "userspace/overlay.mk").is_file(), "frozen v3 adapter snapshot is unavailable")

env = {**os.environ, "CFLAGS": "-O2 -Wall -Wextra", "CPPFLAGS": "", "TMPDIR": str(OUT / "tmp")}
Path(env["TMPDIR"]).mkdir(exist_ok=True)
build = OUT / "squashfuse-build"
build.mkdir()
# The pinned configure.ac defaults demo support to yes. --enable-demo is not a
# supported option and produced the v3 undefined-main failure.
run([FUSE_SOURCE / "configure", "--disable-shared", "--disable-fuse"], build, env)
make = ["make", "-f", "Makefile", "-f", SNAPSHOT / "userspace/overlay.mk",
        "CIX_READER=squashfuse", "SQUASHFUSE_SRC=" + str(FUSE_SOURCE), "-j4"]
run([*make, "squashfuse_extract", "squashfuse-xattr-contract"], build, env)

fixture = json.loads((FIXTURE / "receipt.json").read_text())
expected = {path: entry["sha256"] for path, entry in fixture["entries"].items()}
require(len(expected) == 304, "fixture must contain exactly 304 files")

# Re-run full image decode for both readers. rdsquashfs restores xattrs; the
# Squashfuse library contract checks the same values because extract omits them.
ng_out = OUT / "sqfsng-out"
run([SQFSNG, "-X", "-u", "/", "-p", ng_out, FIXTURE / "image.sqfs"], OUT, env)
require(hashes(ng_out) == expected, "reused sqfsng did not restore all 304 files")
for path, entry in fixture["entries"].items():
    for name, value in entry.get("xattrs", {}).items():
        require(os.getxattr(ng_out / path, name).hex() == value, "sqfsng xattr mismatch: " + path)

run([build / "squashfuse_extract", FIXTURE / "image.sqfs", "-a"], OUT, env)
fuse_out = OUT / "squashfs-root"
require(hashes(fuse_out) == expected, "Squashfuse did not restore all 304 files")
for path, name, value in (("repeated", "user.cix.fixture", "6578706572696d656e74616c"),
                          ("tiny/0", "user.cix.tiny", "796573")):
    run([build / "squashfuse-xattr-contract", FIXTURE / "image.sqfs", path, name, value], build, env)

for label, tool, options in (("sqfsng", SQFSNG, ["-X", "-u", "/", "-p"]),
                             ("squashfuse", build / "squashfuse_extract", [])):
    for bad in ("unknown-method.sqfs", "malformed-inode-profile-version.sqfs"):
        args = [tool, *options, OUT / (label + "-bad"), FIXTURE / bad] if label == "sqfsng" else [tool, FIXTURE / bad, "-a"]
        result = subprocess.run([str(arg) for arg in args], cwd=OUT, env=env, capture_output=True, timeout=120)
        ROWS.append({"negative": [label, bad], "returncode": result.returncode})
        receipt()
        require(result.returncode != 0, label + " accepted " + bad)

final = OUT / "final"
final.mkdir()
shutil.copy2(SQFSNG, final / "rdsquashfs-v3-reused")
for name in ("squashfuse_extract", "squashfuse-xattr-contract"):
    shutil.copy2(final_binary(build, name), final / name)
(OUT / "final-binaries.sha256.json").write_text(json.dumps(
    {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(final.iterdir())}, indent=2) + "\n")
cleanup_object_cache(build)
ROWS.append({"status": "passed", "fixture_files": 304, "xattr_api_checks": 2, "sqfsng": "v3-reused"})
receipt()
