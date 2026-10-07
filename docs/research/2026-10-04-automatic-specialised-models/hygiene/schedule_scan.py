#!/usr/bin/env python3
"""Root-only scheduler for the final integrated Sonar hygiene gate.

One global WaveScheduler lock and one set of physical-core leases protect this
operation.  A verified transient systemd slice limits every Docker child via
Docker's cgroup-parent setting; no service-level limit is mistaken for a slice
limit.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path("/home/user/src/colour-index-compression")
HYGIENE = ROOT / "docs/research/2026-10-04-automatic-specialised-models/hygiene"
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core

CPUS = [8, 10, 12, 14]
SERVER_MEMORY = 4 * 1024**3
SCANNER_MEMORY = 1 * 1024**3
AGGREGATE_MEMORY = SERVER_MEMORY + SCANNER_MEMORY
CONTAINERS = ("cix-hygiene-sonarqube", "cix-hygiene-scanner-rust", "cix-hygiene-scanner-python", "cix-hygiene-scanner-cpp")


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, timeout=kwargs.pop("timeout", 120), **kwargs)


def _slice_receipt(slice_name: str) -> str:
    return _run([
        "sudo", "-n", "systemctl", "show", slice_name,
        "--property=MemoryMax", "--property=MemorySwapMax", "--property=AllowedCPUs", "--property=CPUQuotaPerSecUSec",
    ], capture_output=True, text=True).stdout


def _verify_slice(receipt: str) -> None:
    values = dict(line.split("=", 1) for line in receipt.splitlines() if "=" in line)
    if values.get("MemoryMax") != str(AGGREGATE_MEMORY) or values.get("MemorySwapMax") != "0":
        raise RuntimeError("transient slice memory/swap receipt mismatch")
    if values.get("AllowedCPUs") not in {"8,10,12,14", "8 10 12 14"}:
        raise RuntimeError("transient slice CPU affinity receipt mismatch")
    # systemd may render 400% as 4s or 4000000us depending on version.
    if values.get("CPUQuotaPerSecUSec") not in {"4s", "4000000us"}:
        raise RuntimeError("transient slice CPU quota receipt mismatch")


def _make_slice(slice_name: str, anchor: str) -> None:
    """Create an active transient slice, then set and verify slice properties."""
    _run([
        "sudo", "-n", "systemd-run", "--unit", anchor, "--slice", slice_name,
        "--remain-after-exit", "/bin/true",
    ])
    _run([
        "sudo", "-n", "systemctl", "set-property", "--runtime", slice_name,
        f"MemoryMax={AGGREGATE_MEMORY}", "MemorySwapMax=0", "AllowedCPUs=8,10,12,14", "CPUQuota=400%",
    ])


def _cleanup(slice_name: str, anchor: str) -> None:
    for container in CONTAINERS:
        subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True, text=True, timeout=30)
    subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True, text=True, timeout=30)
    subprocess.run(["sudo", "-n", "systemctl", "reset-failed", anchor], check=False, capture_output=True, text=True, timeout=30)
    # The slice unloads after its anchor and Docker children are gone.  Keep its
    # runtime receipt in evidence; never delete evidence as cleanup.


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-source", type=Path, required=True)
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--clippy-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cgroup-parent", default="cix-final-hygiene.slice")
    parser.add_argument("--compile-commands", type=Path)
    args = parser.parse_args()
    if not args.cgroup_parent.endswith(".slice"):
        raise ValueError("Docker systemd cgroup parent must be a .slice")
    if args.out.exists():
        raise RuntimeError("refusing to overwrite final hygiene evidence")
    native, runtime, clippy = (args.native_source.resolve(), args.runtime_source.resolve(), args.clippy_json.resolve())
    if not (native / "Cargo.toml").is_file() or not (runtime / "cix_runtime" / "__init__.py").is_file() or not clippy.is_file():
        raise RuntimeError("native source, runtime source, or fresh Clippy evidence is absent")
    args.out.mkdir(parents=True)
    freeze, lease_path = args.out / "freeze", args.out / "lease.json"
    launch_stdout, launch_stderr = args.out / "launch.stdout.log", args.out / "launch.stderr.log"
    slice_receipt = args.out / "slice-receipt.txt"
    scheduler = WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=AGGREGATE_MEMORY, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True)
    wave_lock = scheduler._wave_lock_path().open("a+")
    fcntl.flock(wave_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    leases = scheduler._lease_cores([{"physical_core": [_core(cpu) for cpu in CPUS]}])
    anchor = "cix-final-hygiene-anchor"
    try:
        _run([sys.executable, str(HYGIENE / "prepare_scan.py"), "--spec", str(HYGIENE / "final-scan-spec.json"), "--out", str(freeze)])
        _make_slice(args.cgroup_parent, anchor)
        receipt = _slice_receipt(args.cgroup_parent)
        _verify_slice(receipt)
        slice_receipt.write_text(receipt)
        lease_path.write_text(json.dumps({
            "status": "ACTIVE", "reserved_cpus": CPUS, "cgroup_parent": args.cgroup_parent,
            "aggregate_memory_bytes": AGGREGATE_MEMORY, "memory_split_bytes": {"server": SERVER_MEMORY, "scanner": SCANNER_MEMORY},
            "swap": 0, "freeze": str(freeze / "freeze-manifest.json"), "slice_receipt": str(slice_receipt),
        }, indent=2) + "\n")
        command = [
            "sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()),
            "--wait", "--pipe", "--collect", "--slice", args.cgroup_parent,
            sys.executable, str(HYGIENE / "run_scan.py"),
            "--lease", str(lease_path), "--native-source", str(native), "--runtime-source", str(runtime),
            "--freeze", str(freeze / "freeze-manifest.json"), "--clippy-json", str(clippy),
            "--cgroup-parent", args.cgroup_parent, "--out", str(args.out / "sonar"),
        ]
        if args.compile_commands:
            command.extend(("--compile-commands", str(args.compile_commands.resolve())))
        with launch_stdout.open("w") as stdout, launch_stderr.open("w") as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=1800)
        (args.out / "launch-result.json").write_text(json.dumps({"exit": result.returncode}) + "\n")
        if result.returncode:
            raise RuntimeError("final Sonar hygiene gate failed")
    finally:
        _cleanup(args.cgroup_parent, anchor)
        lease_path.write_text(json.dumps({"status": "RELEASED"}) + "\n")
        for lease in leases:
            lease.close()
        wave_lock.close()


if __name__ == "__main__":
    main()
