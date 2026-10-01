#!/usr/bin/env python3
"""Freeze, run and collect the native Rust CIXG1 Silesia stream benchmark wave.

Only the already-verified local Silesia members in the frozen native plan are
used. Historical Python and Silesia matrix results remain separate controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT = Path(__file__).resolve().parents[1]
INPUT_PLAN = ROOT / "docs/research/2026-10-01-rust-native/silesia-plan.json"
AREA = ROOT / "docs/research/2026-10-01-rust-native/silesia-rust-cixg1-v1"
PROFILES = {
    "fast": {"level": 1, "block_bytes": 32768, "memory_mib": 256},
    "current": {"level": 6, "block_bytes": 32768, "memory_mib": 384},
    "size": {"level": 9, "block_bytes": 65536, "memory_mib": 512},
}
FORMATS = ("cixg1",)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def physical_cpus() -> list[int]:
    result: list[int] = []
    seen: set[tuple[str, str]] = set()
    for cpu in sorted(os.sched_getaffinity(0)):
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        key = ((topology / "physical_package_id").read_text(), (topology / "core_id").read_text())
        if key not in seen:
            result.append(cpu)
            seen.add(key)
        if len(result) == 4:
            break
    if len(result) != 4:
        raise RuntimeError("the frozen Silesia wave requires four distinct physical CPUs")
    return result


def source_manifest() -> tuple[dict, str]:
    plan = json.loads(INPUT_PLAN.read_text())
    if len(plan.get("inputs", [])) != 12:
        raise RuntimeError("expected the frozen twelve-member Silesia input plan")
    verified = []
    for item in plan["inputs"]:
        source = Path(item["path"])
        if not source.is_file() or source.stat().st_size != item["bytes"] or sha(source) != item["sha256"]:
            raise RuntimeError(f"frozen Silesia input identity mismatch: {source}")
        verified.append(dict(item))
    return plan, hashlib.sha256(canonical(verified)).hexdigest()


def build_paths() -> list[str]:
    paths = [
        "dist/cix",
        "dist/uncix",
        "benchmarks/silesia_rust_client.py",
        "benchmarks/silesia_rust_cixg1_matrix.py",
        "benchmarks/hutter_bounded_runner.py",
        "benchmarks/hutter_experiment_scheduler.py",
        "rust/cix-native/Cargo.toml",
        "rust/cix-native/Cargo.lock",
    ]
    paths.extend(
        str(path.relative_to(ROOT))
        for path in sorted((ROOT / "rust/cix-native/src").rglob("*.rs"))
    )
    return paths


def prepare() -> None:
    if AREA.exists():
        raise RuntimeError(f"native Rust Silesia experiment already exists; preserve it: {AREA}")
    plan, input_digest = source_manifest()
    cpus = physical_cpus()
    manifest_dir = AREA / "manifests"
    manifest_dir.mkdir(parents=True)
    build = build_paths()
    native_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    cells = []
    for index, item in enumerate(plan["inputs"]):
        for format_name in FORMATS:
            for profile_name, setting in PROFILES.items():
                config = {
                    "method": "cix-rust-native",
                    "format": format_name,
                    "profile": profile_name,
                    **setting,
                    "route_policy": "native Rust bounded selector; not Python timing-dependent selector parity",
                    "repetitions": 1,
                    "warmups": 0,
                    "native_commit": native_commit,
                }
                slug_source = {"input_sha256": item["sha256"], "configuration": config}
                slug = hashlib.sha256(canonical(slug_source)).hexdigest()[:16]
                name = f"{item['name']}-{format_name}-{profile_name}-{slug}"
                adapter = str(ROOT / "benchmarks/silesia_rust_client.py")
                archive = "{workdir}/candidate.cix"
                restored = "{workdir}/restored.bin"
                encode = [
                    "/usr/bin/time",
                    "-v",
                    "-o",
                    "{workdir}/encode.time.txt",
                    sys.executable,
                    adapter,
                    "encode",
                    "{source}",
                    archive,
                    "--profile",
                    profile_name,
                    "--format",
                    format_name,
                    "--workdir",
                    "{workdir}",
                ]
                decode = [
                    "/usr/bin/time",
                    "-v",
                    "-o",
                    "{workdir}/decode.time.txt",
                    sys.executable,
                    adapter,
                    "decode",
                    archive,
                    restored,
                    "--profile",
                    profile_name,
                    "--format",
                    format_name,
                    "--workdir",
                    "{workdir}",
                ]
                manifest = {
                    "hypothesis": "The merged native Rust CIX client can produce independently verified CIXG1 and CIXM6 archives for every existing Silesia member at bounded fast/current/size settings.",
                    "matched_control": "Same complete Silesia source hashes and profile mapping across the two native formats; prior Python CIXG1 and other codec rows remain separately versioned controls.",
                    "input": {
                        "path": item["path"],
                        "offset": 0,
                        "length": item["bytes"],
                        "sha256": item["sha256"],
                        "full_asset_sha256": item["sha256"],
                        "dataset": "official Silesia",
                    },
                    "configuration": config,
                    "initial_state": "empty native model state per complete Silesia member; format-internal block history follows the frozen stream definition",
                    "mechanism": "Packaged Rust cix/uncix binaries; CIXG1 is the generic CIX stream path and CIXM6 is the fully ported legacy-mode selector. Entire physical archive size, frame/footer/checksum bytes and independently measured decode are included.",
                    "budget": {
                        "cpu": cpus[len(cells) % len(cpus)],
                        "max_rss_bytes": 2_000_000_000,
                        "max_temp_bytes": 400_000_000,
                        "wall_seconds": 300,
                        "swap_bytes": 0,
                    },
                    "stage": "exposed Silesia measurement; not a holdout or a general-dataset claim",
                    "promotion_criteria": "Complete archive; separate archive-only Rust decode; exact source length and SHA-256 restoration; all failures and resource exclusions remain visible.",
                    "exposure": "The existing official Silesia inputs and historic Silesia results are already exposed. No new data acquisition or other dataset comparison is included.",
                    "encode_command": encode,
                    "decode_command": decode,
                    "artifacts": {"archive": archive, "restored": restored},
                    "build_paths": build,
                    "resource_accounting": "WaveScheduler: four physical cores, 12 GB aggregate memory, 4 GB aggregate temporary budget, one CPU and 2 GB/400 MB/300 s per cell, swap disabled.",
                }
                manifest_path = manifest_dir / f"{name}.json"
                manifest_path.write_bytes(canonical(manifest) + b"\n")
                frozen, manifest_sha = load_manifest(manifest_path)
                cells.append(
                    {
                        "cell_id": f"silesia-rust-v2-{slug}",
                        "owner": "/root",
                        "manifest_path": str(manifest_path.relative_to(ROOT)),
                        "output_dir": str((AREA / "runs" / name).relative_to(ROOT)),
                        "expected_manifest_sha256": manifest_sha,
                        "expected_build_sha256": build_identity(frozen, ROOT),
                        "label": item["name"],
                        "format": format_name,
                        "profile": profile_name,
                        "input_bytes": item["bytes"],
                        "input_sha256": item["sha256"],
                    }
                )
    environment = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "reference_commit": plan.get("configuration", {}).get("python_commit"),
        "native_code_commit": native_commit,
        "input_plan": str(INPUT_PLAN.relative_to(ROOT)),
        "input_plan_sha256": sha(INPUT_PLAN),
        "verified_member_manifest_sha256": input_digest,
        "hardware_cpus": cpus,
        "limits": {"cores": 4, "ram_bytes": 12_000_000_000, "temporary_bytes": 4_000_000_000, "swap_bytes": 0},
        "cell_limits": {"rss_bytes": 2_000_000_000, "temporary_bytes": 400_000_000, "phase_seconds": 300},
        "formats": list(FORMATS),
        "profiles": PROFILES,
        "cells": len(cells),
        "policy": "Silesia files only. Historic measurements remain immutable; native mode results get new experiment IDs.",
    }
    (AREA / "environment.json").write_bytes(canonical(environment) + b"\n")
    (AREA / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    (AREA / "coverage.json").write_text(json.dumps({"status": "FROZEN_NOT_YET_RUN", "cells": cells}, indent=2) + "\n")
    print(json.dumps({"frozen_cells": len(cells), "formats": FORMATS, "profiles": list(PROFILES), "cpus": cpus}, sort_keys=True))


def run(trial: bool = False) -> None:
    cells = json.loads((AREA / "cells.json").read_text())
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    pending = [
        cell for cell in cells
        if not scheduler._terminal_path(cell["cell_id"]).exists()
        and (not trial or cell["label"] == "dickens")
    ]
    while pending:
        wave = []
        used: set[int] = set()
        for cell in pending:
            manifest, _ = load_manifest(ROOT / cell["manifest_path"])
            cpu = manifest["budget"]["cpu"]
            if cpu in used:
                continue
            wave.append(cell)
            used.add(cpu)
            if len(wave) == 4:
                break
        results = scheduler.run_wave(wave)
        completed_ids = {cell["cell_id"] for cell in wave}
        pending = [cell for cell in pending if cell["cell_id"] not in completed_ids]
        statuses = [result.get("runner_status") for result in results]
        print(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "remaining": len(pending), "statuses": statuses}, sort_keys=True), flush=True)
        if any(status not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for status in statuses):
            raise RuntimeError("native Silesia wave stopped on failure; do not automatically retry frozen cells")


def time_metrics(path: Path) -> dict:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text().splitlines():
        if "Elapsed (wall clock)" in line:
            fields = list(map(float, line.split("):", 1)[1].strip().split(":")))
            values["wall_seconds"] = sum(v * 60 ** (len(fields) - i - 1) for i, v in enumerate(fields))
        elif "Maximum resident set size" in line:
            values["peak_rss_kib"] = int(line.rsplit(":", 1)[1])
    return values


def collect() -> None:
    cells = json.loads((AREA / "cells.json").read_text())
    scheduler = WaveScheduler(ROOT)
    rows = []
    for cell in cells:
        row = {key: cell[key] for key in ("cell_id", "label", "format", "profile", "input_bytes", "input_sha256")}
        terminal_path = scheduler._terminal_path(cell["cell_id"])
        if not terminal_path.is_file():
            row["status"] = "PENDING"
        else:
            terminal = json.loads(terminal_path.read_text())
            result = terminal.get("runner_result", {})
            receipt_path = result.get("receipt")
            row["scheduler_status"] = terminal.get("runner_status")
            if receipt_path and Path(receipt_path).is_file():
                receipt = json.loads(Path(receipt_path).read_text())
                row.update(
                    status=receipt["status"],
                    archive_bytes=receipt.get("archive_bytes"),
                    archive_sha256=receipt.get("archive_sha256"),
                    verification=receipt.get("verification"),
                    receipt=receipt_path,
                )
                work = Path(receipt_path).parent / "work"
                row["encode"] = time_metrics(work / "encode.time.txt")
                row["decode"] = time_metrics(work / "decode.time.txt")
            else:
                row.update(status=terminal.get("runner_status", "FAILED"), failure=result)
        rows.append(row)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    output = AREA / "results.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite native Silesia results: {output}")
    output.write_text(json.dumps({"collected_at": datetime.now(timezone.utc).isoformat(), "counts": counts, "rows": rows}, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": counts}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "collect"))
    parser.add_argument("--trial", action="store_true", help="run only the predeclared Dickens trial cells")
    args = parser.parse_args()
    if args.trial and args.action != "run":
        parser.error("--trial applies to run only")
    if args.action == "run":
        run(trial=args.trial)
    else:
        {"prepare": prepare, "collect": collect}[args.action]()


if __name__ == "__main__":
    main()
