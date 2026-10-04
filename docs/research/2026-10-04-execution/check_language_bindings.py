"""Source-bound optional consumers of an explicitly qualified installed SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("job", type=Path)
    parser.add_argument("name")
    parser.add_argument("sdk", type=Path)
    parser.add_argument("--python-only", action="store_true")
    args = parser.parse_args()
    assert os.environ.get("CIX_RELEASE_LEASE") == "1"
    library = args.sdk / "lib/libcix_native.so"
    assert library.is_file()
    results = []

    def run(label, command, *, env=None, cwd=None):
        result = subprocess.run(list(map(str, command)), env=env, cwd=cwd,
                                capture_output=True, timeout=600)
        (args.job / (label + ".stdout.log")).write_bytes(result.stdout)
        (args.job / (label + ".stderr.log")).write_bytes(result.stderr)
        results.append({"label": label, "command": list(map(str, command)),
                        "exit_code": result.returncode})
        (args.job / "consumer-results.json").write_text(json.dumps(results, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{label} failed; see frozen job log")

    env = os.environ.copy()
    env.update({"LD_LIBRARY_PATH": str(args.sdk / "lib"),
                "JAVA_HOME": "/usr/lib/jvm/java-21-openjdk-amd64",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(args.snapshot / "bindings/python/src"),
                "CIX_NATIVE_LIBRARY": str(library),
                "CIX_PYTHON_NATIVE_LIBRARY": str(library)})
    if not args.python_only:
        node_build = args.work / ("node-binding-" + args.name)
        run("node-configure", ["cmake", "-S", args.snapshot / "bindings/node", "-B", node_build,
            "-DCIX_SDK_INCLUDE_DIR=" + str(args.sdk / "include"),
            "-DCIX_SDK_LIBRARY=" + str(library), "-DNODE_API_INCLUDE_DIR=/usr/include/node"], env=env)
        run("node-build", ["cmake", "--build", node_build, "--parallel", "4"], env=env)
        env["CIX_NODE_ADDON"] = str(node_build / "cix_node.node")
        run("node-contract", ["node", args.snapshot / "bindings/node/test/contract.js"], env=env)

        java_build = args.work / ("java-binding-" + args.name)
        run("java-configure", ["cmake", "-S", args.snapshot / "bindings/java", "-B", java_build,
            "-DCIX_NATIVE_INCLUDE_DIR=" + str(args.sdk / "include"),
            "-DCIX_NATIVE_LIBRARY=" + str(library)], env=env)
        run("java-build", ["cmake", "--build", java_build, "--parallel", "4"], env=env)
        classes = java_build / "classes"
        classes.mkdir()
        java_source = args.snapshot / "bindings/java/src"
        run("java-compile", ["javac", "-d", classes,
            java_source / "main/java/dev/cix/binding/NativeCix.java",
            java_source / "test/java/dev/cix/binding/Contract.java"], env=env)
        env["CIX_JNI_LIBRARY"] = str(java_build / "libcix_jni.so")
        run("java-contract", ["java", "-Xmx256m", "-cp", classes, "dev.cix.binding.Contract"], env=env)

    venv = args.work / "python-host-sdk-v1"
    python = venv / "bin/python"
    if not python.exists():
        run("python-venv", ["python3", "-m", "venv", venv], env=env)
    run("python-host-dependencies", [python, "-m", "pip", "install", "--disable-pip-version-check",
        "--no-cache-dir", "--no-index", "--find-links", args.work / "python-host-wheels-v1",
        "--report", args.job / "python-host-install.json",
        "zarr==3.4.0", "numcodecs==0.17.0", "pytest==9.1.1"], env=env)
    run("python-host-versions", [python, "-m", "pip", "freeze", "--all"], env=env)
    run("python-native-contract", [python, "-m", "unittest", "discover", "-v", "-s",
        args.snapshot / "bindings/python/tests", "-p", "test_contract.py"], env=env)
    run("python-host-contract", [python, "-m", "pytest", "-q", "-p", "no:cacheprovider",
        args.snapshot / "bindings/python/tests/test_integrations.py"], env=env)
    artifacts = [library]
    if not args.python_only:
        artifacts += [node_build / "cix_node.node", java_build / "libcix_jni.so"]
    (args.job / "consumer-artifacts.json").write_text(json.dumps({str(path):
        hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
        for path in artifacts}, indent=2) + "\n")


if __name__ == "__main__":
    main()
