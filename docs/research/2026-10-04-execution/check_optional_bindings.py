"""Focused installed Linux consumer checks; run only under the root lease."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("job", type=Path)
    parser.add_argument("name")
    args = parser.parse_args()
    assert os.environ.get("CIX_RELEASE_LEASE") == "1"
    binary_root = Path(os.environ["CARGO_TARGET_DIR"]) / "debug"
    prefix = args.work / ("sdk-bindings-" + args.name)
    relocated = args.work / ("sdk-bindings-relocated-" + args.name)
    build = args.work / ("sdk-bindings-build-" + args.name)
    receipts = []

    def run(label, command, *, env=None, cwd=None, success=True, input=None):
        result = subprocess.run(command, env=env, cwd=cwd, input=input, capture_output=True)
        (args.job / (label + ".stdout.log")).write_bytes(result.stdout)
        (args.job / (label + ".stderr.log")).write_bytes(result.stderr)
        receipts.append({"label": label, "command": list(map(str, command)), "exit_code": result.returncode,
                         "expected_success": success, "cwd": str(cwd) if cwd else None})
        (args.job / "consumer-results.json").write_text(json.dumps(receipts, indent=2) + "\n")
        if (result.returncode == 0) != success:
            raise RuntimeError(f"{label}: unexpected exit {result.returncode}; see bounded job logs")
        return result

    run("sdk-configure", ["cmake", "-S", str(args.snapshot / "packaging/sdk"), "-B", str(build),
                           "-DCMAKE_INSTALL_PREFIX=" + str(prefix), "-DCMAKE_INSTALL_LIBDIR=lib",
                           "-DCIX_NATIVE_LIBRARY=" + str(binary_root / "libcix_native.so")])
    run("sdk-install", ["cmake", "--install", str(build)])
    prefix.rename(relocated)
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(args.snapshot / "bindings/python/src"),
                "CIX_PYTHON_NATIVE_LIBRARY": str(relocated / "lib/libcix_native.so"),
                "PKG_CONFIG_PATH": str(relocated / "lib/pkgconfig"),
                "LD_LIBRARY_PATH": str(relocated / "lib"), "CGO_ENABLED": "1",
                "GOCACHE": str(args.work / "go-binding-cache"), "GOMODCACHE": str(args.work / "go-binding-modcache"),
                "GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GOMAXPROCS": "4"})
    run("python-bindings", ["python3", "-m", "unittest", "discover", "-v", "-s",
                            str(args.snapshot / "bindings/python/tests")], env=env)
    run("go-bindings", ["go", "test", "-count=1", "-p=4", "./..."],
        env=env, cwd=args.snapshot / "bindings/go")

    runtime_build = args.work / ("runtime-build-" + args.name)
    runtime_prefix = args.work / ("runtime-install-" + args.name)
    runtime = args.work / ("runtime-relocated-" + args.name)
    run("runtime-requires-bridges", ["cmake", "-S", str(args.snapshot / "packaging/runtime"),
          "-B", str(args.work / ("runtime-missing-" + args.name)),
          "-DCIX_RUNTIME_CIX_EXECUTABLE=" + str(binary_root / "cix")], success=False)
    run("runtime-configure", ["cmake", "-S", str(args.snapshot / "packaging/runtime"), "-B", str(runtime_build),
          "-DCMAKE_INSTALL_PREFIX=" + str(runtime_prefix), "-DCIX_RUNTIME_CAPABILITY=native-only",
          "-DCIX_RUNTIME_CIX_EXECUTABLE=" + str(binary_root / "cix")])
    run("runtime-install", ["cmake", "--install", str(runtime_build)])
    runtime_prefix.rename(runtime)
    executable = runtime / "bin/cix"
    for alias in ("uncix", "cixcat"):
        path = runtime / "bin" / alias
        assert path.is_symlink() and os.readlink(path) == "cix"
        assert path.stat().st_ino == executable.stat().st_ino
    payload = b"relocated executable and aliases\n" * 8
    archive = run("runtime-stream-encode", [str(executable), "--fast", "--stream", "-c"], input=payload).stdout
    for alias in ("uncix", "cixcat"):
        restored = run("runtime-" + alias, [str(runtime / "bin" / alias), "-c"], input=archive).stdout
        assert restored == payload, "installed alias restoration differs"
    source_hashes = {str(path): hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
                     for path in (executable, relocated / "lib/libcix_native.so")}
    (args.job / "consumer-artifacts.json").write_text(json.dumps(source_hashes, indent=2) + "\n")


if __name__ == "__main__":
    main()
