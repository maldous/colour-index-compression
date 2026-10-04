"""Freeze a native source snapshot and a focused existing-scheduler job.

This is private release evidence tooling, excluded from the shipping allowlist.
It prepares a job; root explicitly dispatches the resulting spec afterward.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1"
CARGO = "/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo"


def inventory(path):
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file() and not any(x in {"target", ".git"} for x in p.relative_to(path).parts)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--lib-filter", action="append", default=[])
    args = parser.parse_args()
    if not args.name.replace("-", "").isalnum():
        parser.error("name must contain letters, digits and hyphens")
    source = ROOT / "rust/cix-native"
    job = AREA / "jobs" / args.name
    snapshot = WORK / ("execution-" + args.name)
    if job.exists() or snapshot.exists():
        parser.error("immutable job identity already exists")
    before = inventory(source)
    shutil.copytree(source, snapshot, ignore=shutil.ignore_patterns("target", ".git"))
    actual = inventory(snapshot)
    after = inventory(source)
    job.mkdir(parents=True)
    (job / "source.json").write_text(json.dumps({
        "source": str(source), "snapshot": str(snapshot), "sha256": actual,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "stable_copy": before == actual == after,
    }, indent=2) + "\n")
    if before != actual or actual != after:
        raise SystemExit("source changed during snapshot: retain receipt, prepare a fresh job identity")
    common = [CARGO, "--locked", "--offline", "--manifest-path", str(snapshot / "Cargo.toml")]
    commands = [[common[0], "check", *common[1:], "--all-targets"]]
    for filt in args.lib_filter:
        commands.append([common[0], "test", *common[1:], "--lib", filt, "--", "--test-threads=2"])
    if args.test:
        command = [common[0], "test", *common[1:]]
        for target in args.test:
            command += ["--test", target]
        commands.append(command + ["--", "--test-threads=2"])
    (job / "run.py").write_text(
        "import subprocess\ncommands = " + repr(commands) + "\n"
        "for command in commands:\n"
        " print('CHECK', command, flush=True)\n"
        " result = subprocess.run(command, check=False)\n"
        " if result.returncode: raise SystemExit(result.returncode)\n"
    )
    spec = {"id": "execution-" + args.name, "cpus": [8, 10, 12, 14],
            "wall_seconds": 1200, "memory_bytes": 6000000000, "temp_bytes": 4000000000,
            "raw": str(job / "raw"), "work": str(WORK),
            "env": ["CARGO_TARGET_DIR=" + str(WORK / "target"), "CARGO_BUILD_JOBS=4",
                    "PATH=" + str(Path(CARGO).parent) + ":/usr/bin:/bin"],
            "command": ["python3", str(job / "run.py")]}
    (job / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    print(job / "spec.json")


if __name__ == "__main__":
    main()
