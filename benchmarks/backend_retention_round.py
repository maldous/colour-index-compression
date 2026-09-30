#!/usr/bin/env python3
"""Bounded evidence harness for the integrated CIX backend portfolio.

Preparation, dispatch and collection are separate.  The first frozen stage is
only 12 inputs x 3 profiles.  Every portfolio invocation retains every attempt
before selection, plus a standalone payload copy for each external backend.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Direct immutable-snapshot execution needs the copied repository root before
# importing sibling benchmark modules or CIX.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "docs/research/2026-10-01-backend-retention"
BASELINE_AREA = ROOT / "docs/research/2026-10-01-retention-round-v2"
GENERIC_INPUTS = ROOT / "docs/research/2026-09-30-generic-pipeline/inputs.json"
PROFILE_POLICY = ROOT / "docs/research/2026-09-30-codec-profiles/policy.json"
PROFILE_RESULTS = ROOT / "docs/research/2026-09-30-codec-profiles/results.json"
BASELINE_COMMIT = "1302bd7bec130c3105181e6a23ee82c6f2a04838"
INTEGRATION_COMMIT = "ceb41d6442da8454c247fd3aed2b31d50c452ada"
PUBLIC_TO_BACKEND = {"current": "current", "speed": "fast", "size": "size"}
PUBLIC_TO_EFFORT = {"current": "balanced", "speed": "fast", "size": "maximum"}
REPETITIONS = 3
OUTER_BUDGET = {"max_rss_bytes": 2_000_000_000,
                "max_temp_bytes": 100_000_000, "wall_seconds": 180}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(path: Path):
    return json.loads(path.read_text())


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def inputs() -> list[dict]:
    exposed = [dict(row) for row in _json(GENERIC_INPUTS)
        if row["stratum"] in ("development", "heldout")]
    aliases = {"golf": "compression-golf-github-events-prefix",
        "golf-heldout": "compression-golf-github-events-offset-1048576"}
    for row in exposed:
        row["display_label"] = aliases.get(row["label"], row["label"])
        row["exposure"] = "previously examined screening input"
    registry = _json(BASELINE_AREA / "replication-inputs.json")
    fresh = [dict(row) for row in registry["inputs"] if row["stratum"] == "fresh-replication"]
    if len(exposed) != 6 or len(fresh) != 6:
        raise RuntimeError("backend retention requires six exposed and six frozen replication slices")
    for row in fresh:
        row["display_label"] = row["label"]
        row["exposure"] = "frozen before retention evaluation; now shared replication input"
    rows = exposed + fresh
    for row in rows:
        path = Path(row["path"])
        with path.open("rb") as stream:
            stream.seek(int(row["offset"])); data = stream.read(int(row["length"]))
        if len(data) != int(row["length"]) or _sha_bytes(data) != row["sha256"]:
            raise RuntimeError(f"input identity mismatch: {row['label']}")
    return rows


def _baseline_cells() -> dict[tuple[str, str], dict]:
    registry = _json(BASELINE_AREA / "cells.json")
    result = {}
    for cell in registry["cells"]:
        config = cell["configuration"]
        if config["kind"] == "adaptive":
            result[(cell["label"], config["profile"])] = cell
    return result


def _tracked_cix_paths() -> list[str]:
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", INTEGRATION_COMMIT, "--", "cix"],
        cwd=ROOT, text=True).splitlines()
    return sorted(name for name in names if name.endswith(".py"))


def build_paths() -> list[str]:
    return _tracked_cix_paths() + ["benchmarks/backend_retention_round.py",
        "benchmarks/generic_probe.py", "benchmarks/codec_profiles.py",
        "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py",
        "benchmarks/retention_round.py",
        "docs/research/2026-09-30-codec-profiles/policy.json",
        "docs/research/2026-09-30-codec-profiles/results.json",
        "docs/research/2026-09-30-generic-pipeline/inputs.json",
        "docs/research/2026-10-01-retention-round-v2/cells.json",
        "docs/research/2026-10-01-retention-round-v2/replication-inputs.json"]


def snapshot_check() -> dict:
    from cix.backend_portfolio import (HEADER, candidate_plan, coverage_table,
                                        native_cix_inventory)
    policy = _json(PROFILE_POLICY)
    plans = {profile: [row["name"] for row in candidate_plan(profile)]
             for profile in ("fast", "current", "size")}
    if HEADER.size != 47 or not all(plans.values()):
        raise RuntimeError("backend portfolio framing or plans are incomplete")
    return {"header_bytes": HEADER.size, "candidate_plans": plans,
        "coverage": coverage_table(policy), "native_inventory": native_cix_inventory(),
        "inputs": len(inputs()), "status": "READY_NO_COMPRESSION"}


def _copy_snapshot_check(paths: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="cix-backend-snapshot-check-") as directory:
        snapshot = Path(directory)
        for name in paths:
            source, destination = ROOT / name, snapshot / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if _sha(source) != _sha(destination):
                raise RuntimeError(f"snapshot copy mismatch: {name}")
        command = [sys.executable, str(snapshot / "benchmarks/backend_retention_round.py"),
                   "snapshot-check"]
        completed = subprocess.run(command, cwd=snapshot, capture_output=True, text=True,
            timeout=30, check=False)
        if completed.returncode:
            raise RuntimeError("copied snapshot check failed: " + completed.stderr.strip())
        result = json.loads(completed.stdout)
        if result.get("status") != "READY_NO_COMPRESSION" or result.get("inputs") != 12:
            raise RuntimeError("copied snapshot returned unexpected inventory")
        retention_command = [sys.executable,
            str(snapshot / "benchmarks/retention_round.py"), "inventory"]
        retention = subprocess.run(retention_command, cwd=snapshot, capture_output=True,
            text=True, timeout=30, check=False)
        if retention.returncode or json.loads(retention.stdout).get("core_cells") != 864:
            raise RuntimeError("copied retention dependency entrypoint failed: " + retention.stderr.strip())
        return {"command": [sys.executable,
            "<snapshot>/benchmarks/backend_retention_round.py", "snapshot-check"],
            "returncode": completed.returncode, "result": result,
            "retention_entrypoint": {"command": [sys.executable,
                "<snapshot>/benchmarks/retention_round.py", "inventory"],
                "returncode": retention.returncode, "core_cells": 864},
            "dependency_count": len(paths)}


def _time_value(value: str) -> float:
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
            key, value = line.strip().rsplit(": ", 1); fields[key] = value
    key = next((name for name in fields if name.startswith("Elapsed (wall clock) time")), None)
    if key is None:
        raise ValueError(f"missing GNU elapsed time: {path}")
    return {"seconds": _time_value(fields[key]),
        "user_seconds": float(fields.get("User time (seconds)", "0")),
        "system_seconds": float(fields.get("System time (seconds)", "0")),
        "peak_rss_kib": int(fields.get("Maximum resident set size (kbytes)", "0")),
        "raw": str(path)}


def _run_timed(command: list[str], timing: Path, stdout: Path, stderr: Path) -> None:
    with stdout.open("w") as output, stderr.open("w") as errors:
        completed = subprocess.run(["/usr/bin/time", "-v", "-o", str(timing), *command],
            stdout=output, stderr=errors, check=False)
    if completed.returncode:
        raise RuntimeError(f"leaf command failed ({completed.returncode}); see {stderr}")


def _annotate_attempt_artifacts(report: dict, attempt_directory: Path) -> None:
    from cix.backend_portfolio import HEADER
    standalone = attempt_directory / "standalone-payloads"; standalone.mkdir(exist_ok=True)
    verified = []
    for attempt in report["attempts"]:
        if attempt.get("archive_bytes") is None:
            continue
        archive = attempt_directory / f"{attempt['plan_index']:02d}-{attempt['name'].replace(':', '-')}.cix"
        if (not archive.is_file() or archive.stat().st_size != attempt["archive_bytes"]
                or _sha(archive) != attempt["archive_sha256"]):
            raise RuntimeError("attempt artifact differs from portfolio report")
        attempt["artifact"] = {"path": str(archive), "bytes": archive.stat().st_size,
                               "sha256": _sha(archive)}
        detail = attempt.get("detail", {})
        blocks = detail.get("blocks", [])
        if blocks:
            trace = attempt_directory / f"{attempt['plan_index']:02d}-{attempt['name'].replace(':', '-')}.blocks.jsonl"
            trace.write_text("".join(json.dumps(block) + "\n" for block in blocks))
            attempt["trace"] = {"path": str(trace), "sha256": _sha(trace), "blocks": len(blocks)}
            if sum(block["complete_block_bytes"] for block in blocks) + 54 != archive.stat().st_size:
                raise RuntimeError("CIXG1 block accounting does not equal physical archive size")
            if attempt["name"] == "cix-adaptive":
                for block in blocks:
                    completed = [block["source_bytes"] + 41]
                    completed += [trial["bytes"] for trial in block["trials"]
                                  if trial.get("status") == "COMPLETE" and trial.get("bytes") is not None]
                    if block["complete_block_bytes"] != min(completed):
                        raise RuntimeError("adaptive CIX block did not retain its smallest completed trial")
        if attempt["kind"] == "external":
            payload = standalone / f"{attempt['plan_index']:02d}-{attempt['backend']}.payload"
            blob = archive.read_bytes(); payload.write_bytes(blob[HEADER.size:])
            attempt["standalone_artifact"] = {"path": str(payload), "bytes": payload.stat().st_size,
                "sha256": _sha(payload), "framed_bytes": archive.stat().st_size,
                "wrapper_bytes": HEADER.size}
            if (payload.stat().st_size != detail["standalone_payload_bytes"]
                    or archive.stat().st_size != payload.stat().st_size + HEADER.size):
                raise RuntimeError("external standalone/framed accounting mismatch")
        else:
            attempt["standalone_artifact"] = {"path": str(archive),
                "bytes": archive.stat().st_size, "sha256": _sha(archive),
                "framed_bytes": archive.stat().st_size, "wrapper_bytes": 0}
        if attempt.get("status") == "VERIFIED":
            verified.append(attempt)
    if not verified:
        raise RuntimeError("portfolio has no verified attempt")
    framed = min(verified, key=lambda row: (row["archive_bytes"], row["plan_index"]))
    standalone_best = min(verified,
        key=lambda row: (row["standalone_artifact"]["bytes"], row["plan_index"]))
    report["minimum_selection_assertion"] = {
        "passed": report["selected"] == framed["name"]
            and report["compressed_bytes"] == framed["archive_bytes"],
        "selected": report["selected"], "minimum_verified": framed["name"],
        "minimum_verified_bytes": framed["archive_bytes"]}
    if not report["minimum_selection_assertion"]["passed"]:
        raise RuntimeError("portfolio did not select its smallest verified complete archive")
    report["standalone_best"] = {"name": standalone_best["name"],
        "bytes": standalone_best["standalone_artifact"]["bytes"]}
    report["framed_best"] = {"name": framed["name"], "bytes": framed["archive_bytes"]}


def single_encode(source: Path, destination: Path, *, profile: str, policy: Path,
                  receipt: Path, attempt_directory: Path, disabled: list[str]) -> None:
    from cix.backend_portfolio import encode_portfolio
    report = encode_portfolio(source, destination, profile=profile, policy=_json(policy),
        disabled=disabled, attempt_directory=attempt_directory)
    _annotate_attempt_artifacts(report, attempt_directory)
    receipt.write_text(json.dumps(report, indent=2) + "\n")


def single_decode(source: Path, destination: Path, *, policy: Path, receipt: Path) -> None:
    from cix.backend_portfolio import decode_portfolio
    report = decode_portfolio(source, destination, policy=_json(policy))
    receipt.write_text(json.dumps(report, indent=2) + "\n")


def leaf_encode(source: Path, destination: Path, *, public_profile: str,
                policy: Path, disabled: list[str]) -> None:
    root = Path(__file__).resolve().parents[1]; rows = []
    backend_profile = PUBLIC_TO_BACKEND[public_profile]
    for index in range(REPETITIONS):
        directory = destination.parent / "encode-repetitions" / f"rep-{index}"
        directory.mkdir(parents=True, exist_ok=False)
        archive, report = directory / "selected.cix", directory / "portfolio.json"
        attempts = directory / "attempts"; timing = directory / "encode.time.txt"
        command = [sys.executable, str(root / "benchmarks/backend_retention_round.py"),
            "single-encode", str(source), str(archive), "--profile", backend_profile,
            "--policy", str(policy), "--receipt", str(report),
            "--attempt-directory", str(attempts)]
        for name in disabled: command += ["--disable", name]
        _run_timed(command, timing, directory / "stdout.log", directory / "stderr.log")
        detail = _json(report)
        if archive.stat().st_size != detail["compressed_bytes"] or _sha(archive) != detail["archive_sha256"]:
            raise RuntimeError("selected repetition archive differs from portfolio receipt")
        rows.append({"index": index, "archive": str(archive), "bytes": archive.stat().st_size,
            "sha256": _sha(archive), "selected": detail["selected"], "receipt": str(report),
            "attempt_directory": str(attempts), "timing": str(timing), "command": command,
            "minimum_selection_assertion": detail["minimum_selection_assertion"],
            "selected_trace": next((attempt.get("trace") for attempt in detail["attempts"]
                if attempt["name"] == detail["selected"]), None)})
    shutil.copyfile(rows[0]["archive"], destination)
    _write_json(destination.parent / "encode-repetitions.json", {"schema": 1,
        "primary_index": 0, "primary_rule": "predeclared repetition zero; no best-run selection",
        "repetitions": rows, "size_range_bytes": [min(r["bytes"] for r in rows),
                                                   max(r["bytes"] for r in rows)]})


def leaf_decode(destination: Path, *, expected_sha: str, expected_length: int,
                policy: Path, repetitions_manifest: Path) -> None:
    root = Path(__file__).resolve().parents[1]; encoded = _json(repetitions_manifest); rows = []
    for item in encoded["repetitions"]:
        index = item["index"]; directory = destination.parent / "decode-repetitions" / f"rep-{index}"
        directory.mkdir(parents=True, exist_ok=False)
        restored, report = directory / "restored.bin", directory / "decode.json"
        timing = directory / "decode.time.txt"
        command = [sys.executable, str(root / "benchmarks/backend_retention_round.py"),
            "single-decode", item["archive"], str(restored), "--policy", str(policy),
            "--receipt", str(report)]
        _run_timed(command, timing, directory / "stdout.log", directory / "stderr.log")
        if restored.stat().st_size != expected_length or _sha(restored) != expected_sha:
            raise RuntimeError(f"selected repetition {index} failed archive-only restoration")
        rows.append({"index": index, "archive": item["archive"], "restored": str(restored),
            "bytes": restored.stat().st_size, "sha256": _sha(restored),
            "receipt": str(report), "timing": str(timing), "command": command})
    shutil.copyfile(rows[0]["restored"], destination)
    _write_json(destination.parent / "decode-repetitions.json", {"schema": 1,
        "source_inaccessible": True, "repetitions": rows})


def diagnostic_single_encode(source: Path, destination: Path, *, backend: str,
                             policy: Path, receipt: Path) -> None:
    """Create an explicitly non-production fast bzip2/XZ CIXB1 diagnostic."""
    if backend not in ("bzip2", "xz"):
        raise ValueError("diagnostic backend must be bzip2 or xz")
    from cix.backend_portfolio import BACKEND_IDS, HEADER, MAGIC, PROFILE_IDS
    root = Path(__file__).resolve().parents[1]
    payload = destination.with_suffix(".payload")
    command = [sys.executable, str(root / "benchmarks/codec_profiles.py"), "encode",
        "--leaf", "--method", backend, "--profile", "fast", "--policy", str(policy),
        str(source), str(payload)]
    subprocess.run(command, check=True)
    data = source.read_bytes(); blob = payload.read_bytes()
    destination.write_bytes(HEADER.pack(MAGIC, BACKEND_IDS[backend], PROFILE_IDS["fast"],
        len(data), len(blob), hashlib.sha256(data).digest()) + blob)
    report = {"status": "COMPLETE_DIAGNOSTIC_SHORTLISTED_OUT", "backend": backend,
        "profile": "fast", "preset_source": "benchmarks.codec_profiles.SETTINGS",
        "standalone_payload": {"path": str(payload), "bytes": len(blob), "sha256": _sha(payload)},
        "wrapper_bytes": HEADER.size, "framed_bytes": destination.stat().st_size,
        "framed_sha256": _sha(destination), "production_eligible": False,
        "reason": "generic-policy-compatible reference preset intentionally shortlisted out of the fast production plan",
        "leaf_command": command}
    if destination.stat().st_size != len(blob) + HEADER.size:
        raise RuntimeError("diagnostic envelope accounting mismatch")
    receipt.write_text(json.dumps(report, indent=2) + "\n")


def diagnostic_leaf_encode(source: Path, destination: Path, *, backend: str,
                           policy: Path) -> None:
    root = Path(__file__).resolve().parents[1]; rows = []
    for index in range(REPETITIONS):
        directory = destination.parent / "encode-repetitions" / f"rep-{index}"
        directory.mkdir(parents=True, exist_ok=False)
        archive, report = directory / "selected.cix", directory / "diagnostic.json"
        timing = directory / "encode.time.txt"
        command = [sys.executable, str(root / "benchmarks/backend_retention_round.py"),
            "diagnostic-single-encode", str(source), str(archive), "--backend", backend,
            "--policy", str(policy), "--receipt", str(report)]
        _run_timed(command, timing, directory / "stdout.log", directory / "stderr.log")
        rows.append({"index": index, "archive": str(archive), "bytes": archive.stat().st_size,
            "sha256": _sha(archive), "selected": backend + ":direct-diagnostic",
            "receipt": str(report), "timing": str(timing), "command": command,
            "minimum_selection_assertion": {"passed": True, "scope": "single diagnostic candidate"}})
    shutil.copyfile(rows[0]["archive"], destination)
    _write_json(destination.parent / "encode-repetitions.json", {"schema": 1,
        "primary_index": 0, "primary_rule": "predeclared repetition zero",
        "repetitions": rows, "size_range_bytes": [min(r["bytes"] for r in rows),
                                                   max(r["bytes"] for r in rows)]})


def inventory() -> dict:
    rows = inputs(); baseline = _baseline_cells()
    return {"inputs": len(rows), "profiles": PUBLIC_TO_BACKEND,
        "integrated_cells": len(rows) * len(PUBLIC_TO_BACKEND),
        "optional_native_recode_cells": len(rows) * len(PUBLIC_TO_BACKEND),
        "fast_shortlist_diagnostic_cells": len(rows) * 2,
        "scaling_integrated_cells": 6 * 2, "scaling_baseline_cells": 6 * 2,
        "matched_baseline_cells": sum((row["label"], profile) in baseline
            for row in rows for profile in PUBLIC_TO_BACKEND),
        "repetitions": REPETITIONS, "outer_budget": OUTER_BUDGET,
        "aggregate_budget": {"jobs": 4, "memory_bytes": 12_000_000_000,
            "temp_bytes": 4_000_000_000, "swap": "disabled"}}


def _configuration(public_profile: str, *, mode="integrated", disabled=(), backend=None) -> dict:
    return {"profile": public_profile, "backend_profile": PUBLIC_TO_BACKEND[public_profile],
        "mode": mode, "disabled": list(disabled), "diagnostic_backend": backend,
        "repetitions": REPETITIONS,
        "warmups": 0, "startup_included": True}


def _make_cell(inp: dict, config: dict, cpu: int, freeze: dict, baseline_cell: dict | None) -> dict:
    script = str(ROOT / "benchmarks/backend_retention_round.py")
    mode = config["mode"]
    if mode in ("optional-native-recode", "scaling-baseline"):
        retention = str(ROOT / "benchmarks/retention_round.py")
        flags = ["--effort", PUBLIC_TO_EFFORT[config["profile"]], "--backend", "hybrid",
                 "--repetitions", str(REPETITIONS)]
        if mode == "optional-native-recode": flags.append("--recode")
        encode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/encode.outer.time.txt",
            sys.executable, retention, "leaf-encode", "{source}", "{workdir}/candidate.bin", *flags]
        decode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/decode.outer.time.txt",
            sys.executable, retention, "leaf-decode", "{workdir}/candidate.bin", "{workdir}/restored.bin",
            "--expected-sha", inp["sha256"], "--expected-length", str(inp["length"]),
            "--repetitions-manifest", "{workdir}/encode-repetitions.json"]
        mechanism = ("optional one-pass native CIX composition recode with paid 37-byte CIXR1 metadata; "
            "unwrapped adaptive CIXG1 retained byte-for-byte unless recode is strictly smaller"
            if mode == "optional-native-recode" else
            "unchanged adaptive CIXG1 control on a pre-frozen 64 KiB scaling range")
    elif mode == "fast-shortlist-diagnostic":
        encode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/encode.outer.time.txt",
            sys.executable, script, "diagnostic-leaf-encode", "{source}", "{workdir}/candidate.bin",
            "--backend", config["diagnostic_backend"], "--policy", str(PROFILE_POLICY)]
        decode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/decode.outer.time.txt",
            sys.executable, script, "leaf-decode", "{workdir}/restored.bin",
            "--expected-sha", inp["sha256"], "--expected-length", str(inp["length"]),
            "--policy", str(PROFILE_POLICY),
            "--repetitions-manifest", "{workdir}/encode-repetitions.json"]
        mechanism = "fast bzip2/XZ exact ranked standalone preset plus paid 47-byte CIXB1 diagnostic envelope; explicitly excluded from production fast shortlist"
    else:
        flags = ["--public-profile", config["profile"], "--policy", str(PROFILE_POLICY)]
        for name in config["disabled"]: flags += ["--disable", name]
        encode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/encode.outer.time.txt",
            sys.executable, script, "leaf-encode", "{source}", "{workdir}/candidate.bin", *flags]
        decode_command = ["/usr/bin/time", "-v", "-o", "{workdir}/decode.outer.time.txt",
            sys.executable, script, "leaf-decode", "{workdir}/restored.bin",
            "--expected-sha", inp["sha256"], "--expected-length", str(inp["length"]),
            "--policy", str(PROFILE_POLICY),
            "--repetitions-manifest", "{workdir}/encode-repetitions.json"]
        mechanism = "complete original-byte reference archives receive a paid 47-byte CIXB1 envelope; native CIXG1 stays byte-identical; every completed candidate is independently validated before complete-size selection"
    manifest = {"hypothesis": "The integrated generic CIX portfolio retains the smallest complete exact-verified archive among its declared eligible candidates, including external framing, then exposes any remaining backend or native-CIX contribution.",
        "matched_control": "Same exact input, ranked reference preset, frozen commit-1302bd7 CIX implementation, integrated backend implementation hash, empty state, three startup-inclusive repetitions, identical outer limits; v2 adaptive identity linked where available.",
        "input": inp, "configuration": config, "mechanism": mechanism,
        "budget": {"cpu": cpu, **OUTER_BUDGET},
        "promotion_criteria": "Every selected repetition is the minimum complete VERIFIED attempt, all attempts and standalone payloads remain physical, and all three selected archives restore exactly in source-inaccessible decode processes.",
        "encode_command": encode_command, "decode_command": decode_command,
        "artifacts": {"archive": "{workdir}/candidate.bin", "restored": "{workdir}/restored.bin"},
        "build_paths": freeze["build_paths"], "initial_state": "empty for every repetition",
        "stage": "screening", "matrix_stage": config["mode"],
        "source_freeze": freeze["sha256"],
        "matched_v2_baseline_cell_id": baseline_cell["cell_id"] if baseline_cell else None,
        "timing_policy": "no warmup; encode includes every discarded candidate plus validation; selected-route production decode separately measured three times"}
    identity = hashlib.sha256(canonical({"manifest": manifest,
        "build": build_identity(manifest, ROOT)})).hexdigest()[:24]
    cell_id = "backend-retention-" + identity
    path = AREA / "manifests" / f"{cell_id}.json"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(manifest) + b"\n"); _, manifest_sha = load_manifest(path)
    return {"cell_id": cell_id, "owner": "/root/retention_harness",
        "manifest_path": str(path), "output_dir": str(AREA / "runs" / cell_id),
        "expected_manifest_sha256": manifest_sha,
        "expected_build_sha256": build_identity(manifest, ROOT), "label": inp["label"],
        "matrix_stage": config["mode"], "configuration": config,
        "matched_v2_baseline_cell_id": baseline_cell["cell_id"] if baseline_cell else None}


def prepare(backend_sha256: str) -> dict:
    if (AREA / "source-freeze.json").exists() or (AREA / "cells.json").exists():
        raise RuntimeError("backend retention is already frozen")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != INTEGRATION_COMMIT:
        raise RuntimeError("canonical HEAD differs from the reviewed integration commit")
    backend = ROOT / "cix/backend_portfolio.py"
    if _sha(backend) != backend_sha256:
        raise ValueError("--backend-sha256 does not match the reviewed implementation")
    paths = build_paths(); tracked = set(_tracked_cix_paths()) | {
        "benchmarks/generic_probe.py", "benchmarks/codec_profiles.py", "benchmarks/hutter_bounded_runner.py",
        "benchmarks/hutter_experiment_scheduler.py",
        "docs/research/2026-09-30-codec-profiles/policy.json",
        "docs/research/2026-09-30-codec-profiles/results.json",
        "docs/research/2026-09-30-generic-pipeline/inputs.json"}
    mismatched = []
    for name in sorted(tracked):
        committed = subprocess.check_output(["git", "show", f"{INTEGRATION_COMMIT}:{name}"], cwd=ROOT)
        if _sha_bytes(committed) != _sha(ROOT / name): mismatched.append(name)
    if mismatched:
        raise RuntimeError("tracked integration closure differs from reviewed commit: " + ", ".join(mismatched))
    copied_check = _copy_snapshot_check(paths)
    freeze = {"schema": 1, "frozen_at": _now(), "source_commit": INTEGRATION_COMMIT,
        "baseline_cix_commit": BASELINE_COMMIT,
        "backend_portfolio_sha256": backend_sha256, "build_paths": paths,
        "build_sha256": {name: _sha(ROOT / name) for name in paths},
        "snapshot_entrypoint_check": copied_check,
        "baseline_source_freeze": _json(BASELINE_AREA / "source-freeze.json")["sha256"]}
    freeze["sha256"] = _sha_bytes(canonical(freeze)); AREA.mkdir(parents=True, exist_ok=True)
    _write_json(AREA / "source-freeze.json", freeze)
    cpus = _physical_cpus(); baseline = _baseline_cells(); cells = []
    for index, inp in enumerate(inputs()):
        for profile in PUBLIC_TO_BACKEND:
            config = _configuration(profile)
            cells.append(_make_cell(inp, config, cpus[len(cells) % 4], freeze,
                                    baseline.get((inp["label"], profile))))
            recode = _configuration(profile, mode="optional-native-recode")
            cells.append(_make_cell(inp, recode, cpus[len(cells) % 4], freeze,
                                    baseline.get((inp["label"], profile))))
        for backend in ("bzip2", "xz"):
            diagnostic = _configuration("speed", mode="fast-shortlist-diagnostic", backend=backend)
            cells.append(_make_cell(inp, diagnostic, cpus[len(cells) % 4], freeze,
                                    baseline.get((inp["label"], "speed"))))
    scaling = [row for row in _json(BASELINE_AREA / "replication-inputs.json")["inputs"]
               if row["stratum"] == "fresh-scaling"]
    if len(scaling) != 6: raise RuntimeError("expected six frozen 64 KiB scaling ranges")
    for inp in scaling:
        for profile in ("current", "size"):
            integrated = _configuration(profile, mode="scaling-integrated")
            cells.append(_make_cell(inp, integrated, cpus[len(cells) % 4], freeze, None))
            control = _configuration(profile, mode="scaling-baseline")
            cells.append(_make_cell(inp, control, cpus[len(cells) % 4], freeze, None))
    _write_json(AREA / "cells.json", {"schema": 1, "status": "FROZEN_NOT_AUTHORIZED",
        "source_freeze": freeze["sha256"], "cells": cells})
    _write_json(AREA / "results.json", {"schema": 1, "status": "NOT_RUN", "rows": []})
    summary = inventory() | {"source_freeze": freeze["sha256"], "cells": len(cells),
        "backend_portfolio_sha256": backend_sha256}
    _write_json(AREA / "plan-summary.json", summary); return summary


def _authorization(stages: set[str], path: Path) -> None:
    auth, freeze = _json(path), _json(AREA / "source-freeze.json")
    if (auth.get("authorized_by") != "/root" or auth.get("source_freeze") != freeze["sha256"]
            or not stages <= set(auth.get("authorized_stages", []))):
        raise PermissionError("root authorization does not cover this frozen stage")


def _registries() -> list[dict]:
    rows = list(_json(AREA / "cells.json")["cells"])
    extra = AREA / "counterfactual-cells.json"
    if extra.exists(): rows += _json(extra)["cells"]
    return rows


def run(stages: set[str], authorization: Path) -> None:
    _authorization(stages, authorization)
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000,
                              max_temp_bytes=4_000_000_000)
    cells = [cell for cell in _registries() if cell["matrix_stage"] in stages
             and not scheduler._terminal_path(cell["cell_id"]).exists()]
    while cells:
        wave, cpus = [], set()
        for cell in cells:
            cpu = _json(Path(cell["manifest_path"]))["budget"]["cpu"]
            if cpu not in cpus: wave.append(cell); cpus.add(cpu)
            if len(wave) == 4: break
        outcomes = scheduler.run_wave(wave)
        for cell in wave: cells.remove(cell)
        print(json.dumps({"at": _now(), "remaining": len(cells),
            "wave": [cell["cell_id"] for cell in wave],
            "outcomes": [row.get("runner_status", row.get("status")) for row in outcomes]}), flush=True)
        if any(row.get("runner_status") not in ("VERIFIED_SCREENING", "REUSED_VERIFIED")
               for row in outcomes):
            raise RuntimeError("backend retention stopped after a failed bounded cell")
    collect()


def _aggregate(repetitions: list[dict]) -> dict:
    for row in repetitions: row["measurement"] = _timing(Path(row["timing"]))
    values = [row["measurement"]["seconds"] for row in repetitions]
    median = statistics.median(values)
    return {"seconds": median, "min_seconds": min(values), "max_seconds": max(values),
        "mad_seconds": statistics.median(abs(value - median) for value in values),
        "peak_rss_kib": max(row["measurement"]["peak_rss_kib"] for row in repetitions)}


def _reference_index() -> dict[tuple[str, str, str], dict]:
    if not PROFILE_RESULTS.exists(): return {}
    result = {}
    for row in _json(PROFILE_RESULTS):
        config = row.get("config", {})
        if row.get("status") == "VERIFIED_SCREENING":
            result[(row["label"], config.get("profile"), config.get("method"))] = row
    return result


def collect() -> dict:
    references = _reference_index(); rows = []
    for cell in _registries():
        paths = list(Path(cell["output_dir"]).glob("*/receipt.json"))
        paths += list(Path(cell["output_dir"]).glob("*/failed.json"))
        row = {"cell_id": cell["cell_id"], "label": cell["label"],
            "matrix_stage": cell["matrix_stage"], "configuration": cell["configuration"],
            "matched_v2_baseline_cell_id": cell.get("matched_v2_baseline_cell_id"),
            "status": "PENDING"}
        if paths:
            if len(paths) != 1: raise RuntimeError("ambiguous bounded receipt")
            receipt = _json(paths[0]); work = paths[0].parent / "work"
            row.update(status=receipt["status"], receipt=str(paths[0]),
                archive_bytes=receipt.get("archive_bytes"), archive_sha256=receipt.get("archive_sha256"),
                verification=receipt["verification"], budget=receipt["budget"], phases=receipt["phases"])
            if receipt["status"] == "VERIFIED_SCREENING":
                enc = _json(work / "encode-repetitions.json")["repetitions"]
                dec = _json(work / "decode-repetitions.json")["repetitions"]
                if len(enc) != REPETITIONS or len(dec) != REPETITIONS:
                    raise RuntimeError("qualified cell lacks three repetitions")
                mode = cell["configuration"]["mode"]
                reports = []
                for repetition in enc:
                    if (_sha(Path(repetition["archive"])) != repetition["sha256"]
                            or Path(repetition["archive"]).stat().st_size != repetition["bytes"]):
                        raise RuntimeError("selected repetition artifact changed")
                    if mode in ("optional-native-recode", "scaling-baseline"):
                        report = _json(Path(repetition["codec"])); reports.append(report)
                        if mode == "optional-native-recode":
                            recode = report["optional_native_cix_recode"]
                            if recode["selected_bytes"] != min(recode["baseline_bytes"], recode["recode_bytes"]):
                                raise RuntimeError("optional recode failed strict minimum selection")
                    else:
                        report = _json(Path(repetition["receipt"])); reports.append(report)
                        if not repetition["minimum_selection_assertion"]["passed"]:
                            raise RuntimeError("minimum selection assertion failed")
                        for attempt in report.get("attempts", []):
                            if attempt.get("status") == "VERIFIED" and attempt["kind"] == "external":
                                ref = references.get((cell["label"],
                                    "fast" if cell["configuration"]["profile"] == "speed" else cell["configuration"]["profile"],
                                    attempt["backend"]))
                                if ref:
                                    attempt["matched_standalone_reference"] = {"cell_id": ref["cell_id"],
                                        "bytes": ref["bytes"], "archive_sha256": ref["archive_sha256"],
                                        "bytes_match": ref["bytes"] == attempt["standalone_artifact"]["bytes"],
                                        "sha256_match": ref["archive_sha256"] == attempt["standalone_artifact"]["sha256"]}
                if any(item["sha256"] != receipt["identity"]["input"]["sha256"] for item in dec):
                    raise RuntimeError("archive-only decode repetition mismatch")
                common = {"encode_repetitions": enc, "decode_repetitions": dec,
                    "encode": _aggregate(enc), "decode": _aggregate(dec)}
                if mode in ("optional-native-recode", "scaling-baseline"):
                    selected = (reports[0].get("optional_native_cix_recode", {}).get("selected")
                        or next(iter(reports[0].get("route_usage_source_bytes", {"unknown": 0}))))
                    common.update(adaptive_reports=reports, selected=selected,
                        minimum_selection_assertion=True,
                        selection_encode_wall_seconds=[r.get("selection_total_seconds") for r in reports],
                        candidate_validation_wall_seconds=[0.0] * REPETITIONS,
                        total_audit_wall_seconds=[r.get("encode_seconds") for r in reports])
                elif mode == "fast-shortlist-diagnostic":
                    common.update(diagnostic_reports=reports, selected=enc[0]["selected"],
                        minimum_selection_assertion=True,
                        selection_encode_wall_seconds=[r["measurement"]["seconds"] for r in enc],
                        candidate_validation_wall_seconds=[0.0] * REPETITIONS,
                        total_audit_wall_seconds=[r["measurement"]["seconds"] for r in enc])
                else:
                    common.update(portfolio_reports=reports, selected=reports[0]["selected"],
                        minimum_selection_assertion=all(r["minimum_selection_assertion"]["passed"] for r in reports),
                        selection_encode_wall_seconds=[r["selection_encode_wall_seconds"] for r in reports],
                        candidate_validation_wall_seconds=[r["candidate_validation_wall_seconds"] for r in reports],
                        total_audit_wall_seconds=[r["total_audit_wall_seconds"] for r in reports])
                row.update(common)
        rows.append(row)
    result = {"schema": 1, "collected_at": _now(),
        "source_freeze": _json(AREA / "source-freeze.json")["sha256"],
        "counts": dict(Counter(row["status"] for row in rows)), "rows": rows}
    _write_json(AREA / "results.json", result); return result


def prepare_counterfactuals() -> dict:
    destination = AREA / "counterfactual-cells.json"
    if destination.exists(): raise RuntimeError("counterfactual identities already frozen")
    result = collect(); completed = [row for row in result["rows"] if row["matrix_stage"] == "integrated"]
    if len(completed) != 36 or any(row["status"] != "VERIFIED_SCREENING" for row in completed):
        raise RuntimeError("all 36 integrated cells must verify before counterfactual preparation")
    freeze = _json(AREA / "source-freeze.json"); cpus = _physical_cpus(); by_label = {row["label"]: row for row in inputs()}
    cells = []
    from cix.backend_portfolio import PROFILE_BACKENDS
    for row in completed:
        selected = row["selected"]; profile = row["configuration"]["profile"]
        configs = [_configuration(profile, mode="counterfactual-disable-selected", disabled=[selected])]
        if selected.endswith(":direct"):
            configs.append(_configuration(profile, mode="counterfactual-native-only",
                disabled=list(PROFILE_BACKENDS[PUBLIC_TO_BACKEND[profile]])))
        else:
            configs.append(_configuration(profile, mode="counterfactual-external-with-raw-fallback", disabled=["cix"]))
        for config in configs:
            cells.append(_make_cell(by_label[row["label"]], config, cpus[len(cells) % 4],
                                    freeze, {"cell_id": row["matched_v2_baseline_cell_id"]}
                                    if row["matched_v2_baseline_cell_id"] else None))
    _write_json(destination, {"schema": 1, "status": "FROZEN_NOT_AUTHORIZED",
        "source_freeze": freeze["sha256"], "based_on_results_sha256": _sha(AREA / "results.json"),
        "cells": cells})
    return {"counterfactual_cells": len(cells), "source_freeze": freeze["sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("inventory"); commands.add_parser("snapshot-check")
    prepare_parser = commands.add_parser("prepare"); prepare_parser.add_argument("--backend-sha256", required=True)
    run_parser = commands.add_parser("run"); run_parser.add_argument("--stage", action="append", required=True); run_parser.add_argument("--authorization", type=Path, required=True)
    commands.add_parser("collect"); commands.add_parser("prepare-counterfactuals")
    single = commands.add_parser("single-encode"); single.add_argument("source", type=Path); single.add_argument("destination", type=Path); single.add_argument("--profile", required=True); single.add_argument("--policy", type=Path, required=True); single.add_argument("--receipt", type=Path, required=True); single.add_argument("--attempt-directory", type=Path, required=True); single.add_argument("--disable", action="append", default=[])
    single_dec = commands.add_parser("single-decode"); single_dec.add_argument("source", type=Path); single_dec.add_argument("destination", type=Path); single_dec.add_argument("--policy", type=Path, required=True); single_dec.add_argument("--receipt", type=Path, required=True)
    diagnostic_single = commands.add_parser("diagnostic-single-encode"); diagnostic_single.add_argument("source", type=Path); diagnostic_single.add_argument("destination", type=Path); diagnostic_single.add_argument("--backend", choices=("bzip2", "xz"), required=True); diagnostic_single.add_argument("--policy", type=Path, required=True); diagnostic_single.add_argument("--receipt", type=Path, required=True)
    diagnostic_leaf = commands.add_parser("diagnostic-leaf-encode"); diagnostic_leaf.add_argument("source", type=Path); diagnostic_leaf.add_argument("destination", type=Path); diagnostic_leaf.add_argument("--backend", choices=("bzip2", "xz"), required=True); diagnostic_leaf.add_argument("--policy", type=Path, required=True)
    leaf = commands.add_parser("leaf-encode"); leaf.add_argument("source", type=Path); leaf.add_argument("destination", type=Path); leaf.add_argument("--public-profile", choices=PUBLIC_TO_BACKEND, required=True); leaf.add_argument("--policy", type=Path, required=True); leaf.add_argument("--disable", action="append", default=[])
    leaf_dec = commands.add_parser("leaf-decode"); leaf_dec.add_argument("destination", type=Path); leaf_dec.add_argument("--expected-sha", required=True); leaf_dec.add_argument("--expected-length", type=int, required=True); leaf_dec.add_argument("--policy", type=Path, required=True); leaf_dec.add_argument("--repetitions-manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "inventory": print(json.dumps(inventory(), indent=2)); return 0
    if args.operation == "snapshot-check": print(json.dumps(snapshot_check(), indent=2)); return 0
    if args.operation == "prepare": print(json.dumps(prepare(args.backend_sha256), indent=2)); return 0
    if args.operation == "run": run(set(args.stage), args.authorization); return 0
    if args.operation == "collect": print(json.dumps(collect()["counts"])); return 0
    if args.operation == "prepare-counterfactuals": print(json.dumps(prepare_counterfactuals(), indent=2)); return 0
    if args.operation == "single-encode": single_encode(args.source, args.destination, profile=args.profile, policy=args.policy, receipt=args.receipt, attempt_directory=args.attempt_directory, disabled=args.disable); return 0
    if args.operation == "single-decode": single_decode(args.source, args.destination, policy=args.policy, receipt=args.receipt); return 0
    if args.operation == "diagnostic-single-encode": diagnostic_single_encode(args.source, args.destination, backend=args.backend, policy=args.policy, receipt=args.receipt); return 0
    if args.operation == "diagnostic-leaf-encode": diagnostic_leaf_encode(args.source, args.destination, backend=args.backend, policy=args.policy); return 0
    if args.operation == "leaf-encode": leaf_encode(args.source, args.destination, public_profile=args.public_profile, policy=args.policy, disabled=args.disable); return 0
    if args.operation == "leaf-decode": leaf_decode(args.destination, expected_sha=args.expected_sha, expected_length=args.expected_length, policy=args.policy, repetitions_manifest=args.repetitions_manifest); return 0
    raise AssertionError(args.operation)


if __name__ == "__main__":
    raise SystemExit(main())
