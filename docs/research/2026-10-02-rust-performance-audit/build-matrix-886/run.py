#!/usr/bin/env python3
"""Bounded, reproducible compiler-setting experiment for native CIX.

This deliberately measures a small screening matrix first, then performs five
counterbalanced repetitions only for the portable baseline and any screened
winner.  The input labels are evidence labels: no encoder option depends on
them.  All compression is single-threaded to isolate code generation from
selector parallelism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = Path(os.environ.get("CIX_AUDIT_FIXTURE_ROOT", "/home/user/src/colour-index-compression")).resolve()
MANIFEST = ROOT / "rust/cix-native/Cargo.toml"
FROZEN_SOURCE = "8865bfbccba354b02920da86c7088c17e5f96aab"
CPUS = "20,22"
MEMORY_BYTES = 2_000_000_000
TEMP_LIMIT_BYTES = 512_000_000
REPETITIONS = 5
VARIANTS = (
    ("portable-opt3-fat-cgu1", {"CARGO_PROFILE_RELEASE_OPT_LEVEL": "3", "CARGO_PROFILE_RELEASE_LTO": "fat", "CARGO_PROFILE_RELEASE_CODEGEN_UNITS": "1", "RUSTFLAGS": "-C target-cpu=x86-64"}),
    ("portable-opt3-fat-cgu16", {"CARGO_PROFILE_RELEASE_OPT_LEVEL": "3", "CARGO_PROFILE_RELEASE_LTO": "fat", "CARGO_PROFILE_RELEASE_CODEGEN_UNITS": "16", "RUSTFLAGS": "-C target-cpu=x86-64"}),
)
WORKLOADS = (
    ("fast-kennedy", FIXTURE_ROOT / "benchmark-work/canterbury/kennedy.xls", ("--fast", "--threads", "1"), "ordinary FAST"),
    ("default-kennedy", FIXTURE_ROOT / "benchmark-work/canterbury/kennedy.xls", ("--threads", "1"), "ordinary DEFAULT"),
    ("best-constrained-g1-lz-grammar", FIXTURE_ROOT / "benchmark-work/canterbury/grammar.lsp", ("--best", "--format", "cixg1", "--route", "lz", "--threads", "1"), "BEST constrained to CIXG1/LZ; not an unconstrained size claim"),
)

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def command_version(command: list[str]) -> str:
    return subprocess.check_output(command, text=True).strip()

def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def limit() -> None:
    # The caller owns the aggregate cgroup MemoryMax/MemorySwapMax policy.
    # RLIMIT_AS is deliberately not used: virtual address space is not RSS.
    return None

def run_measured(command: list[str], cwd: Path) -> tuple[dict, bytes]:
    # RUSAGE_CHILDREN.ru_maxrss is cumulative and cannot yield a valid
    # per-command peak by subtraction. GNU time records the child peak.
    metric = tempfile.NamedTemporaryFile(prefix="cix-build-metric-", delete=False)
    metric.close()
    started = time.perf_counter_ns()
    p = subprocess.run(["/usr/bin/time", "-o", metric.name, "-f", "%U %S %e %M", *command], cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       preexec_fn=limit, check=False)
    elapsed = (time.perf_counter_ns() - started) / 1e9
    if p.returncode:
        raise RuntimeError(f"failed ({p.returncode}): {' '.join(command)}\n{p.stderr.decode(errors='replace')}")
    user, system, _reported_wall, rss = Path(metric.name).read_text().split()
    Path(metric.name).unlink()
    return ({"wall_seconds": elapsed,
             "cpu_seconds": float(user) + float(system), "peak_rss_kib": int(rss)}, p.stdout)

def build(name: str, flags: dict[str, str], directory: Path) -> tuple[dict, Path, Path]:
    build_dir = directory / name
    build_dir.mkdir()
    env = os.environ.copy()
    env.update(flags)
    env["CARGO_TARGET_DIR"] = str(build_dir / "target")
    env["CARGO_BUILD_JOBS"] = "1"
    command = ["taskset", "-c", CPUS, "cargo", "build", "--release", "--locked", "--manifest-path", str(MANIFEST), "--bin", "cix", "--bin", "uncix"]
    started = time.perf_counter_ns()
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, preexec_fn=limit)
    elapsed = (time.perf_counter_ns() - started) / 1e9
    (build_dir / "build.stdout.log").write_text(p.stdout)
    (build_dir / "build.stderr.log").write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f"build {name} failed; see {build_dir}")
    cix, uncix = build_dir / "target/release/cix", build_dir / "target/release/uncix"
    used = sum(p.stat().st_size for p in build_dir.rglob("*") if p.is_file())
    aggregate = sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
    if aggregate > TEMP_LIMIT_BYTES:
        raise RuntimeError(f"build matrix exceeded temporary-space cap: {aggregate}")
    return ({"name": name, "flags": flags, "command": command, "compile_wall_seconds": elapsed,
             "temporary_bytes": used, "aggregate_temporary_bytes": aggregate,
             "cix_sha256": digest(cix), "uncix_sha256": digest(uncix),
             "cix_bytes": cix.stat().st_size, "uncix_bytes": uncix.stat().st_size}, cix, uncix)

def evaluate(name: str, cix: Path, uncix: Path, directory: Path, repetitions: int) -> list[dict]:
    rows = []
    for repeat in range(repetitions):
        # Flip workload order every repetition so cold-cache effects do not
        # always accrue to one profile.
        order = WORKLOADS if repeat % 2 == 0 else tuple(reversed(WORKLOADS))
        for label, input_path, flags, qualification in order:
            archive = directory / f"{name}-{repeat}-{label}.cix"
            measured, output = run_measured(["taskset", "-c", CPUS, str(cix), *flags, "-c", str(input_path)], ROOT)
            archive.write_bytes(output)
            decoded, restored = run_measured(["taskset", "-c", CPUS, str(uncix), "-c", str(archive)], ROOT)
            source_hash, restored_hash = digest(input_path), hashlib.sha256(restored).hexdigest()
            if source_hash != restored_hash:
                raise RuntimeError(f"own decode mismatch: {name}/{label}/{repeat}")
            rows.append({"variant": name, "repeat": repeat, "workload": label, "qualification": qualification,
                         "input_bytes": input_path.stat().st_size, "input_sha256": source_hash,
                         "archive_bytes": archive.stat().st_size, "archive_sha256": digest(archive),
                         "encode": measured, "decode": decoded,
                         "encode_mib_per_second": input_path.stat().st_size / (1024 * 1024) / measured["wall_seconds"],
                         "decode_mib_per_second": input_path.stat().st_size / (1024 * 1024) / decoded["wall_seconds"]})
    return rows

def cross_decode(rows: list[dict], binaries: dict[str, Path], directory: Path) -> list[dict]:
    checks = []
    # Test each distinct produced archive with every independently built decoder.
    archives = sorted({(r["archive_sha256"], r["input_sha256"], r["workload"], r["repeat"], r["variant"]) for r in rows})
    for archive_hash, input_hash, workload, repeat, producer in archives:
        archive = directory / f"{producer}-{repeat}-{workload}.cix"
        for consumer, uncix in binaries.items():
            _, restored = run_measured(["taskset", "-c", CPUS, str(uncix), "-c", str(archive)], ROOT)
            actual = hashlib.sha256(restored).hexdigest()
            if actual != input_hash:
                raise RuntimeError(f"cross decode mismatch {producer}->{consumer}: {workload}/{repeat}")
            checks.append({"producer": producer, "consumer": consumer, "archive_sha256": archive_hash,
                           "workload": workload, "repeat": repeat, "restoration_sha256": actual})
    return checks

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="perform bounded local builds and measurements")
    ap.add_argument("--pgo", action="store_true", help="record PGO availability only; PGO runs require a separately frozen train/evaluation split")
    args = ap.parse_args()
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != FROZEN_SOURCE:
        raise SystemExit("refusing a source revision other than the frozen build-matrix-886 checkpoint")
    evidence = Path(__file__).resolve().parent
    freeze = {"schema": "cix-build-matrix-886-v1", "source_revision": FROZEN_SOURCE, "cpus": CPUS,
              "memory_bytes": MEMORY_BYTES, "temporary_bytes": TEMP_LIMIT_BYTES, "fixture_root": str(FIXTURE_ROOT), "repetitions": REPETITIONS,
              "rustc": command_version(["rustc", "-Vv"]), "cargo": command_version(["cargo", "-V"]),
              "kernel": platform.platform(), "workloads": [{"label": w[0], "input": str(w[1]), "sha256": digest(w[1]), "flags": w[2], "qualification": w[3]} for w in WORKLOADS],
              "variants": [{"name": n, "flags": f} for n, f in VARIANTS],
              "pgo": {"status": "not-run", "reason": "requires separately frozen, disjoint CCA train/evaluation split", "llvm_profdata": str(Path(command_version(["rustc", "--print", "sysroot"])) / "lib/rustlib/x86_64-unknown-linux-gnu/bin/llvm-profdata")}}
    dump(evidence / "freeze.json", freeze)
    if not args.run:
        return 0
    with tempfile.TemporaryDirectory(prefix="cix-build-matrix-886-", dir="/tmp") as temp:
        root = Path(temp)
        variants, rows, decoders = [], [], {}
        for name, flags in VARIANTS:
            metadata, cix, uncix = build(name, flags, root)
            variants.append(metadata)
            decoders[name] = uncix
            rows += evaluate(name, cix, uncix, root, REPETITIONS)
        cross = cross_decode(rows, decoders, root)
        dump(evidence / "results.json", {"schema": "cix-build-matrix-886-v1", "status": "completed", "freeze_sha256": digest(evidence / "freeze.json"), "variants": variants, "measurements": rows, "cross_decode": cross})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
