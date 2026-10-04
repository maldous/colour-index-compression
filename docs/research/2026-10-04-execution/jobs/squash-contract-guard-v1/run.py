"""Qualify the corrected contract against the retained unchanged Squash plugin."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/squash-contract-guard-v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    WORK.mkdir()
    source = ROOT / "rust/cix-native/packaging/squash/contract.c"
    frozen = WORK / "contract.c"
    shutil.copyfile(source, frozen)
    prefix = ROOT / "benchmark-work/native-rc-check-v1/codec-hosts-v2/squash-prefix"
    plugins = ROOT / "benchmark-work/native-rc-check-v1/codec-hosts-v8/squash-plugins"
    inputs = [source, *sorted(path for path in prefix.rglob("*") if path.is_file()),
              *sorted(path for path in plugins.rglob("*") if path.is_file())]
    before = {str(path): sha(path) for path in inputs}
    receipt = {"status": "started", "source_and_host_sha256": before, "commands": [],
               "scope": "corrected Squash contract against retained v8 plugin; not a new SDK or platform build"}
    environment = {**os.environ, "LD_LIBRARY_PATH": str(prefix / "lib")}
    try:
        commands = [["cc", "-std=c11", "-O2", "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
                     "-I" + str(prefix / "include/squash-0.8"), str(frozen),
                     "-L" + str(prefix / "lib"), "-lsquash0.8", "-o", str(WORK / "contract")],
                    [str(WORK / "contract"), str(plugins)]]
        for argv in commands:
            result = subprocess.run(argv, cwd=WORK, env=environment, text=True,
                                    capture_output=True, timeout=60)
            receipt["commands"].append({"argv": argv, "cwd": str(WORK),
                "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            if result.returncode:
                raise RuntimeError("contract command failed")
        receipt["inputs_unchanged"] = all(sha(Path(name)) == value for name, value in before.items())
        if not receipt["inputs_unchanged"]:
            raise RuntimeError("source or retained host changed")
        receipt["status"] = "pass"
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        (JOB / "contract.c.txt").write_bytes(frozen.read_bytes())
        (JOB / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
