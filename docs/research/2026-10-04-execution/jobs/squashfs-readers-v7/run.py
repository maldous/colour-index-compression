"""Deferred leased Squashfuse mount qualification; always unmounts its own path."""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
REPO = Path(__file__).resolve().parents[5]
WORK = REPO / "benchmark-work/native-rc-check-v1"
OUT = WORK / "squashfs-readers-v7"
OUT.mkdir(exist_ok=False)
SOURCE = WORK / "squashfs-readers-v3/squashfuse-src"
SNAPSHOT = WORK / "squashfs-readers-source-v5"
FIXTURE = WORK / "squashfs-host-v3/fixture"
ROWS = []

def receipt():
    (OUT / "receipt.json").write_text(json.dumps(ROWS, indent=2) + "\n")

def fail(message, code=1):
    ROWS.append({"status": "failed", "message": message, "code": code})
    receipt()
    raise SystemExit(code)

def run(args, cwd, env, timeout=300):
    process = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                             capture_output=True, text=True, timeout=timeout)
    ROWS.append({"argv": [str(arg) for arg in args], "cwd": str(cwd),
                 "returncode": process.returncode, "stdout": process.stdout,
                 "stderr": process.stderr})
    receipt()
    if process.returncode:
        fail(process.stderr[-6000:] or process.stdout[-6000:])

def mounted(path):
    target = str(path.resolve())
    with open("/proc/self/mountinfo", encoding="utf-8") as stream:
        return any(" " + target + " " in line for line in stream)

def tree_hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}

def unmount(mountpoint, server):
    if mounted(mountpoint):
        result = subprocess.run(["/bin/fusermount3", "-u", "-z", "--", str(mountpoint)],
                                capture_output=True, text=True, timeout=30)
        ROWS.append({"unmount": str(mountpoint), "returncode": result.returncode,
                     "stderr": result.stderr})
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
    receipt()

sdk = WORK / "fuse-sdk-v1"
os.environ["PKG_CONFIG_PATH"] = str(sdk / "cix-pkgconfig")

if not Path("/dev/fuse").is_char_device():
    fail("missing usable /dev/fuse", 3)
pkg = subprocess.run(["pkg-config", "--exists", "fuse3"])
if pkg.returncode != 0:
    fail("missing development SDK: install libfuse3-dev (pkg-config fuse3, fuse.h, fuse_lowlevel.h)", 3)
if not (SOURCE / "configure").is_file() or not (SNAPSHOT / "userspace/overlay.mk").is_file():
    fail("missing pinned source or fresh adapter snapshot", 3)

env = {**os.environ, "CFLAGS": "-O2 -Wall -Wextra", "CPPFLAGS": "", "TMPDIR": str(OUT / "tmp")}
Path(env["TMPDIR"]).mkdir()
includedir = subprocess.check_output(["pkg-config", "--variable=includedir", "fuse3"], text=True).strip()
libdir = subprocess.check_output(["pkg-config", "--variable=libdir", "fuse3"], text=True).strip()
build = OUT / "squashfuse-fuse-build"
build.mkdir()
# The pinned upstream pkg-config branch sets FUSE_USE_VERSION=32;
# explicit include/lib arguments take its legacy API branch instead.
run([SOURCE / "configure", "--disable-shared", "--disable-demo"], build, env)
run(["make", "-f", "Makefile", "-f", SNAPSHOT / "userspace/overlay.mk",
     "CIX_READER=squashfuse", "SQUASHFUSE_SRC=" + str(SOURCE), "-j4", "squashfuse"], build, env)

fixture = json.loads((FIXTURE / "receipt.json").read_text())
expected = {path: row["sha256"] for path, row in fixture["entries"].items()}
if len(expected) != 304:
    fail("fixture no longer has exactly 304 files")
mountpoint = OUT / "mount"
mountpoint.mkdir()
server_log = (OUT / "squashfuse.stderr.log").open("w")
server = subprocess.Popen([str(build / "squashfuse"), str(FIXTURE / "image.sqfs"), str(mountpoint), "-f"],
                          cwd=OUT, env=env, stdout=subprocess.DEVNULL, stderr=server_log, text=True)
try:
    deadline = time.monotonic() + 45
    while not mounted(mountpoint) and time.monotonic() < deadline:
        if server.poll() is not None:
            fail("Squashfuse exited before mounting")
        time.sleep(0.1)
    if not mounted(mountpoint):
        fail("Squashfuse mount timed out")
    if tree_hashes(mountpoint) != expected:
        fail("mounted Squashfuse tree did not restore all 304 files")
    for path, row in fixture["entries"].items():
        for name, value in row.get("xattrs", {}).items():
            if os.getxattr(mountpoint / path, name).hex() != value:
                fail("mounted xattr mismatch: " + path)
    ROWS.append({"status": "passed", "fixture_files": 304, "mounted_xattrs": 2})
finally:
    unmount(mountpoint, server)
    server_log.close()
receipt()
