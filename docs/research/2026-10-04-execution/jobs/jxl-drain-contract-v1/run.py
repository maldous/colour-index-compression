"""Qualify the shared JXL drain against the retained pinned native dependency."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/jxl-drain-contract-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    WORK.mkdir()
    current = ROOT / "rust/cix-native/codecs/jxl"
    source, build, prefix = (WORK / name for name in ("source", "build", "prefix"))
    shutil.copytree(current, source)
    dependency = ROOT / "benchmark-work/native-rc-check-v1/jxl-prefix-v3"
    before = {str(path.relative_to(source)): sha(path) for path in source.rglob("*") if path.is_file()}
    deps = {str(path.relative_to(dependency)): sha(path) for path in dependency.rglob("*") if path.is_file()}
    receipt = {"status": "started", "source_sha256": before, "dependency_root": str(dependency),
               "dependency_sha256": deps, "commands": [], "scope": "Generated focused boundary/equivalence checks; no corpus or throughput benchmark"}

    def save():
        body = json.dumps(receipt, indent=2) + "\n"
        (WORK / "receipt.json").write_text(body)
        (JOB / "receipt.json").write_text(body)

    env = {**os.environ, "LD_LIBRARY_PATH": str(prefix / "lib") + ":" + str(dependency / "lib")}

    def run(label, argv):
        start = time.monotonic()
        with (WORK / (label + ".stdout.log")).open("xb") as out, (WORK / (label + ".stderr.log")).open("xb") as err:
            value = subprocess.run(argv, cwd=WORK, env=env, stdout=out, stderr=err, check=False)
        receipt["commands"].append({"label": label, "argv": argv, "cwd": str(WORK), "returncode": value.returncode,
                                    "elapsed_seconds": time.monotonic() - start})
        save()
        for suffix in ("stdout.log", "stderr.log"):
            shutil.copyfile(WORK / (label + "." + suffix), JOB / (label + "." + suffix))
        if value.returncode:
            raise RuntimeError(label + " failed")

    try:
        run("configure", ["cmake", "-S", str(source), "-B", str(build), "-G", "Ninja",
                          "-DCIX_JXL_ROOT=" + str(dependency), "-DCMAKE_BUILD_TYPE=Release",
                          "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_INSTALL_PREFIX=" + str(prefix)])
        run("build", ["cmake", "--build", str(build), "--parallel", "4"])
        run("install", ["cmake", "--install", str(build)])
        run("compile-contract", ["c++", "-std=c++17", "-O2", "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
             str(source / "tests/jxl_drain_contract.cpp"), "-I", str(prefix / "include/cix"), "-L", str(prefix / "lib"),
             "-Wl,-rpath," + str(prefix / "lib"), "-lcix_jxl_bridge", "-o", str(WORK / "jxl_drain_contract")])
        run("contract", [str(WORK / "jxl_drain_contract")])
        old_job = ROOT / "docs/research/2026-10-04-execution/jobs/jxl-bridge-v3"
        for script in ("check_jxl_bridge.py", "planar_fixture.py"):
            shutil.copyfile(old_job / script, WORK / script)
        receipt["fixture_scripts_sha256"] = {script: sha(WORK / script) for script in ("check_jxl_bridge.py", "planar_fixture.py")}
        python = str(ROOT / ".venv/bin/python")
        run("gray-regression", [python, str(WORK / "check_jxl_bridge.py"), str(prefix / "lib/libcix_jxl_bridge.so"), str(WORK / "fixtures")])
        run("planar-regression", [python, str(WORK / "planar_fixture.py"), "--native", "--bridge", str(prefix / "lib/libcix_jxl_bridge.so"), "--result", str(WORK / "planar-result.json")])
        receipt["source_unchanged"] = all(sha(current / name) == identity for name, identity in before.items())
        receipt["dependencies_unchanged"] = all(sha(dependency / name) == identity for name, identity in deps.items())
        if not receipt["source_unchanged"] or not receipt["dependencies_unchanged"]:
            raise RuntimeError("source/dependency changed during qualification")
        receipt["installed_sha256"] = {str(path.relative_to(prefix)): sha(path) for path in prefix.rglob("*") if path.is_file()}
        receipt["status"] = "pass"
        shutil.copyfile(build / "compile_commands.json", JOB / "compile_commands.json")
        shutil.copyfile(WORK / "planar-result.json", JOB / "planar-result.json")
        for path in (WORK / "fixtures").glob("*.json"):
            shutil.copyfile(path, JOB / path.name)
    except Exception as error:
        receipt["status"] = "fail"
        receipt["error"] = str(error)
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
