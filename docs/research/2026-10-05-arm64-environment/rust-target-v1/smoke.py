"""Offline Rust target compiler and generated threaded/I/O execution check."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
PARENT = ROOT / "benchmark-work/native-rc-check-v1"
WORK = PARENT / "platform-linux-arm64-rust-target-v1"
PREFIX = PARENT / "platform-linux-arm64-user-toolchain-v2/prefix"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__ == "__main__":
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise SystemExit("root lease required")
    if json.loads((WORK / "receipt.json").read_text())["status"] != "pass":
        raise SystemExit("target acquisition must pass")
    rustc = Path("/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustc")
    compiler = PREFIX / "usr/bin/aarch64-linux-gnu-gcc"
    qemu = PREFIX / "usr/bin/qemu-aarch64-static"
    bound = [AREA / "smoke.py", AREA / "smoke-spec.json", WORK / "receipt.json", rustc, compiler, qemu]
    before = {str(p): digest(p) for p in bound}
    source = WORK / "probe.rs"
    source.write_text('fn main(){let v:Vec<u64>=(0..1024).collect();let n=std::thread::spawn(move||v.iter().sum::<u64>()).join().unwrap();assert_eq!(n,523776);let p=std::env::args().nth(1).unwrap();std::fs::write(&p,n.to_le_bytes()).unwrap();assert_eq!(std::fs::read(p).unwrap(),n.to_le_bytes());println!("CIX_ARM64_RUST_PASS");}\n')
    binary = WORK / "probe-rust"
    receipt = {"status": "fail", "inputs_before": before, "commands": []}
    try:
        def run(name, argv, env):
            result = subprocess.run([str(x) for x in argv], text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=60, env=env)
            (WORK / (name + ".stdout")).write_text(result.stdout)
            (WORK / (name + ".stderr")).write_text(result.stderr)
            receipt["commands"].append({"argv": [str(x) for x in argv], "returncode": result.returncode})
            if result.returncode:
                raise RuntimeError(result.stderr[-4000:])
            return result.stdout
        env = {"PATH": f"{PREFIX}/usr/bin:/usr/bin:/bin", "LD_LIBRARY_PATH": str(PREFIX / "usr/lib/x86_64-linux-gnu")}
        version = run("version", [rustc, "--version"], env)
        if not version.startswith("rustc 1.98.1 "):
            raise RuntimeError("rustc version differs from target component")
        run("compile", [rustc, "--target", "aarch64-unknown-linux-gnu", "--sysroot", WORK / "sysroot",
                        "-C", "opt-level=2", "-C", "strip=debuginfo", "-C", f"linker={compiler}",
                        "-C", f"link-arg=--sysroot={PREFIX}", source, "-o", binary], env)
        output = run("execute", [qemu, "-cpu", "cortex-a72", "-L", PREFIX / "usr/aarch64-linux-gnu", binary, WORK / "probe.dat"], {"PATH": "/usr/bin:/bin"})
        if output.strip() != "CIX_ARM64_RUST_PASS":
            raise RuntimeError("missing exact Rust execution marker")
        receipt.update(status="pass", rustc=version, binary_sha256=digest(binary), output=output,
                       scope="ARM64 Rust compilation and actual QEMU user-mode heap/thread/file execution; not CIX product qualification")
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        receipt["inputs_after"] = {str(p): digest(p) for p in bound}
        if receipt["inputs_after"] != before:
            receipt.update(status="fail", error="smoke inputs changed")
        (WORK / "smoke-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
