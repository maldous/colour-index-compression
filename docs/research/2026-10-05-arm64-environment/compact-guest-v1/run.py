"""Acquire one signed Ubuntu ARM64 kernel and boot a generated minimal guest."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import urllib.request

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
PARENT = ROOT / "benchmark-work/native-rc-check-v1"
WORK = PARENT / "platform-linux-arm64-compact-guest-v1"
PREFIX = PARENT / "platform-linux-arm64-user-toolchain-v2/prefix"
INPUT = json.loads((AREA / "input.json").read_text())
CAP = 64_000_000


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def occupied(path):
    return int(subprocess.check_output(["du", "-sx", "-B1", str(path)]).split()[0])


def checked_run(name, argv, **kwargs):
    result = subprocess.run([str(x) for x in argv], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=120, **kwargs)
    (WORK / (name + ".stdout")).write_text(result.stdout)
    (WORK / (name + ".stderr")).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError(f"{name}: {result.stderr[-3000:]}")
    return result.stdout


def acquire():
    if occupied(PARENT) + CAP > 4_000_000_000:
        raise RuntimeError("64MB aggregate reservation unavailable")
    WORK.mkdir()
    checked_run("signature", ["gpgv", "--keyring", "/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg",
                              AREA / "SHA256SUMS.gpg", AREA / "SHA256SUMS"])
    if INPUT["sha256"] not in (AREA / "SHA256SUMS").read_text():
        raise RuntimeError("kernel hash is not publisher-signed")
    path = WORK / "vmlinuz"
    received = 0
    with urllib.request.urlopen(INPUT["url"], timeout=45) as response, path.open("xb") as out:
        if response.geturl() != INPUT["url"]:
            raise RuntimeError("unexpected kernel redirect")
        while chunk := response.read(min(1 << 20, INPUT["compressed_bytes"] + 1 - received)):
            received += len(chunk)
            if received > INPUT["compressed_bytes"]:
                raise RuntimeError("kernel download too large")
            out.write(chunk)
    if received != INPUT["compressed_bytes"] or digest(path) != INPUT["sha256"]:
        raise RuntimeError("kernel input identity mismatch")
    return {"status": "pass", "input": INPUT, "local_cap_bytes": CAP,
            "allocated_bytes": occupied(WORK), "scope": "publisher-verified ARM64 Linux kernel acquired"}


def initramfs(entries):
    out = io.BytesIO()
    for inode, (name, mode, data, major, minor) in enumerate(entries + [("TRAILER!!!", 0, b"", 0, 0)], 1):
        encoded = name.encode() + b"\0"
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(encoded), 0]
        out.write(b"070701" + b"".join(f"{v:08x}".encode() for v in fields))
        out.write(encoded)
        out.write(b"\0" * (-out.tell() % 4))
        out.write(data)
        out.write(b"\0" * (-out.tell() % 4))
    return gzip.compress(out.getvalue(), compresslevel=1, mtime=0)


def smoke():
    if json.loads((WORK / "acquire-receipt.json").read_text())["status"] != "pass":
        raise RuntimeError("acquisition must pass first")
    original = json.loads((PARENT / "platform-linux-arm64-user-toolchain-v3/receipt.json").read_text())
    if original["status"] != "pass":
        raise RuntimeError("toolchain execution proof missing")
    cpp = PARENT / "platform-linux-arm64-user-toolchain-v3/probe-aarch64"
    if digest(cpp) != original["binary_sha256"] or digest(WORK / "vmlinuz") != INPUT["sha256"]:
        raise RuntimeError("retained executable/kernel identity changed")
    init = WORK / "init"
    compiler = PREFIX / "usr/bin/aarch64-linux-gnu-gcc"
    env = {"PATH": f"{PREFIX}/usr/bin:/usr/bin:/bin",
           "LD_LIBRARY_PATH": str(PREFIX / "usr/lib/x86_64-linux-gnu")}
    checked_run("compile-init", [compiler, f"--sysroot={PREFIX}", f"-B{PREFIX}/usr/aarch64-linux-gnu/bin/",
                                "-O2", "-static", AREA / "init.c", "-o", init], env=env)
    entries = [(x, stat.S_IFDIR | 0o755, b"", 0, 0) for x in ["dev", "proc", "tmp", "lib", "lib/aarch64-linux-gnu"]]
    entries += [("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
                ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3)]
    inputs = {"init": init, "probe-cpp": cpp}
    runtime = PREFIX / "usr/aarch64-linux-gnu/lib"
    inputs["lib/ld-linux-aarch64.so.1"] = runtime / "ld-linux-aarch64.so.1"
    for name in ["libc.so.6", "libm.so.6", "libgcc_s.so.1", "libstdc++.so.6"]:
        inputs["lib/aarch64-linux-gnu/" + name] = runtime / name
    for name, path in inputs.items():
        entries.append((name, stat.S_IFREG | 0o755, path.read_bytes(), 0, 0))
    archive = WORK / "initramfs.cpio.gz"
    archive.write_bytes(initramfs(entries))
    kernel = WORK / "vmlinuz"
    fds = ()
    # Ubuntu publishes gzip-compressed Image. Keep decompression in memory so
    # this small test guest does not retain another large temporary kernel copy.
    if kernel.read_bytes()[:2] == b"\x1f\x8b":
        fd = os.memfd_create("cix-arm64-kernel", 0)
        with gzip.open(kernel, "rb") as source:
            kernel_bytes = source.read(128_000_001)
        if len(kernel_bytes) > 128_000_000:
            raise RuntimeError("unexpected expanded kernel size")
        with os.fdopen(os.dup(fd), "wb") as image_output:
            image_output.write(kernel_bytes)
        fds = (fd,)
        kernel_argument = f"/proc/self/fd/{fd}"
    else:
        kernel_argument = str(kernel)
    argv = ["qemu-system-aarch64", "-machine", "virt-8.2", "-cpu", "cortex-a72", "-accel", "tcg,thread=single",
            "-smp", "1", "-m", "512", "-nodefaults", "-nographic", "-serial", "stdio", "-monitor", "none",
            "-nic", "none", "-kernel", kernel_argument, "-initrd", str(archive),
            "-append", "console=ttyAMA0 rdinit=/init panic=-1"]
    (WORK / "qemu-command.json").write_text(json.dumps(argv, indent=2) + "\n")
    try:
        serial = checked_run("guest-serial", argv, pass_fds=fds)
    finally:
        for fd in fds:
            os.close(fd)
    for marker in ["CIX_ARM64_TOOLCHAIN_PASS", "CIX_ARM64_COMPACT_GUEST_PASS"]:
        if not re.search(r"(?m)^" + marker + r"\r?$", serial):
            raise RuntimeError("missing exact guest execution success marker")
    return {"status": "pass", "execution_kind": "full-system ARM64 Linux QEMU TCG emulation on x86_64",
            "scope": "minimal generated guest with official Ubuntu kernel; C++ runtime executed; not full Ubuntu userspace",
            "inputs": {name: digest(path) for name, path in inputs.items()}, "kernel": INPUT,
            "initramfs_sha256": digest(archive), "qemu_version": checked_run("qemu-version", ["qemu-system-aarch64", "--version"]),
            "qemu_sha256": digest("/usr/bin/qemu-system-aarch64"), "serial_sha256": digest(WORK / "guest-serial.stdout"),
            "allocated_bytes": occupied(WORK), "aggregate_allocated_bytes": occupied(PARENT),
            "not_established": ["CIX full-product ARM64 qualification", "PAQ ARM64 qualification", "native ARM speed"]}


if __name__ == "__main__":
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise SystemExit("root lease required")
    mode = sys.argv[1]
    if mode not in {"acquire", "smoke"}:
        raise SystemExit("invalid mode")
    bound_paths = [AREA / "run.py", AREA / "init.c", AREA / "input.json", AREA / (mode + "-spec.json"), AREA / "SHA256SUMS", AREA / "SHA256SUMS.gpg"]
    inputs_before = {str(p): digest(p) for p in bound_paths}
    receipt = {"status": "fail"}
    try:
        receipt = acquire() if mode == "acquire" else smoke()
        if occupied(WORK) > CAP:
            raise RuntimeError("guest exceeds local64MB reservation")
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        receipt["job_inputs_before"] = inputs_before
        receipt["job_inputs_after"] = {str(p): digest(p) for p in bound_paths}
        if receipt["job_inputs_before"] != receipt["job_inputs_after"]:
            receipt.update(status="fail", error="job inputs changed during execution")
        if WORK.exists():
            (WORK / (mode + "-receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
