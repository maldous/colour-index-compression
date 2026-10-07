#!/usr/bin/env python3
"""Declare and execute the bounded CIX route-retention evidence round.

Preparation and dispatch are deliberately separate.  ``prepare`` freezes an
immutable source snapshot and manifests.  ``run`` additionally requires a
root-authored authorization file, so importing this module or preparing the
matrix can never start compression work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import resource
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT = Path(__file__).resolve().parents[1]
V1_AREA = ROOT / "docs/research/2026-09-30-retention-round"
AREA = ROOT / "docs/research/2026-10-01-retention-round-v2"
INPUTS_SOURCE = ROOT / "docs/research/2026-09-30-generic-pipeline/inputs.json"
PROFILES = {"current": "balanced", "speed": "fast", "size": "maximum"}
ROUTES = ("raw", "runs", "composition", "lz", "predictor", "bwt", "stride",
          "phrases", "ppm", "mixture", "deflate")
STREAM_BACKENDS = ("hybrid", "cix", "deflate", "count-range", "range")
TRANSFORM_ROUTES = ("lz", "predictor", "bwt", "stride", "phrases")
REPETITIONS = 3
OUTER_BUDGET = {"max_rss_bytes": 2_000_000_000,
                "max_temp_bytes": 100_000_000, "wall_seconds": 180}
RECODE_MAGIC = b"CIXR1"


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(path: Path):
    return json.loads(path.read_text())


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _physical_cpus() -> list[int]:
    cpus, seen = [], set()
    for cpu in sorted(os.sched_getaffinity(0)):
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        key = ((topology / "physical_package_id").read_text().strip(),
               (topology / "core_id").read_text().strip())
        if key not in seen:
            cpus.append(cpu); seen.add(key)
        if len(cpus) == 4:
            break
    if len(cpus) != 4:
        raise RuntimeError("four independent physical CPUs are required")
    return cpus


def _build_paths(source_commit: str) -> list[str]:
    # The baseline must not absorb unrelated/untracked CIX modules created by
    # concurrent workers.  Take the CIX file list from the named Git tree, then
    # add only this harness and its existing adapter.
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", source_commit, "--", "cix"],
        cwd=ROOT, text=True).splitlines()
    paths = sorted(name for name in names if name.endswith(".py"))
    return paths + ["benchmarks/generic_probe.py", "benchmarks/codec_profiles.py",
        "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py",
        "benchmarks/retention_round.py",
        "docs/research/2026-09-30-generic-pipeline/inputs.json",
        "docs/research/2026-09-30-codec-profiles/policy.json"]


def _source_inputs() -> list[dict]:
    rows = [row for row in _json(INPUTS_SOURCE)
            if row["stratum"] in ("development", "heldout")]
    if len(rows) != 6 or any(row["length"] != 16384 for row in rows):
        raise RuntimeError("expected the frozen six 16 KiB screening slices")
    aliases = {
        "golf": "compression-golf-github-events-prefix",
        "golf-heldout": "compression-golf-github-events-offset-1048576",
    }
    for row in rows:
        row["display_label"] = aliases.get(row["label"], row["label"])
        row["exposure"] = "previously examined screening input"
    return rows


def _nonoverlapping_offset(path: Path, length: int, numerator: int, denominator: int,
                           occupied: list[tuple[int, int]]) -> int:
    alignment = 16384
    maximum = path.stat().st_size - length
    if maximum < 0:
        raise ValueError(f"asset is shorter than requested frozen range: {path}")
    offset = ((maximum * numerator // denominator) // alignment) * alignment
    for _ in range(maximum // alignment + 2):
        if all(offset + length <= start or offset >= end for start, end in occupied):
            return offset
        offset += alignment
        if offset > maximum:
            offset = 0
    raise RuntimeError(f"cannot place a non-overlapping range in {path}")


def freeze_replication_inputs(destination: Path) -> dict:
    """Hash deterministic, structurally agnostic ranges before evaluation."""
    preserved = V1_AREA / "replication-inputs.json"
    if preserved.is_file():
        v1 = _json(preserved)
        if v1.get("source_registry_sha256") != _sha(INPUTS_SOURCE):
            raise RuntimeError("preserved v1 replication registry has a different source registry")
        for row in v1.get("inputs", []):
            path = Path(row["path"])
            with path.open("rb") as stream:
                stream.seek(int(row["offset"])); data = stream.read(int(row["length"]))
            if len(data) != int(row["length"]) or _sha_bytes(data) != row["sha256"]:
                raise RuntimeError("preserved v1 replication input no longer matches local bytes")
        if len(v1.get("inputs", [])) != 12:
            raise RuntimeError("preserved v1 replication registry is incomplete")
        receipt = dict(v1)
        receipt["v2_imported_at"] = _now()
        receipt["imported_from"] = str(preserved.relative_to(ROOT))
        receipt["imported_from_sha256"] = _sha(preserved)
        receipt["selection_repeated"] = False
        _write_json(destination, receipt)
        return receipt
    old = _source_inputs()
    by_path: dict[str, list[dict]] = {}
    for row in old:
        by_path.setdefault(str(Path(row["path"]).resolve()), []).append(row)
    frozen, selection = [], []
    for path_text, members in sorted(by_path.items()):
        path = Path(path_text)
        occupied = [(int(row["offset"]), int(row["offset"]) + int(row["length"]))
                    for row in members]
        for ordinal, row in enumerate(members):
            # Duplicate source assets receive deterministic 1/3 and 2/3
            # placements; singletons receive the midpoint.  No byte content is
            # consulted when selecting a location.
            denominator = len(members) + 1
            numerator = ordinal + 1
            offset = _nonoverlapping_offset(path, 16384, numerator, denominator, occupied)
            occupied.append((offset, offset + 16384))
            with path.open("rb") as stream:
                stream.seek(offset); data = stream.read(16384)
            label = row["display_label"] + "-fresh-midrange-16k"
            frozen.append({"label": label, "parent_label": row["label"],
                "stratum": "fresh-replication", "path": str(path), "offset": offset,
                "length": len(data), "sha256": _sha_bytes(data),
                "full_asset_sha256": row["full_asset_sha256"],
                "classification": "content-blind aligned fractional range; bytes not profiled",
                "exposure": "hash frozen for this round; no compression result at freeze"})
            selection.append({"label": label, "algorithm":
                f"aligned fraction {numerator}/{denominator}; first non-overlap from that offset"})
        # Scaling ranges are disjoint from old and fresh 16 KiB ranges.  Their
        # reverse fractional order avoids nesting the replication slices.
        for ordinal, row in enumerate(reversed(members)):
            denominator = len(members) + 1
            numerator = ordinal + 1
            offset = _nonoverlapping_offset(path, 65536, numerator, denominator, occupied)
            occupied.append((offset, offset + 65536))
            with path.open("rb") as stream:
                stream.seek(offset); data = stream.read(65536)
            label = row["display_label"] + "-fresh-scaling-64k"
            frozen.append({"label": label, "parent_label": row["label"],
                "stratum": "fresh-scaling", "path": str(path), "offset": offset,
                "length": len(data), "sha256": _sha_bytes(data),
                "full_asset_sha256": row["full_asset_sha256"],
                "classification": "content-blind aligned fractional range; bytes not profiled",
                "exposure": "hash frozen for this round; no compression result at freeze"})
            selection.append({"label": label, "algorithm":
                f"reverse-order aligned fraction {numerator}/{denominator}; first non-overlap"})
    if len(frozen) != 12 or any(row["length"] not in (16384, 65536) for row in frozen):
        raise AssertionError("replication registry must contain six 16 KiB and six 64 KiB ranges")
    receipt = {"schema": 1, "frozen_at": _now(),
        "selection_uses_content": False, "source_registry": str(INPUTS_SOURCE.relative_to(ROOT)),
        "source_registry_sha256": _sha(INPUTS_SOURCE), "inputs": frozen, "selection": selection,
        "warning": "Hashing records identity only; it is not publisher verification."}
    _write_json(destination, receipt)
    return receipt


def _snapshot_entrypoint_check(paths: list[str]) -> dict:
    """Execute the copied harness inventory from the exact dependency closure."""
    with tempfile.TemporaryDirectory(prefix="cix-retention-snapshot-check-") as directory:
        snapshot = Path(directory)
        for name in paths:
            source, copied = ROOT / name, snapshot / name
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, copied)
            if _sha(copied) != _sha(source):
                raise RuntimeError(f"snapshot entrypoint copy mismatch: {name}")
        command = [sys.executable, str(snapshot / "benchmarks/retention_round.py"), "inventory"]
        completed = subprocess.run(command, cwd=snapshot, capture_output=True, text=True,
            timeout=30, check=False)
        if completed.returncode:
            raise RuntimeError("snapshot inventory entrypoint failed: " + completed.stderr.strip())
        inventory_result = json.loads(completed.stdout)
        if inventory_result.get("core_cells") != 864:
            raise RuntimeError("snapshot inventory returned an unexpected matrix")
        return {"command": [sys.executable, "<snapshot>/benchmarks/retention_round.py", "inventory"],
            "returncode": completed.returncode, "core_cells": inventory_result["core_cells"],
            "planned_fresh_replication_cells": inventory_result["planned_fresh_replication_cells"],
            "dependency_count": len(paths)}


def _original_worker(connection, data: bytes, backend: str, memory_mib: int) -> None:
    try:
        from cix.pipeline import streams
        resource.setrlimit(resource.RLIMIT_AS,
                           (memory_mib * 1048576, memory_mib * 1048576))
        started = time.perf_counter(); payload = streams([data], backend)
        connection.send((payload, time.perf_counter() - started,
                         resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, None))
    except Exception as error:
        connection.send((None, 0.0, 0, f"{type(error).__name__}: {error}"))
    finally:
        connection.close()


def _original_trial(data: bytes, backend: str, seconds: float, memory_mib: int) -> tuple:
    context = mp.get_context("fork"); parent, child = context.Pipe(False)
    process = context.Process(target=_original_worker,
        args=(child, data, backend, memory_mib))
    started = time.perf_counter(); process.start(); child.close()
    result = (None, 0.0, 0, "TIME_BUDGET")
    try:
        if parent.poll(max(0.0, seconds - (time.perf_counter() - started))):
            try:
                result = parent.recv()
            except EOFError:
                result = (None, 0.0, 0, "WORKER_EXIT")
    finally:
        if process.is_alive():
            process.terminate()
        process.join(); parent.close()
    return (*result, time.perf_counter() - started)


def _encode_original(source: Path, destination: Path, effort: str, backend: str) -> dict:
    """Encode unchanged bytes with one declared streams() backend in CIXG1."""
    from cix.pipeline import EFFORTS, END, FRAME, HEADER, MAGIC, accounting, profile
    policy = EFFORTS[effort]
    whole = hashlib.sha256(); blocks = []; offset = 0; begin = time.perf_counter()
    with source.open("rb") as incoming, destination.open("wb") as output:
        output.write(HEADER.pack(MAGIC, policy.block_bytes, 0))
        while data := incoming.read(policy.block_bytes):
            started = time.perf_counter(); features = profile(data, policy.sample_bytes)
            profiling_seconds = time.perf_counter() - started
            remaining = policy.search_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise RuntimeError("forced original control exhausted search budget during profiling")
            payload, compute, peak_rss, error, wall = _original_trial(data, backend,
                min(policy.trial_seconds, remaining), policy.worker_memory_mib)
            trial = {"route": "original", "status": error or "COMPLETE",
                "payload_bytes": None if payload is None else len(payload),
                "backend": backend, "compute_seconds": compute,
                "wall_seconds": wall, "peak_rss_kib": peak_rss}
            if payload is None:
                raise RuntimeError(f"forced original control did not complete: {trial}")
            digest = hashlib.sha256(data).digest(); whole.update(data)
            output.write(FRAME.pack(2, len(data), len(payload), digest)); output.write(payload)
            blocks.append({"offset": offset, "source_bytes": len(data), "route": "original",
                "complete_block_bytes": FRAME.size + len(payload),
                "features": features, "profiling_seconds": profiling_seconds,
                "selection_seconds": time.perf_counter() - started,
                "selected_trial_compute_seconds": compute,
                "accounting": accounting("composition", payload, len(data)),
                "trials": [trial]})
            offset += len(data)
        output.write(FRAME.pack(END, 0, 0, whole.digest()))
    return {"format": "CIXG1", "effort": effort, "backend": backend,
        "force": "original", "history_bytes": 0, "block_bytes": policy.block_bytes,
        "source_bytes": offset, "compressed_bytes": destination.stat().st_size,
        "source_sha256": whole.hexdigest(), "encode_seconds": time.perf_counter() - begin,
        "block_count": len(blocks), "route_usage_source_bytes": {"original": offset},
        "selection_total_seconds": sum(block["selection_seconds"] for block in blocks),
        "search_and_launch_overhead_seconds": sum(
            block["selection_seconds"] - block["selected_trial_compute_seconds"] for block in blocks),
        "blocks": blocks}


def _decode_any(source: Path, destination: Path) -> dict:
    from cix.pipeline import decode_file
    if source.read_bytes()[:5] != RECODE_MAGIC:
        return decode_file(source, destination)
    header = source.read_bytes()[:37]
    expected = header[5:].hex()
    with tempfile.TemporaryDirectory(prefix="cix-retention-decode-") as directory:
        directory = Path(directory)
        outer = directory / "outer.cix"; baseline = directory / "baseline.cix"
        with source.open("rb") as incoming, outer.open("wb") as output:
            incoming.seek(37); shutil.copyfileobj(incoming, output)
        outer_report = decode_file(outer, baseline)
        inner_report = decode_file(baseline, destination)
    actual = _sha(destination)
    if actual != expected:
        raise ValueError("CIXR1 reconstructed source hash mismatch")
    return {"format": "CIXR1", "decoded_bytes": destination.stat().st_size,
        "decoded_sha256": actual, "outer": outer_report, "inner": inner_report}


def _single_encode(source: Path, destination: Path, *, effort: str, backend: str,
                   force: str | None, disable: list[str], recode: bool) -> dict:
    from cix.pipeline import encode_file
    if force == "original":
        report = _encode_original(source, destination, effort, backend)
    else:
        report = encode_file(source, destination, effort=effort, backend=backend,
            force=force, disable=disable, trace_path=destination.parent / "blocks.jsonl")
    trace = destination.parent / "blocks.jsonl"
    if not trace.exists():
        trace.write_text("".join(json.dumps(block) + "\n" for block in report.get("blocks", [])))
    baseline_bytes = destination.stat().st_size
    if recode:
        baseline = destination.with_suffix(".baseline.cix")
        destination.replace(baseline)
        outer = destination.with_suffix(".outer.cix")
        _encode_original(baseline, outer, effort, "cix")
        wrapped = RECODE_MAGIC + bytes.fromhex(_sha(source)) + outer.read_bytes()
        if len(wrapped) < baseline.stat().st_size:
            destination.write_bytes(wrapped); selected = "native-cix-recode"
        else:
            shutil.copyfile(baseline, destination); selected = "unchanged-candidate"
        report["optional_native_cix_recode"] = {"baseline_bytes": baseline_bytes,
            "recode_bytes": len(wrapped), "selected": selected,
            "selected_bytes": destination.stat().st_size, "wrapper_bytes": 37,
            "outer_cixg1_bytes": outer.stat().st_size}
    (destination.parent / "encode.codec.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _run_timed(command: list[str], timing: Path, stdout: Path, stderr: Path) -> None:
    with stdout.open("w") as output, stderr.open("w") as errors:
        completed = subprocess.run(["/usr/bin/time", "-v", "-o", str(timing), *command],
            stdout=output, stderr=errors, check=False)
    if completed.returncode:
        raise RuntimeError(f"leaf command failed ({completed.returncode}); see {stderr}")


def _elapsed_seconds(value: str) -> float:
    fields = value.strip().split(":")
    if len(fields) == 2:
        return float(fields[0]) * 60 + float(fields[1])
    if len(fields) == 3:
        return float(fields[0]) * 3600 + float(fields[1]) * 60 + float(fields[2])
    return float(value)


def _timing(path: Path) -> dict:
    fields = {}
    for line in path.read_text().splitlines():
        if ": " in line:
            key, value = line.strip().rsplit(": ", 1)
            fields[key] = value
    elapsed_key = next((key for key in fields if key.startswith("Elapsed (wall clock) time")), None)
    if elapsed_key is None:
        raise ValueError(f"missing elapsed time in {path}")
    return {"seconds": _elapsed_seconds(fields[elapsed_key]),
        "user_seconds": float(fields.get("User time (seconds)", "0")),
        "system_seconds": float(fields.get("System time (seconds)", "0")),
        "peak_rss_kib": int(fields.get("Maximum resident set size (kbytes)", "0")),
        "raw": str(path)}


def leaf_encode(source: Path, destination: Path, args) -> None:
    root = Path(__file__).resolve().parents[1]
    rows = []
    for index in range(args.repetitions):
        directory = destination.parent / "encode-repetitions" / f"rep-{index}"
        directory.mkdir(parents=True, exist_ok=False)
        archive = directory / "candidate.bin"
        command = [sys.executable, str(root / "benchmarks/retention_round.py"), "single-encode",
            str(source), str(archive), "--effort", args.effort, "--backend", args.backend]
        if args.force: command += ["--force", args.force]
        for route in args.disable: command += ["--disable", route]
        if args.recode: command.append("--recode")
        timing = directory / "encode.time.txt"
        _run_timed(command, timing, directory / "stdout.log", directory / "stderr.log")
        rows.append({"index": index, "archive": str(archive), "bytes": archive.stat().st_size,
            "sha256": _sha(archive), "timing": str(timing), "command": command,
            "codec": str(directory / "encode.codec.json"),
            "trace": str(directory / "blocks.jsonl")})
    shutil.copyfile(rows[0]["archive"], destination)
    _write_json(destination.parent / "encode-repetitions.json", {
        "schema": 1, "policy": "three independent measured processes; no warmup; startup included; repetition zero is the predeclared primary archive",
        "repetitions": rows, "size_range_bytes": [min(r["bytes"] for r in rows), max(r["bytes"] for r in rows)]})


def leaf_decode(source: Path, destination: Path, expected_sha: str,
                expected_length: int, repetitions_manifest: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    encoded = _json(repetitions_manifest); rows = []
    for item in encoded["repetitions"]:
        index = item["index"]
        directory = destination.parent / "decode-repetitions" / f"rep-{index}"
        directory.mkdir(parents=True, exist_ok=False)
        restored = directory / "restored.bin"
        command = [sys.executable, str(root / "benchmarks/retention_round.py"), "single-decode",
                   item["archive"], str(restored)]
        timing = directory / "decode.time.txt"
        _run_timed(command, timing, directory / "stdout.log", directory / "stderr.log")
        actual = _sha(restored)
        if restored.stat().st_size != expected_length or actual != expected_sha:
            raise RuntimeError(f"repetition {index} failed exact restoration")
        rows.append({"index": index, "restored": str(restored), "bytes": restored.stat().st_size,
            "sha256": actual, "timing": str(timing), "command": command,
            "codec": str(directory / "decode.codec.json")})
    shutil.copyfile(rows[0]["restored"], destination)
    _write_json(destination.parent / "decode-repetitions.json", {
        "schema": 1, "policy": "three independent archive-only decodes; source path inaccessible; startup included",
        "repetitions": rows})


def _configuration(profile: str, kind: str, *, route=None, backend="hybrid", disable=None) -> dict:
    return {"profile": profile, "effort": PROFILES[profile], "kind": kind,
        "route": route, "backend": backend, "disable": list(disable or []),
        "repetitions": REPETITIONS, "warmups": 0, "history_bytes": 0,
        "startup_included": True}


def _planned_core(inputs: list[dict]):
    for inp in inputs:
        for profile in PROFILES:
            for route in ROUTES:
                yield inp, "forced-hybrid", _configuration(profile, "forced", route=route)
            for backend in STREAM_BACKENDS:
                yield inp, "original-controls", _configuration(profile, "original-control",
                    route="original", backend=backend)
            for route in TRANSFORM_ROUTES:
                for backend in STREAM_BACKENDS[1:]:
                    yield inp, "alternate-backends", _configuration(profile, "forced",
                        route=route, backend=backend)
            yield inp, "adaptive", _configuration(profile, "adaptive")
            for route in ROUTES:
                yield inp, "removal-ablations", _configuration(profile, "removal-ablation",
                    disable=[route])


def _planned_replication(inputs: list[dict]):
    for inp in inputs:
        for profile in PROFILES:
            yield inp, "replication-adaptive", _configuration(profile, "adaptive")
            for route in ROUTES:
                yield inp, "replication-forced-hybrid", _configuration(profile, "forced", route=route)
            for backend in STREAM_BACKENDS:
                yield inp, "replication-original-controls", _configuration(profile,
                    "original-control", route="original", backend=backend)


def inventory() -> dict:
    core = list(_planned_core(_source_inputs()))
    return {"profiles": PROFILES, "representations": list(ROUTES),
        "stream_backends": list(STREAM_BACKENDS), "core_cells": len(core),
        "counts_by_stage": dict(Counter(stage for _, stage, _ in core)),
        "planned_fresh_replication_cells": 6 * 3 * (1 + len(ROUTES) + len(STREAM_BACKENDS)),
        "planned_scaling": "six frozen 64 KiB ranges; current/size adaptive plus shortlisted forced routes after core evidence",
        "outer_budget_per_cell": OUTER_BUDGET, "aggregate_budget": {
            "jobs": 4, "memory_bytes": 12_000_000_000, "temp_bytes": 4_000_000_000,
            "swap": "disabled by bounded runner"}}


def _make_cell(inp: dict, stage: str, config: dict, cpu: int, source_freeze: dict) -> dict:
    flags = ["--effort", config["effort"], "--backend", config["backend"],
             "--repetitions", str(REPETITIONS)]
    if config["kind"] in ("forced", "original-control"):
        flags += ["--force", config["route"]]
    for route in config["disable"]:
        flags += ["--disable", route]
    if config["kind"] == "adaptive-recode":
        flags.append("--recode")
    script = str(ROOT / "benchmarks/retention_round.py")
    manifest = {"hypothesis": "CIX must retain the smallest completed eligible complete archive; a representation or native recode is useful only when its paid physical result is smaller.",
        "matched_control": "Same exact input, immutable build, profile effort, stream backend where applicable, empty/reset state, three startup-inclusive repetitions, and identical outer resource caps.",
        "input": inp, "configuration": config,
        "mechanism": "forced route, original-byte stream control, adaptive selector, removal ablation, or optional one-pass native CIX recode as declared; all framing and inverse information remain physical",
        "budget": {"cpu": cpu, **OUTER_BUDGET},
        "promotion_criteria": "All three physical archives complete; all three independent source-inaccessible decodes exactly match SHA-256 and length; selected result uses predeclared repetition zero; budget failures remain unqualified.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.outer.time.txt",
            sys.executable, script, "leaf-encode", "{source}", "{workdir}/candidate.bin", *flags],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.outer.time.txt",
            sys.executable, script, "leaf-decode", "{workdir}/candidate.bin", "{workdir}/restored.bin",
            "--expected-sha", inp["sha256"], "--expected-length", str(inp["length"]),
            "--repetitions-manifest", "{workdir}/encode-repetitions.json"],
        "artifacts": {"archive": "{workdir}/candidate.bin", "restored": "{workdir}/restored.bin"},
        "build_paths": source_freeze["build_paths"], "initial_state": "empty for every repetition",
        "stage": "screening", "matrix_stage": stage, "source_freeze": source_freeze["sha256"],
        "timing_policy": "no warmup; three independent leaf processes; startup, reads/writes, profiling and discarded trials included"}
    identity = hashlib.sha256(canonical({"manifest": manifest,
        "build": build_identity(manifest, ROOT)})).hexdigest()[:24]
    cell_id = "retention-" + identity
    path = AREA / "manifests" / f"{cell_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(manifest) + b"\n")
    _, manifest_sha = load_manifest(path)
    return {"cell_id": cell_id, "owner": "/root/retention_harness",
        "manifest_path": str(path), "output_dir": str(AREA / "runs" / cell_id),
        "expected_manifest_sha256": manifest_sha,
        "expected_build_sha256": build_identity(manifest, ROOT),
        "label": inp["label"], "matrix_stage": stage, "configuration": config}


def prepare(source_commit: str) -> dict:
    if (AREA / "source-freeze.json").exists() or (AREA / "cells.json").exists():
        raise RuntimeError("retention round is already frozen; never rewrite its identity")
    actual_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if source_commit != actual_commit:
        raise ValueError("--source-commit must equal canonical HEAD at freeze")
    paths = _build_paths(source_commit)
    tracked = [name for name in paths if name != "benchmarks/retention_round.py"]
    mismatched = []
    for name in tracked:
        committed = subprocess.check_output(["git", "show", f"{source_commit}:{name}"], cwd=ROOT)
        if _sha_bytes(committed) != _sha(ROOT / name):
            mismatched.append(name)
    if mismatched:
        raise RuntimeError("baseline tracked build differs from the named commit: " + ", ".join(mismatched))
    snapshot_check = _snapshot_entrypoint_check(paths)
    source_freeze = {"schema": 1, "frozen_at": _now(), "source_commit": actual_commit,
        "build_paths": paths, "build_sha256": {name: _sha(ROOT / name) for name in paths},
        "policy": "one immutable build for controls, candidates, adaptive selection and ablations",
        "snapshot_entrypoint_check": snapshot_check,
        "supersedes": str((V1_AREA / "ROUND-STATUS.json").relative_to(ROOT)),
        "v1_policy": "v1 manifests, claims and import-failure logs are preserved and never restarted"}
    source_freeze["sha256"] = _sha_bytes(canonical(source_freeze))
    AREA.mkdir(parents=True, exist_ok=True)
    _write_json(AREA / "source-freeze.json", source_freeze)
    replication = freeze_replication_inputs(AREA / "replication-inputs.json")
    cpus = _physical_cpus(); cells = []
    for index, (inp, stage, config) in enumerate(_planned_core(_source_inputs())):
        cells.append(_make_cell(inp, stage, config, cpus[index % len(cpus)], source_freeze))
    fresh = [row for row in replication["inputs"] if row["stratum"] == "fresh-replication"]
    for inp, stage, config in _planned_replication(fresh):
        cells.append(_make_cell(inp, stage, config, cpus[len(cells) % len(cpus)], source_freeze))
    _write_json(AREA / "cells.json", {"schema": 1, "status": "FROZEN_NOT_AUTHORIZED",
        "source_freeze": source_freeze["sha256"], "cells": cells})
    _write_json(AREA / "results.json", {"schema": 1, "status": "NOT_RUN", "rows": []})
    result = inventory() | {"frozen_cells": len(cells), "source_freeze": source_freeze["sha256"],
        "replication_registry_sha256": _sha(AREA / "replication-inputs.json")}
    _write_json(AREA / "plan-summary.json", result)
    return result


def _authorization(stages: set[str], path: Path) -> dict:
    authorization = _json(path); freeze = _json(AREA / "source-freeze.json")
    if authorization.get("source_freeze") != freeze["sha256"]:
        raise ValueError("dispatch authorization does not match frozen source")
    allowed = set(authorization.get("authorized_stages", []))
    if not stages <= allowed or authorization.get("authorized_by") != "/root":
        raise PermissionError("root authorization does not cover requested stages")
    return authorization


def _terminal_summary(cell: dict) -> dict:
    paths = list(Path(cell["output_dir"]).glob("*/receipt.json"))
    paths += list(Path(cell["output_dir"]).glob("*/failed.json"))
    paths += list(Path(cell["output_dir"]).glob("*/size-rejected.json"))
    if not paths:
        return {"cell_id": cell["cell_id"], "status": "PENDING"}
    if len(paths) != 1:
        raise RuntimeError(f"ambiguous terminal evidence for {cell['cell_id']}")
    receipt = _json(paths[0]); row = {"cell_id": cell["cell_id"], "status": receipt["status"]}
    if receipt["status"] != "VERIFIED_SCREENING":
        row["failure_class"], row["failure_reason"] = _failure_details(paths[0], receipt)
    return row


def run(stages: set[str], authorization: Path) -> None:
    _authorization(stages, authorization)
    registry = _json(AREA / "cells.json")
    cells = [cell for cell in registry["cells"] if cell["matrix_stage"] in stages]
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000,
                              max_temp_bytes=4_000_000_000)
    completed_before = sum(scheduler._terminal_path(cell["cell_id"]).exists() for cell in cells)
    cells = [cell for cell in cells if not scheduler._terminal_path(cell["cell_id"]).exists()]
    completed_now = 0
    while cells:
        wave, cpus = [], set()
        for cell in cells:
            cpu = _json(Path(cell["manifest_path"]))["budget"]["cpu"]
            if cpu not in cpus:
                wave.append(cell); cpus.add(cpu)
            if len(wave) == 4:
                break
        outcomes = scheduler.run_wave(wave)
        for cell in wave:
            cells.remove(cell)
        summaries = [_terminal_summary(cell) for cell in wave]; completed_now += len(wave)
        unexpected = [row for row in summaries if row["status"] == "FAILED"
            and row.get("failure_class") == "UNEXPECTED_FAILURE"]
        print(json.dumps({"at": _now(), "remaining": len(cells),
            "wave": [cell["cell_id"] for cell in wave],
            "outcomes": [row.get("runner_status", row.get("status")) for row in outcomes],
            "wave_counts": dict(Counter(row["status"] for row in summaries)),
            "completed_in_requested_stages": completed_before + completed_now,
            "unexpected_failures": [row["cell_id"] for row in unexpected]}), flush=True)
        if unexpected:
            raise RuntimeError("unexpected command or verification failure; wave stopped")
    collect()


def _failure_details(terminal_path: Path, receipt: dict) -> tuple[str, str]:
    destination = terminal_path.parent
    text = "\n".join(path.read_text(errors="replace")
        for path in destination.rglob("*.stderr.log"))
    stops = " ".join(str(phase.get("stop_reason")) for phase in receipt.get("phases", [])
        if isinstance(phase, dict))
    evidence = text + "\n" + stops
    if "TIME_BUDGET" in evidence or "SEARCH_BUDGET" in evidence:
        return "UNQUALIFIED", "internal route/search budget exhausted"
    if ("MemoryError" in evidence or "memory_budget_exhausted" in evidence
            or "WORKER_EXIT" in evidence):
        return "RESOURCE_LIMIT", "declared worker or outer memory/resource limit"
    if "wall_budget_exhausted" in evidence or "temp_budget_exhausted" in evidence:
        return "RESOURCE_LIMIT", "declared outer wall/temp resource limit"
    return "UNEXPECTED_FAILURE", "command, archive, or exact-restoration failure"


def collect() -> dict:
    registry = _json(AREA / "cells.json"); rows = []
    for cell in registry["cells"]:
        paths = list(Path(cell["output_dir"]).glob("*/receipt.json"))
        paths += list(Path(cell["output_dir"]).glob("*/failed.json"))
        paths += list(Path(cell["output_dir"]).glob("*/size-rejected.json"))
        row = {"cell_id": cell["cell_id"], "label": cell["label"],
               "matrix_stage": cell["matrix_stage"], "configuration": cell["configuration"],
               "status": "PENDING"}
        if paths:
            if len(paths) != 1:
                raise RuntimeError(f"ambiguous terminal evidence for {cell['cell_id']}")
            receipt = _json(paths[0]); row.update({"status": receipt["status"],
                "receipt": str(paths[0]), "archive_bytes": receipt.get("archive_bytes"),
                "archive_sha256": receipt.get("archive_sha256"), "verification": receipt["verification"],
                "budget": receipt["budget"], "phases": receipt["phases"]})
            if receipt["status"] != "VERIFIED_SCREENING":
                row["failure_class"], row["failure_reason"] = _failure_details(paths[0], receipt)
            work = paths[0].parent / "work"
            for phase in ("encode", "decode"):
                detail = work / f"{phase}-repetitions.json"
                if detail.exists():
                    repetitions = _json(detail)["repetitions"]
                    if len(repetitions) != REPETITIONS:
                        raise RuntimeError("qualified timing set does not contain three repetitions")
                    for repetition in repetitions:
                        repetition["measurement"] = _timing(Path(repetition["timing"]))
                    seconds = [repetition["measurement"]["seconds"] for repetition in repetitions]
                    median = statistics.median(seconds)
                    row[phase + "_repetitions"] = repetitions
                    row[phase] = {"seconds": median, "min_seconds": min(seconds),
                        "max_seconds": max(seconds),
                        "mad_seconds": statistics.median(abs(value - median) for value in seconds),
                        "peak_rss_kib": max(repetition["measurement"]["peak_rss_kib"]
                                            for repetition in repetitions)}
            if receipt["status"] == "VERIFIED_SCREENING":
                if "encode_repetitions" not in row or "decode_repetitions" not in row:
                    raise RuntimeError("verified result is missing repetition evidence")
                if any(rep["sha256"] != receipt["identity"]["input"]["sha256"]
                       for rep in row["decode_repetitions"]):
                    raise RuntimeError("a decode repetition hash does not match the input")
                for repetition in row["encode_repetitions"]:
                    archive = Path(repetition["archive"])
                    if (not archive.is_file() or archive.stat().st_size != repetition["bytes"]
                            or _sha(archive) != repetition["sha256"]):
                        raise RuntimeError("an encode repetition archive no longer matches its record")
                if _sha(Path(receipt["artifacts"]["archive"])) != receipt["archive_sha256"]:
                    raise RuntimeError("physical archive hash mismatch")
                if _sha(Path(receipt["artifacts"]["restored"])) != receipt["identity"]["input"]["sha256"]:
                    raise RuntimeError("physical restoration hash mismatch")
        rows.append(row)
    result = {"schema": 1, "collected_at": _now(), "source_freeze": registry["source_freeze"],
        "counts": dict(Counter(row["status"] for row in rows)), "rows": rows}
    _write_json(AREA / "results.json", result)
    _write_json(AREA / "run-summary.json", {"schema": 1, "collected_at": result["collected_at"],
        "source_freeze": result["source_freeze"], "counts": result["counts"],
        "counts_by_stage_and_status": {
            stage: dict(Counter(row["status"] for row in rows if row["matrix_stage"] == stage))
            for stage in sorted({row["matrix_stage"] for row in rows})},
        "qualified_archive_bytes": sum(row.get("archive_bytes") or 0 for row in rows
            if row["status"] == "VERIFIED_SCREENING")})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("inventory")
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--source-commit", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--stage", action="append", required=True)
    run_parser.add_argument("--authorization", type=Path, required=True)
    commands.add_parser("collect")
    single = commands.add_parser("single-encode")
    single.add_argument("source", type=Path); single.add_argument("destination", type=Path)
    single.add_argument("--effort", choices=PROFILES.values(), required=True)
    single.add_argument("--backend", choices=STREAM_BACKENDS, required=True)
    single.add_argument("--force", choices=("original", *ROUTES))
    single.add_argument("--disable", action="append", default=[], choices=ROUTES)
    single.add_argument("--recode", action="store_true")
    single_decode = commands.add_parser("single-decode")
    single_decode.add_argument("source", type=Path); single_decode.add_argument("destination", type=Path)
    encode = commands.add_parser("leaf-encode")
    encode.add_argument("source", type=Path); encode.add_argument("destination", type=Path)
    encode.add_argument("--effort", choices=PROFILES.values(), required=True)
    encode.add_argument("--backend", choices=STREAM_BACKENDS, required=True)
    encode.add_argument("--force", choices=("original", *ROUTES))
    encode.add_argument("--disable", action="append", default=[], choices=ROUTES)
    encode.add_argument("--recode", action="store_true"); encode.add_argument("--repetitions", type=int, default=3)
    decode = commands.add_parser("leaf-decode")
    decode.add_argument("source", type=Path); decode.add_argument("destination", type=Path)
    decode.add_argument("--expected-sha", required=True); decode.add_argument("--expected-length", type=int, required=True)
    decode.add_argument("--repetitions-manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "inventory":
        print(json.dumps(inventory(), indent=2)); return 0
    if args.operation == "prepare":
        print(json.dumps(prepare(args.source_commit), indent=2)); return 0
    if args.operation == "run":
        run(set(args.stage), args.authorization); return 0
    if args.operation == "collect":
        print(json.dumps(collect()["counts"], sort_keys=True)); return 0
    if args.operation == "single-encode":
        report = _single_encode(args.source, args.destination, effort=args.effort,
            backend=args.backend, force=args.force, disable=args.disable, recode=args.recode)
        print(json.dumps({key: value for key, value in report.items() if key != "blocks"})); return 0
    if args.operation == "single-decode":
        report = _decode_any(args.source, args.destination)
        (args.destination.parent / "decode.codec.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report)); return 0
    if args.operation == "leaf-encode":
        if args.repetitions != REPETITIONS:
            raise ValueError("retention evidence requires exactly three repetitions")
        leaf_encode(args.source, args.destination, args); return 0
    if args.operation == "leaf-decode":
        leaf_decode(args.source, args.destination, args.expected_sha,
                    args.expected_length, args.repetitions_manifest); return 0
    raise AssertionError(args.operation)


if __name__ == "__main__":
    raise SystemExit(main())
