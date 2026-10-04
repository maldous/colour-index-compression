"""Deferred RC40 userspace-reader qualification.  Scheduled only by root."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
REPO = Path(__file__).resolve().parents[5]
WORK = REPO / "benchmark-work/native-rc-check-v1"
OUT = WORK / "squashfs-readers-v3"
OUT.mkdir(exist_ok=False)
FIXTURE = WORK / "squashfs-host-v3/fixture"
ADAPTERS = WORK / "squashfs-readers-source-v3/userspace"
PROFILE = WORK / "squashfs-readers-source-v3/profile"
ROWS = []

def digest_tree(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}

def receipt():
    (OUT / "receipt.json").write_text(json.dumps(ROWS, indent=2) + "\n")

def run(args, cwd, env, timeout=600):
    process = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=timeout)
    ROWS.append({"argv": [str(arg) for arg in args], "cwd": str(cwd),
                 "returncode": process.returncode, "stdout": process.stdout,
                 "stderr": process.stderr})
    receipt()
    if process.returncode:
        raise RuntimeError(process.stderr[-6000:] or process.stdout[-6000:])

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def extracted_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}

def cleanup_object_cache(build, label):
    cache = [p for p in build.rglob("*") if p.suffix in {".o", ".lo", ".la"} or p.name == ".libs"]
    manifest = {p.relative_to(build).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in cache if p.is_file()}
    (OUT / (label + "-object-cache.sha256.json")).write_text(json.dumps(manifest, indent=2) + "\n")
    for path in sorted(cache, key=lambda p: len(p.parts), reverse=True):
        if path.is_dir(): shutil.rmtree(path)
        elif path.exists(): path.unlink()

sqfsng_seed = WORK / "sqfsng-source-v1"
squashfuse_seed = WORK / "squashfuse-source-v1"
seed_before = {"sqfsng": digest_tree(sqfsng_seed), "squashfuse": digest_tree(squashfuse_seed)}
(OUT / "pinned-source-before.sha256.json").write_text(json.dumps(seed_before, indent=2) + "\n")

# Autogen requires generated files in its source tree.  It therefore runs only
# in disposable copies; the pinned seed source manifest is checked afterward.
ngsrc, fusrc = OUT / "sqfsng-src", OUT / "squashfuse-src"
for source, copy in ((sqfsng_seed, ngsrc), (squashfuse_seed, fusrc)):
    if copy.exists(): shutil.rmtree(copy)
    shutil.copytree(source, copy, ignore=shutil.ignore_patterns(".git"))

env = {**os.environ,
       "CFLAGS": "-O2 -Wall -Wextra",
       "CPPFLAGS": "",
       "TMPDIR": str(OUT / "tmp")}
Path(env["TMPDIR"]).mkdir(exist_ok=True)
run([ngsrc / "autogen.sh"], ngsrc, env)
run([fusrc / "autogen.sh"], fusrc, env)
ngbuild, fubuild = OUT / "sqfsng-build", OUT / "squashfuse-build"
for build in (ngbuild, fubuild):
    if build.exists(): shutil.rmtree(build)
    build.mkdir()
run([ngsrc / "configure", "--disable-shared"], ngbuild, env)
run([fusrc / "configure", "--disable-shared", "--disable-fuse", "--enable-demo"], fubuild, env)

overlay = ADAPTERS / "overlay.mk"
ngmake = ["make", "-f", "Makefile", "-f", overlay, "CIX_READER=sqfsng", "SQFSNG_SRC=" + str(ngsrc), "-j4", "rdsquashfs"]
fumake = ["make", "-f", "Makefile", "-f", overlay, "CIX_READER=squashfuse", "SQUASHFUSE_SRC=" + str(fusrc), "-j4"]
run(ngmake, ngbuild, env)
run([*fumake, "squashfuse_extract", "squashfuse-xattr-contract"], fubuild, env)

fixture_receipt = json.loads((FIXTURE / "receipt.json").read_text())
expected = {name: row["sha256"] for name, row in fixture_receipt["entries"].items()}
require(len(expected) == 304, "fixture must contain exactly 304 files")
tools = {"sqfsng": (ngbuild / "rdsquashfs", ["-X", "-u", "/", "-p"]),
         "squashfuse": (fubuild / "squashfuse_extract", [])}
for label, (tool, options) in tools.items():
    destination = OUT / (label + "-out")
    if destination.exists(): shutil.rmtree(destination)
    if label == "sqfsng":
        run([tool, *options, destination, FIXTURE / "image.sqfs"], OUT, env)
    else:
        run([tool, FIXTURE / "image.sqfs", "-a"], OUT, env)
        destination = OUT / "squashfs-root"
    require(extracted_hashes(destination) == expected, label + " did not restore all 304 fixture files")
    if label == "sqfsng":
        for path, row in fixture_receipt["entries"].items():
            for attr, value in row.get("xattrs", {}).items():
                require(os.getxattr(destination / path, attr).hex() == value, "sqfsng xattr mismatch")
    for bad in ("unknown-method.sqfs", "malformed-inode-profile-version.sqfs"):
        negative = subprocess.run([str(tool), *(options if label == "sqfsng" else []), str(OUT / (label + "-bad")), str(FIXTURE / bad)] if label == "sqfsng" else [str(tool), str(FIXTURE / bad), "-a"], cwd=OUT, env=env, capture_output=True, timeout=120)
        ROWS.append({"negative": [label, bad], "returncode": negative.returncode})
        receipt(); require(negative.returncode != 0, label + " accepted " + bad)

# squashfuse_extract intentionally has no xattr restore feature; qualify its
# decoder through the actual public library API for both fixture xattrs.
for path, name, value in (("repeated", "user.cix.fixture", "6578706572696d656e74616c"), ("tiny/0", "user.cix.tiny", "796573")):
    run([fubuild / "squashfuse-xattr-contract", FIXTURE / "image.sqfs", path, name, value], fubuild, env)

seed_after = {"sqfsng": digest_tree(sqfsng_seed), "squashfuse": digest_tree(squashfuse_seed)}
(OUT / "pinned-source-after.sha256.json").write_text(json.dumps(seed_after, indent=2) + "\n")
require(seed_before == seed_after, "pinned upstream source bytes changed")

# Preserve final reader binaries before deleting the reproducible object cache.
# Libtool wrapper scripts point into .libs, so retain the real executables.
final = OUT / "final"
if final.exists(): shutil.rmtree(final)
final.mkdir()
for source, name in ((ngbuild / ".libs/rdsquashfs", "rdsquashfs"),
                     (fubuild / ".libs/squashfuse_extract", "squashfuse_extract"),
                     (fubuild / ".libs/squashfuse-xattr-contract", "squashfuse-xattr-contract")):
    if not source.is_file():
        source = source.parent.parent / source.name
    require(source.is_file(), "missing final binary " + str(source))
    shutil.copy2(source, final / name)
(OUT / "final-binaries.sha256.json").write_text(json.dumps(
    {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(final.iterdir())}, indent=2) + "\n")

# Only the reproducible object cache is removed after its own hash receipt is retained.
for build, label in ((ngbuild, "sqfsng"), (fubuild, "squashfuse")):
    cleanup_object_cache(build, label)
ROWS.append({"status": "passed", "fixture_files": 304, "xattr_api_checks": 2})
receipt()
