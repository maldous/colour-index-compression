#!/usr/bin/env python3
"""Prepare, but never execute, finite v0.1 performance-release cells.

It writes scheduler-ready argv/environment plans only. Root dispatches each cell
under the existing WaveScheduler; this program never builds, profiles, spawns,
or imports a scheduler. Every named runtime configuration has one observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXPORT = Path("/home/user/src/cix-0.1-release")
CPUS = (16, 17, 18, 19)
LIMITS = {"aggregate_cores": 4, "aggregate_memory_bytes": 12_000_000_000,
          "aggregate_temp_bytes": 4_000_000_000, "aggregate_swap_bytes": 0,
          "dispatch": "root-owned existing WaveScheduler; no independent scheduler/job"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_binding(source: Path) -> dict:
    required = ("Cargo.toml", "Cargo.lock", "build.rs", "src/main.rs", "src/portfolio_auto.rs")
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise ValueError(f"incomplete source export: {', '.join(missing)}")
    files = {}
    for path in sorted(source.rglob("*")):
        if path.is_file() and "target" not in path.relative_to(source).parts:
            files[str(path.relative_to(source))] = sha256(path)
    return {"path": str(source), "files": files,
            "note": "all exported files are bound; documentation is allowed and public-scope review is separate"}


def frozen_input(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"missing frozen input: {path}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


def step(name: str, argv: list[str], env: dict[str, str] | None = None) -> dict:
    return {"name": name, "argv": argv, "environment": env or {}}


def cell(cell_id: str, purpose: str, steps: list[dict], cpus: list[int], memory: int,
         temp: int, wall: int, inputs: list[dict], acceptance: list[str]) -> dict:
    if not 1 <= len(cpus) <= 4:
        raise ValueError("cell requires one to four leased CPUs")
    return {"id": cell_id, "status": "PREPARED_NOT_EXECUTED", "purpose": purpose,
            "steps": steps, "inputs": inputs,
            "resources": {"cpus": cpus, "memory_max_bytes": memory, "temp_max_bytes": temp,
                          "swap_max_bytes": 0, "wall_seconds": wall},
            "observation_policy": "one observation per named runtime/profiler configuration; never retry or average",
            "acceptance": acceptance,
            "dispatch_guard": "root binds produced binaries, archives and fresh decoder output to this source binding under an active existing WaveScheduler lease"}


def codec_steps(binary: Path, decoder: Path, output: Path, input_row: dict,
                flags: list[str], label: str) -> list[dict]:
    archive, restored = output / f"{label}.cix", output / f"{label}.restored"
    return [step(f"encode-{label}", ["/usr/bin/time", "-v", "-o", str(output / f"{label}.encode.time"), str(binary), *flags, "--threads", "1", "--memory", "512MiB", "-f", "-o", str(archive), input_row["path"]]),
            step(f"decode-{label}", ["/usr/bin/time", "-v", "-o", str(output / f"{label}.decode.time"), str(decoder), "-f", "-o", str(restored), str(archive)])]


def build_arm(source: Path, root: Path, arm: tuple[str, str, str], inputs: dict[str, dict]) -> dict:
    arm_id, purpose, rustflags = arm
    target = root / "builds" / arm_id
    binary, decoder = target / "release" / "cix", target / "release" / "uncix"
    options=dict(item.split('=',1) for item in rustflags.replace('-C ', '').split())
    env = {"CARGO_TARGET_DIR": str(target), "CARGO_BUILD_JOBS": "2",
           "RUSTFLAGS": '-C target-cpu='+options['target-cpu'],
           "CARGO_PROFILE_RELEASE_OPT_LEVEL": options['opt-level'],
           "CARGO_PROFILE_RELEASE_CODEGEN_UNITS": options['codegen-units'],
           "CARGO_PROFILE_RELEASE_LTO": 'false' if options['lto']=='off' else options['lto']}
    steps = [step("build", ["cargo", "build", "--locked", "--manifest-path", str(source / "Cargo.toml"), "--release", "--bin", "cix", "--bin", "uncix", "--bin", "cixcat", "--lib", "-j2"], env)]
    steps += codec_steps(binary, decoder, root / "runs" / arm_id, inputs["kennedy"], ["--fast"], "fast")
    steps += codec_steps(binary, decoder, root / "runs" / arm_id, inputs["kennedy"], [], "default")
    steps += codec_steps(binary, decoder, root / "runs" / arm_id, inputs["kennedy"], ["--best", "--format", "cixg1", "--route", "predictor", "--block-size", "64KiB"], "constrained-best")
    return cell(arm_id, purpose, steps, [CPUS[0]], 2_000_000_000, 750_000_000, 1_200, [inputs["kennedy"]],
                ["record build wall/user/system/RSS, toolchain, binary and DSO hashes",
                 "one FAST, DEFAULT and constrained-BEST encode/decode observation from the build-bound binary",
                 "all fresh decoder SHA-256 values equal the frozen input; compare complete archives to B0",
                 "retain B0 unless a portable arm improves both DEFAULT wall and user CPU without FAST/constrained-BEST regression"])


def plan_cells(source: Path, root: Path, inputs: dict[str, dict]) -> list[dict]:
    selected, selected_decoder = root / "selected" / "cix", root / "selected" / "uncix"
    profile_output = root / "profiling"
    common = [str(selected), "--threads", "1", "--memory", "512MiB", "-f", "-o", str(profile_output / "default.cix"), inputs["kennedy"]["path"]]
    probes = (("P1", "call-graph availability", ["perf", "record", "--call-graph", "dwarf", "--", *common]),
              ("P2", "counter availability", ["perf", "stat", "--no-big-num", "-e", "cycles,instructions,cache-misses,branch-misses,context-switches,cpu-migrations", "--", *common]),
              ("P3", "syscall/I-O attribution", ["strace", "-f", "-c", "-o", str(profile_output / "strace.summary"), *common]),
              ("P4", "lock-contention availability", ["perf", "lock", "record", "--", *common]))
    cells = [cell(name, purpose, [step("probe", argv)], [CPUS[0]], 1_073_741_824, 256_000_000, 300, [inputs["kennedy"]],
                  ["bind selected binary/decoder hashes", "complete archive plus fresh decode must match input", "permission/unsupported becomes terminal UNAVAILABLE only after this retained probe receipt"])
             for name, purpose, argv in probes]
    arms = (("B0", "portable opt3 fat-LTO CGU1 baseline", "-C target-cpu=x86-64 -C opt-level=3 -C lto=fat -C codegen-units=1"),
            ("B1", "portable opt2 no-LTO CGU16", "-C target-cpu=x86-64 -C opt-level=2 -C lto=off -C codegen-units=16"),
            ("B2", "portable opt3 no-LTO CGU16", "-C target-cpu=x86-64 -C opt-level=3 -C lto=off -C codegen-units=16"),
            ("B3", "portable opt3 ThinLTO CGU16", "-C target-cpu=x86-64 -C opt-level=3 -C lto=thin -C codegen-units=16"),
            ("B4", "portable opt3 fat-LTO CGU16", "-C target-cpu=x86-64 -C opt-level=3 -C lto=fat -C codegen-units=16"),
            ("B5", "host-native opt3 fat-LTO CGU1; host-only", "-C target-cpu=native -C opt-level=3 -C lto=fat -C codegen-units=1"))
    cells.extend(build_arm(source, root, arm, inputs) for arm in arms)
    pgo_raw, pgo_merge = root / "pgo" / "raw", root / "pgo" / "merged.profdata"
    generated, used = root / "builds" / "G-generate", root / "builds" / "G-use"
    generate_env = {"CARGO_TARGET_DIR": str(generated), "CARGO_BUILD_JOBS": "2", "RUSTFLAGS": f"-C target-cpu=x86-64 -Cprofile-generate={pgo_raw}"}
    cells.append(cell("G-BUILD-GENERATE", "build PGO instrumentation", [step("build", ["cargo", "build", "--locked", "--manifest-path", str(source / "Cargo.toml"), "--release", "--bin", "cix", "--bin", "uncix", "-j2"], generate_env)], [CPUS[1]], 2_000_000_000, 1_000_000_000, 1_200, [], ["record generated binary hashes and raw profile directory identity"]))
    generated_binary, generated_decoder = generated / "release" / "cix", generated / "release" / "uncix"
    cells.append(cell("G-TRAIN-FAST", "one PGO FAST training observation", codec_steps(generated_binary, generated_decoder, root / "runs" / "G-fast", inputs["alice"], ["--fast"], "fast"), [CPUS[1]], 1_073_741_824, 1_000_000_000, 600, [inputs["alice"]], ["exact restoration", "retain raw-profile count/inventory"]))
    cells.append(cell("G-TRAIN-DEFAULT", "one PGO DEFAULT training observation", codec_steps(generated_binary, generated_decoder, root / "runs" / "G-default", inputs["book1"], [], "default"), [CPUS[1]], 1_073_741_824, 1_000_000_000, 600, [inputs["book1"]], ["exact restoration", "training remains disjoint from held-out Kennedy"]))
    cells.append(cell("G-MERGE", "merge PGO profiles", [step("merge", ["llvm-profdata", "merge", "-output", str(pgo_merge), str(pgo_raw)])], [CPUS[2]], 1_000_000_000, 1_000_000_000, 300, [], ["record llvm-profdata version and merged-profile SHA-256"]))
    use_env = {"CARGO_TARGET_DIR": str(used), "CARGO_BUILD_JOBS": "2", "RUSTFLAGS": f"-C target-cpu=x86-64 -Cprofile-use={pgo_merge}"}
    cells.append(cell("G-BUILD-USE", "build PGO-use artifact", [step("build", ["cargo", "build", "--locked", "--manifest-path", str(source / "Cargo.toml"), "--release", "--bin", "cix", "--bin", "uncix", "-j2"], use_env)], [CPUS[2]], 2_000_000_000, 1_000_000_000, 1_200, [], ["record PGO-use binary hashes and merged-profile binding"]))
    used_binary, used_decoder = used / "release" / "cix", used / "release" / "uncix"
    heldout = codec_steps(used_binary, used_decoder, root / "runs" / "G-heldout", inputs["kennedy"], ["--fast"], "fast")
    heldout += codec_steps(used_binary, used_decoder, root / "runs" / "G-heldout", inputs["kennedy"], [], "default")
    heldout += codec_steps(used_binary, used_decoder, root / "runs" / "G-heldout", inputs["kennedy"], ["--best", "--format", "cixg1", "--route", "predictor", "--block-size", "64KiB"], "constrained-best")
    cells.append(cell("G-HELDOUT", "PGO held-out FAST/DEFAULT/constrained-BEST", heldout, [CPUS[2]], 1_073_741_824, 512_000_000, 1_200, [inputs["kennedy"]], ["one exact restoration per named profile", "compare complete archives to B0", "retain PGO only if all profiles avoid material CPU/RSS regression and one clearly improves"]))
    cells.append(cell("A1", "probe whether public export has an audit allocator target", [step("metadata-probe", ["cargo", "metadata", "--locked", "--manifest-path", str(source / "Cargo.toml"), "--no-deps", "--format-version", "1"])], [CPUS[3]], 512_000_000, 64_000_000, 120, [], ["if audit target/feature is absent, record terminal UNAVAILABLE only after this probe; do not add audit dependencies to public package"]))
    alloc = codec_steps(selected, selected_decoder, root / "runs" / "A2", inputs["kennedy"], [], "default")
    cells.append(cell("A2-SYSTEM", "system allocator sensitivity", alloc, [CPUS[3]], 1_073_741_824, 256_000_000, 300, [inputs["kennedy"]], ["exact archive/decode; record wall/user/system/RSS/cgroup high-water"]))
    jemalloc = [dict(item, environment={"LD_PRELOAD": "/lib/x86_64-linux-gnu/libjemalloc.so.2"}) for item in alloc]
    cells.append(cell("A2-JEMALLOC", "preloaded jemalloc sensitivity", jemalloc, [CPUS[3]], 1_073_741_824, 256_000_000, 300, [inputs["kennedy"]], ["exact archive/decode; record library hash/mappings; never add a package dependency from this screen"]))
    for strategy in ("blocks", "candidates"):
        for workers in (1, 2, 4):
            cpus = list(CPUS[:workers])
            command = [str(selected), "--format", "cixg1", "--parallelism", strategy, "--threads", str(workers), "--block-size", "64KiB", "--memory", "512MiB", "-f", "-o", str(root / "runs" / f"S-{strategy}-{workers}.cix"), inputs["kennedy"]["path"]]
            cells.append(cell(f"S-{strategy.upper()}-{workers}", f"CIXG1 {strategy} scaling point", [step("encode", command)], cpus, 2_000_000_000, 256_000_000, 300, [inputs["kennedy"]], ["exact archive identity across equal format/policy worker counts", "record task/thread and ordered-queue peaks, wall/user CPU and memory admission"]))
    cells.append(cell("S-M6", "serial CIXM6 FAST anchor", [step("encode", [str(selected), "--format", "cixm6", "--fast", "--threads", "1", "--block-size", "64KiB", "--memory", "16MiB", "-f", "-o", str(root / "runs" / "S-m6.cix"), inputs["kennedy"]["path"]])], [CPUS[3]], 512_000_000, 128_000_000, 300, [inputs["kennedy"]], ["fresh serial decode exact; no decoder-parallel claim"]))
    return cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-export", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output, source, artifact_root = args.output.resolve(), args.source_export.resolve(), args.artifact_root.resolve()
    if output.exists():
        raise SystemExit("refusing to overwrite an existing prepared queue")
    inputs = {"kennedy": frozen_input(ROOT / "benchmark-work/canterbury/kennedy.xls"), "alice": frozen_input(ROOT / "benchmark-work/canterbury/alice29.txt"), "book1": frozen_input(ROOT / "benchmark-work/calgary/book1")}
    plan = {"schema": "cix-v0.1-performance-release-plan-v3", "status": "PREPARED_NOT_EXECUTED", "created_at": datetime.now(timezone.utc).isoformat(), "source_export": source_binding(source), "artifact_root": str(artifact_root), "inputs": inputs, "aggregate_limits": LIMITS, "cells": plan_cells(source, artifact_root, inputs), "notes": ["P probes become UNAVAILABLE only after attempted receipt.", "B0-B5 are unique build arms; no duplicate B0/B6.", "PGO generation happens during build; Alice/book1 train and Kennedy is held out.", "No unconstrained BEST, Silesia, Hutter, acquisition, or broad benchmark route is present."]}
    output.mkdir(parents=True)
    plan_path = output / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": plan["status"], "plan": str(plan_path), "cells": len(plan["cells"])}, sort_keys=True))


if __name__ == "__main__":
    main()
