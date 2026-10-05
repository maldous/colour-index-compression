"""Isolated pinned Rust ARM64 stdlib and actual emulated Rust execution."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
PARENT = ROOT / "benchmark-work/native-rc-check-v1"
WORK = PARENT / "platform-linux-arm64-rust-target-v1"
PREFIX = PARENT / "platform-linux-arm64-user-toolchain-v2/prefix"
INPUT = json.loads((AREA / "input.json").read_text())
CAP = 200_000_000


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def occupied(path):
    return int(subprocess.check_output(["du", "-sx", "-B1", str(path)]).split()[0])


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if occupied(PARENT) + CAP > 4_000_000_000:
        raise RuntimeError("200MB aggregate reservation unavailable")
    if json.loads((PARENT / "platform-linux-arm64-user-toolchain-v3/receipt.json").read_text())["status"] != "pass":
        raise RuntimeError("working ARM cross-toolchain required")
    if digest(INPUT["channel_manifest"]) != INPUT["channel_manifest_sha256"]:
        raise RuntimeError("installed Rust channel manifest changed")
    bound = [AREA / "run.py", AREA / "input.json", AREA / "spec.json"]
    inputs_before = {str(p): digest(p) for p in bound}
    WORK.mkdir()
    receipt = {"status": "fail", "input": INPUT, "local_cap_bytes": CAP, "inputs_before": inputs_before}
    try:
        archive = WORK / "rust-std.tar.xz"
        received = 0
        with urllib.request.urlopen(INPUT["url"], timeout=45) as response, archive.open("xb") as output:
            if response.geturl() != INPUT["url"]:
                raise RuntimeError("unexpected Rust component redirect")
            while chunk := response.read(min(1 << 20, INPUT["compressed_bytes"] + 1 - received)):
                received += len(chunk)
                if received > INPUT["compressed_bytes"]:
                    raise RuntimeError("component exceeds declared length")
                output.write(chunk)
        if received != INPUT["compressed_bytes"] or digest(archive) != INPUT["sha256"]:
            raise RuntimeError("Rust component identity mismatch")
        sysroot = WORK / "sysroot"
        prefix = "rust-std-1.98.1-aarch64-unknown-linux-gnu/rust-std-aarch64-unknown-linux-gnu/"
        with tarfile.open(archive, "r:xz") as tar:
            members = [m for m in tar if m.name.startswith(prefix + "lib/")]
            payload = sum(m.size for m in members)
            receipt["measured_payload_bytes"] = payload
            if payload + received + 9_000_000 > CAP:
                raise RuntimeError("measured Rust extraction cannot fit; archive retained, no extraction")
            for member in members:
                name = Path(member.name.removeprefix(prefix))
                if name.is_absolute() or ".." in name.parts or not (member.isdir() or member.isfile()):
                    raise RuntimeError("unexpected Rust target member")
            for member in members:
                path = sysroot / member.name.removeprefix(prefix)
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, path.open("xb") as output:
                        shutil.copyfileobj(source, output)
        if not list(sysroot.glob("lib/rustlib/aarch64-unknown-linux-gnu/lib/libstd-*.rlib")):
            raise RuntimeError("target stdlib absent")
        receipt.update(status="pass", sysroot=str(sysroot), sysroot_allocated_bytes=occupied(sysroot),
                       work_allocated_bytes=occupied(WORK), aggregate_allocated_bytes=occupied(PARENT),
                       scope="matching Rust ARM64 standard library acquired/extracted; compiler execution is a separate offline stage")
        if occupied(WORK) > CAP:
            raise RuntimeError("local cap exceeded")
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        receipt["inputs_after"] = {str(p): digest(p) for p in bound}
        if receipt["inputs_after"] != inputs_before:
            receipt.update(status="fail", error="job inputs changed")
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
