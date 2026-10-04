"""Root-scheduled native release validation and optimized artifact construction."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> None:
    source, work = map(Path, sys.argv[1:])
    work.mkdir(parents=True, exist_ok=True)
    cargo = "/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo"
    env = dict(os.environ, CARGO_TARGET_DIR=str(work / "target"),
               CARGO_PROFILE_RELEASE_CODEGEN_UNITS="1", CARGO_PROFILE_RELEASE_LTO="fat",
               CARGO_PROFILE_RELEASE_OPT_LEVEL="3", RUSTFLAGS="-C target-cpu=x86-64")
    steps = [
        ("format", [cargo, "fmt", "--manifest-path", str(source / "Cargo.toml"), "--", "--check"]),
        ("clippy", [cargo, "clippy", "--manifest-path", str(source / "Cargo.toml"),
                    "--locked", "--offline", "--all-targets", "--message-format=json", "-j", "4", "--", "-D", "warnings"]),
        ("optimized-tests", [cargo, "test", "--manifest-path", str(source / "Cargo.toml"),
                            "--locked", "--offline", "--release", "--all-targets", "-j", "4"]),
        ("optimized-build", [cargo, "build", "--manifest-path", str(source / "Cargo.toml"),
                            "--locked", "--offline", "--release", "--bins", "--lib", "-j", "4"]),
    ]
    receipts = []
    for name, command in steps:
        with (work / (name + ".stdout")).open("wb") as stdout, (work / (name + ".stderr")).open("wb") as stderr:
            result = subprocess.run(command, env=env, stdout=stdout, stderr=stderr)
        receipts.append({"step": name, "command": command, "exit_code": result.returncode})
        (work / "steps.json").write_text(json.dumps(receipts, indent=2) + "\n")
        if result.returncode:
            raise SystemExit(result.returncode)
    binaries = work / "bin"
    binaries.mkdir()
    files = {}
    for name in ("cix", "uncix", "cixcat", "libcix_native.so"):
        destination = binaries / name
        shutil.copy2(work / "target/release" / name, destination)
        subprocess.run(["strip", "--strip-unneeded", str(destination)], check=True)
        files[name] = {"bytes": destination.stat().st_size,
                       "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    (work / "artifacts.json").write_text(json.dumps({"files": files, "flags": {
        key: value for key, value in env.items() if key.startswith("CARGO_") or key == "RUSTFLAGS"
    }}, indent=2) + "\n")


if __name__ == "__main__":
    main()
