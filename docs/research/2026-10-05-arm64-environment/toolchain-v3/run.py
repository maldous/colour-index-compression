"""Offline continuation of verified v2 inputs with scoped host DSO lookup."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[3]
PARENT = ROOT / "benchmark-work/native-rc-check-v1"
OLD = PARENT / "platform-linux-arm64-user-toolchain-v2"
PREFIX = OLD / "prefix"
WORK = PARENT / "platform-linux-arm64-user-toolchain-v3"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    occupied = int(subprocess.check_output(["du", "-sx", "-B1", str(PARENT)], text=True).split()[0])
    if occupied + 16_000_000 > 4_000_000_000:
        raise RuntimeError("shared work cannot admit 16MB toolchain continuation")
    WORK.mkdir()
    manifest = json.loads((AREA.parent / "toolchain-v2/packages.json").read_text())
    packages = {}
    for row in manifest["packages"]:
        archive = OLD / "downloads" / row["filename"]
        actual = digest(archive)
        if actual != row["sha256"] or archive.stat().st_size != row["compressed_bytes"]:
            raise RuntimeError("retained package identity changed")
        packages[row["filename"]] = actual
    compiler = PREFIX / "usr/bin/aarch64-linux-gnu-g++"
    qemu = PREFIX / "usr/bin/qemu-aarch64-static"
    bound = [compiler, qemu, OLD / "receipt.json", AREA / "run.py", AREA / "spec.json", AREA.parent / "toolchain-v2/packages.json"]
    bound.extend(p for p in (PREFIX / "usr/lib/x86_64-linux-gnu").glob("*.so*") if p.is_file())
    originals = {str(p): digest(p) for p in bound}
    env = {"PATH": f"{PREFIX}/usr/bin:/usr/bin:/bin",
           "LD_LIBRARY_PATH": str(PREFIX / "usr/lib/x86_64-linux-gnu")}
    commands = []
    receipt = {"status": "fail", "inputs": originals, "verified_packages": packages,
               "relocation_fix": "host binutils DSOs scoped to prefix/usr/lib/x86_64-linux-gnu; target runtime remains separate"}
    try:
        def run(name, args, process_env):
            result = subprocess.run([str(x) for x in args], text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=process_env, timeout=45)
            (WORK / (name + ".stdout")).write_text(result.stdout)
            (WORK / (name + ".stderr")).write_text(result.stderr)
            commands.append({"name": name, "argv": [str(x) for x in args], "returncode": result.returncode})
            if result.returncode:
                raise RuntimeError(f"{name}: {result.stderr[-4096:]}")
            return result.stdout
        source = WORK / "probe.cpp"
        source.write_text('#include <iostream>\n#include <vector>\n#include <numeric>\nint main(){std::vector<int> v{1,2,3,4};if(std::accumulate(v.begin(),v.end(),0)!=10)return 1;std::cout<<"CIX_ARM64_TOOLCHAIN_PASS\\n";}\n')
        binary = WORK / "probe-aarch64"
        run("compile", [compiler, f"--sysroot={PREFIX}", f"-B{PREFIX}/usr/aarch64-linux-gnu/bin/", "-O2", source, "-o", binary], env)
        file_info = run("file", ["file", binary], env)
        if "aarch64" not in file_info.lower():
            raise RuntimeError("compiler output is not ARM64")
        output = run("execute", [qemu, "-cpu", "cortex-a72", "-L", PREFIX / "usr/aarch64-linux-gnu", binary], {"PATH": "/usr/bin:/bin"})
        if output.strip() != "CIX_ARM64_TOOLCHAIN_PASS":
            raise RuntimeError("ARM64 program did not produce expected result")
        receipt.update(status="pass", binary_sha256=digest(binary), output=output,
                       toolchain_prefix=str(PREFIX), relocated_compiler_sha256=digest(compiler),
                       relocated_qemu_sha256=digest(qemu), host_library_path=env["LD_LIBRARY_PATH"],
                       compiler_version=run("compiler-version", [compiler, "--version"], env),
                       qemu_version=run("qemu-version", [qemu, "--version"], env),
                       scope="relocated C++ toolchain and actual Linux ARM64 user-mode execution; no CIX or PAQ acceptance")
    except Exception as error:
        receipt["error"] = str(error)
        raise
    finally:
        receipt["commands"] = commands
        receipt["input_hashes_after"] = {p: digest(Path(p)) for p in originals}
        if receipt["input_hashes_after"] != originals:
            receipt["status"] = "fail"
            receipt["error"] = "retained v2 input changed"
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
