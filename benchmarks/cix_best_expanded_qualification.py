#!/usr/bin/env python3
"""Freeze, queue, and collect a BEST-only qualification for an expanded Rust CIX.

This deliberately consumes the existing frozen CCA and Squash catalog inputs.
It does not build an artifact, download data, or dispatch unless ``--queue``
is explicitly supplied.  The queue waits for the one Hutter reservation and
uses the repository WaveScheduler; it never creates a competing scheduler.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.cix_full_catalog import cca_inputs, catalog_inputs, frozen_references, require_cpus
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest, sha256, NATIVE_CATALOG_AUTHORIZATION
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.cix_dickens_best_compare import gnu_time, selector_log, typed_whole_archive_ledger

AREA_ROOT = ROOT / "docs/research/2026-10-02-best-expanded"
CATALOG_AREA = ROOT / "docs/research/2026-10-02-rust-full-catalog/native-catalog-d667-v3"
HUTTER_ROOT = ROOT / "docs/research/2026-10-02-rust-hutter-qualification"
HOST_RUNTIME = ROOT / "docs/research/2026-10-02-rust-full-catalog/host-runtime.json"
CPUS = [16, 17, 18, 19]
# BEST owns a 2 GiB codec working budget.  The cgroup must leave room for the
# executable, allocator and complete framed candidate without converting an
# ordinary BEST trial into an artificial memory failure.
BEST_DEFAULT_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
RSS_BYTES, TEMP_BYTES, WALL_SECONDS = 3_000_000_000, 1_000_000_000, 7_200
OLD_CATALOG_REVISION = "d66739120c40fc409f2bf011b165389fc1062c2b"
REVISION = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_GNU_TIME = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
EXTERNAL_SOURCE = ROOT / "rust/cix-native/src/external.rs"
PORTFOLIO_SOURCE = ROOT / "rust/cix-native/src/portfolio_auto.rs"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    value = path.resolve()
    if ROOT != value and ROOT not in value.parents:
        raise ValueError(f"path outside repository: {value}")
    return str(value.relative_to(ROOT))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def git_state() -> dict:
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    if revision.returncode:
        raise RuntimeError("cannot determine source revision")
    diff = subprocess.run(["git", "diff", "--binary", "HEAD", "--", "rust/cix-native", "benchmarks"], cwd=ROOT,
                          capture_output=True, check=False)
    if diff.returncode:
        raise RuntimeError("cannot snapshot current source state")
    untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", "rust/cix-native", "benchmarks"],
                              cwd=ROOT, text=True, capture_output=True, check=False)
    if untracked.returncode:
        raise RuntimeError("cannot enumerate untracked native source content")
    untracked_hashes = {}
    for name in sorted(line for line in untracked.stdout.splitlines() if line):
        candidate = ROOT / name
        if not candidate.is_file():
            raise RuntimeError(f"untracked source is not a regular file: {name}")
        untracked_hashes[name] = sha256(candidate)
    # Aggregate hashes make the release metadata compact while the per-file
    # map remains audit evidence.  Unrelated logs elsewhere in the repository
    # intentionally do not affect a native artifact's source provenance.
    return {"revision": revision.stdout.strip(), "dirty_diff_sha256": hashlib.sha256(diff.stdout).hexdigest(),
            "untracked_source_sha256": hashlib.sha256(canonical(untracked_hashes)).hexdigest(),
            "untracked_source_files": untracked_hashes}


def artifact_identity(directory: Path) -> dict:
    directory = directory.resolve()
    if ROOT not in directory.parents:
        raise ValueError("artifact directory must be within the repository")
    metadata_path = directory / "native-release.json"
    if not metadata_path.is_file():
        raise ValueError("missing native-release.json")
    metadata = json.loads(metadata_path.read_text())
    source_revision = metadata.get("source_revision")
    if not isinstance(source_revision, str) or not REVISION.fullmatch(source_revision):
        raise ValueError("artifact metadata must contain a lowercase 40-hex source_revision")
    resolved = subprocess.run(["git", "rev-parse", "--verify", f"{source_revision}^{{commit}}"], cwd=ROOT,
                              text=True, capture_output=True, check=False)
    if resolved.returncode or resolved.stdout.strip() != source_revision:
        raise ValueError("artifact metadata source_revision is not an available exact commit")
    current_source = git_state()
    declared_source = metadata.get("build_source_state")
    if not isinstance(declared_source, dict):
        raise ValueError("artifact metadata must bind build_source_state")
    for key in ("revision", "dirty_diff_sha256", "untracked_source_sha256"):
        if declared_source.get(key) != current_source[key]:
            raise ValueError(f"artifact build_source_state does not match current relevant source: {key}")
    if source_revision != current_source["revision"]:
        raise ValueError("artifact source_revision must equal current HEAD")
    if metadata.get("source_revision") == OLD_CATALOG_REVISION:
        raise ValueError("expanded BEST requires a new artifact, not the frozen d667/512 MiB catalog release")
    # A release must explicitly state the ordinary BEST default.  The old
    # metadata had no such assertion and corresponded to the legacy 512 MiB
    # policy, so accepting it would make this plan silently test the wrong
    # product behaviour.
    defaults = metadata.get("selector_defaults", {})
    qualified = metadata.get("qualification", {}).get("selector_defaults", {})
    declared_memory = metadata.get("best_default_memory_bytes", defaults.get("best_memory_bytes", qualified.get("best_memory_bytes")))
    if declared_memory != BEST_DEFAULT_MEMORY_BYTES:
        raise ValueError("artifact metadata must declare ordinary BEST default memory as 2147483648 bytes")
    expected_descriptors = descriptor_ids_from_source()
    declared_descriptors = metadata.get("candidate_registry")
    if declared_descriptors != expected_descriptors:
        raise ValueError("artifact candidate_registry must exactly match the 14 current CIXB1 BEST descriptors")
    binaries = metadata.get("binaries")
    if not isinstance(binaries, dict) or not {"cix", "uncix"}.issubset(binaries):
        raise ValueError("artifact metadata lacks cix/uncix")
    frozen = {}
    for name, declared in sorted(binaries.items()):
        candidate = directory / name
        actual = sha256(candidate) if candidate.is_file() else None
        if not candidate.is_file() or actual != declared.get("sha256"):
            raise ValueError(f"artifact does not match metadata: {name}")
        if name in {"cix", "uncix"} and not os.access(candidate, os.X_OK):
            raise ValueError(f"native client is not executable: {name}")
        frozen[name] = {"path": rel(candidate), "bytes": candidate.stat().st_size, "sha256": actual,
                        "kind": "native_build_library" if candidate.suffix in {".so", ".a"} else "native_client"}
    return {"directory": rel(directory), "metadata": rel(metadata_path), "metadata_sha256": sha256(metadata_path),
            "source_revision": source_revision, "binaries": frozen, "source_state": current_source,
            "build_source_state": declared_source,
            "candidate_registry": declared_descriptors,
            "provenance_binding": {"metadata_source_revision_equals_head": True,
                                   "tracked_dirty_diff_matches": True,
                                   "untracked_source_digest_matches": True}}


def inputs() -> tuple[list[dict], dict]:
    references = frozen_references()
    catalog, unavailable, catalog_meta = catalog_inputs(references)
    if unavailable:
        raise RuntimeError("expanded BEST cannot freeze missing catalog inputs")
    gate = cca_inputs(catalog, references)
    post_gate = [row for row in catalog if row["stage"] == "catalog"]
    rows = gate + post_gate
    if len(gate) != 33 or len(post_gate) != 17 or len(rows) != 50 or len({x["label"] for x in rows}) != 50:
        raise RuntimeError("expected 33 CCA inputs plus 17 non-overlapping catalog inputs")
    return rows, {"frozen_references": references["sources"], "acquisition_cutoff_utc": references["acquisition_cutoff_utc"],
                  "catalog_manifest": {k: v for k, v in catalog_meta.items() if k != "datasets"}}


def descriptor_ids_from_source() -> list[str]:
    """Freeze the source-defined CIXB1 BEST descriptor identity, not a hand list."""
    text = EXTERNAL_SOURCE.read_text()
    marker, end = "const CIXB1_BEST_CANDIDATES", "];\n\n/// Every direct backend"
    try: section = text[text.index(marker):text.index(end, text.index(marker))]
    except ValueError as error: raise RuntimeError("cannot find CIXB1 BEST candidate registry") from error
    ids = re.findall(r'\bid:\s*"([^"]+)"', section)
    if len(ids) != 14 or len(set(ids)) != 14:
        raise RuntimeError("current CIXB1 BEST candidate registry must contain exactly fourteen unique descriptors")
    return ids


def native_trial_ids(input_bytes: int) -> list[str]:
    blocks = [16 * 1024, 32 * 1024, 64 * 1024] if input_bytes <= 16 * 1024 * 1024 else [64 * 1024]
    return [f"{container}:native-auto:block={block}" for container in ("cixg1", "cixg2", "cixm6") for block in blocks]


def phase_command(status_file: str, command: list[str]) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "phase", status_file, *command]


def manifest(row: dict, artifact: dict, identity: str, registry: dict) -> dict:
    cix, uncix = artifact["binaries"]["cix"]["path"], artifact["binaries"]["uncix"]["path"]
    encode = ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(ROOT / cix), "--best", "--verbose",
              "-o", "{workdir}/candidate.cix", "{source}"]
    decode = ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(ROOT / uncix),
              "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"]
    return {
        "hypothesis": "The expanded automatic Rust BEST selector evaluates every qualified native and wrapped candidate permitted by its 2 GiB resource policy, choosing the smallest complete exact-lossless CIX archive.",
        "matched_control": "Every cell uses one frozen complete input, ordinary --best automatic selection, a fresh encoder, a fresh archive-only native decoder, four physical CPUs, a 3 GB no-swap RSS cap, no swap and GNU Time.",
        "input": {"path": str(row["path"].resolve()), "offset": 0, "length": row["bytes"], "sha256": row["sha256"],
                  "label": row["label"], "catalog_id": row["catalog_id"]},
        "study_identity": identity,
        "configuration": {"effort": "best", "flags": ["--best", "--verbose"],
                          "automatic_selection": True, "advanced_overrides": [],
                          "expected_ordinary_best_memory_bytes": BEST_DEFAULT_MEMORY_BYTES,
                          "expected_descriptor_ids": artifact["candidate_registry"],
                          "expected_native_trial_ids": native_trial_ids(row["bytes"]),
                          "candidate_policy": "expanded-best-auto", "candidate_observability": "verbose selector diagnostics retained",
                          "host_runtime": {"path": rel(HOST_RUNTIME), "sha256": sha256(HOST_RUNTIME)}},
        "artifact": artifact, "initial_state": "fresh native encoder and fresh archive-only decoder; no cross-file history",
        "mechanism": "Complete archive cost includes candidate discovery, materialised trials, route/backend/representation metadata, framing and footer. Candidate and representation decisions are read from encoder diagnostics after exact restoration.",
        "budget": {"cpu": CPUS, "max_rss_bytes": RSS_BYTES, "max_temp_bytes": TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "native_catalog_qualification",
        "authorization": NATIVE_CATALOG_AUTHORIZATION,
        "expanded_best_authorization": "2026-10-02-user-expanded-rust-best-qualification",
        "longer_budget_justification": "The user authorized an expanded Rust BEST catalog qualification. Each complete frozen input is at most 100,000,000 bytes; the 7,200 second bound includes automatic candidate search and fresh archive-only decode under a 3 GB no-swap cgroup.",
        "promotion_criteria": "Record all outcomes. A ranked point requires explicit child exit-status records, a complete archive, fresh decoder restoration SHA-256 equal to the frozen input, and physical archive hash/length verification. A failed or resource-limited candidate remains visible and is never silently replaced.",
        "resource_accounting": "One serial cell leases CPUs 16,17,18,19. The shared WaveScheduler caps aggregate work at four physical cores, decimal 12 GB RAM and 4 GB temporary space without swap. No GPU is requested or used. This plan waits for the current Hutter reservation.",
        "encode_command": phase_command("{workdir}/encode.exit-status.txt", encode),
        "decode_command": phase_command("{workdir}/decode.exit-status.txt", decode),
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": [*(entry["path"] for entry in artifact["binaries"].values()), artifact["metadata"],
                        "benchmarks/cix_best_expanded_qualification.py", "benchmarks/cix_full_catalog.py",
                        "benchmarks/cix_dickens_best_compare.py", "benchmarks/hutter_bounded_runner.py",
                        "benchmarks/hutter_experiment_scheduler.py", rel(EXTERNAL_SOURCE), rel(PORTFOLIO_SOURCE),
                        registry["build_path"], rel(HOST_RUNTIME)],
        "qualification_registry": registry,
    }


def prepare(identity: str, artifacts: Path) -> Path:
    require_cpus()
    if not HOST_RUNTIME.is_file():
        raise RuntimeError("host runtime identity is required before freezing BEST qualification")
    area = AREA_ROOT / identity
    if area.exists():
        raise RuntimeError(f"immutable plan already exists: {area}")
    artifact = artifact_identity(artifacts)
    rows, provenance = inputs()
    area.mkdir(parents=True)
    (area / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    registry_path = ROOT / "docs/research/2026-10-02-rust-full-catalog" / (identity + "-best-expanded") / "input-registry.json"
    if registry_path.exists(): raise RuntimeError("immutable qualification registry already exists")
    write_json(registry_path, {"authorization": NATIVE_CATALOG_AUTHORIZATION,
        "expanded_best_authorization": "2026-10-02-user-expanded-rust-best-qualification",
                               "inputs": [{"label": row["label"], "path": str(row["path"].resolve()), "offset": 0,
                                                  "length": row["bytes"], "sha256": row["sha256"]} for row in rows], **provenance})
    registry = {"path": str(registry_path.resolve()), "build_path": rel(registry_path), "sha256": sha256(registry_path)}
    write_json(area / "input-census.json", {"cca_gate": [{**x, "path": str(x["path"].resolve())} for x in rows if x["stage"] == "gate"],
                                               "catalog_after_gate": [{**x, "path": str(x["path"].resolve())} for x in rows if x["stage"] == "catalog"]})
    manifests = area / "manifests"; manifests.mkdir()
    cells = []
    for row in rows:
        value = manifest(row, artifact, identity, registry)
        manifest_sha = hashlib.sha256(canonical(value)).hexdigest()
        cell_id = f"cix-expanded-best-{hashlib.sha256(identity.encode()).hexdigest()[:12]}-{manifest_sha[:24]}"
        path = manifests / f"{cell_id}.json"
        path.write_bytes(canonical(value) + b"\n")
        loaded, actual_sha = load_manifest(path)
        if actual_sha != manifest_sha:
            raise RuntimeError("manifest changed while freezing")
        cells.append({"cell_id": cell_id, "owner": "/root", "label": row["label"], "catalog_id": row["catalog_id"],
                      "stage": row["stage"], "profile": "best", "manifest_path": rel(path),
                      "output_dir": rel(area / "runs" / cell_id), "cpu": CPUS, "expected_manifest_sha256": actual_sha,
                      "expected_build_sha256": build_identity(loaded, ROOT),
                      "expected_descriptor_ids": loaded["configuration"]["expected_descriptor_ids"],
                      "expected_native_trial_ids": loaded["configuration"]["expected_native_trial_ids"],
                      "fresh_justification": "New expanded BEST implementation; previous source outcomes are not reused."})
    gate_cells = [cell for cell in cells if cell["stage"] == "gate"]
    catalog_cells = [cell for cell in cells if cell["stage"] == "catalog"]
    expected_gate = {"canterbury": 11, "calgary": 18, "artificial": 4}
    actual_gate = {name: sum(cell["label"].startswith(name + "/") for cell in gate_cells) for name in expected_gate}
    if (len(cells) != 50 or len({c["cell_id"] for c in cells}) != 50 or len(gate_cells) != 33
            or len(catalog_cells) != 17 or actual_gate != expected_gate
            or any(cell["label"].split("/", 1)[0] in expected_gate for cell in catalog_cells)):
        raise RuntimeError("expanded BEST plan must contain exactly fifty unique cells")
    write_json(area / "cells.json", {"schema": 1, "identity": identity, "artifact": artifact, "cells": cells,
                                      "counts": {"total": 50, "cca_gate": 33, "catalog_after_gate": 17}, "registry": registry})
    write_json(area / "plan.json", {"identity": identity, "status": "PREPARED_NOT_EXECUTED", "artifact": artifact,
                                     "counts": {"inputs": 50, "cells": 50, "cca_gate": 33, "catalog_after_gate": 17},
                                     "ordering": "All 33 CCA BEST cells must verify before catalog dispatch.",
                                     "resource_policy": {"ordinary_best_memory_bytes": BEST_DEFAULT_MEMORY_BYTES, "cell_rss_bytes": RSS_BYTES, "threads": 4, "aggregate": "4 cores / 12 GB RAM / 4 GB temp / no swap", "gpu": "not used"},
                                     "admission": "existing frozen-catalog admission; latest expanded BEST authorization is separately recorded",
                                     "exit_status": "Each child command records its own status because transient systemd ExecMainStatus can be stale after short failures; missing records are unqualified."})
    return area


def hutter_terminal() -> bool:
    states = list(HUTTER_ROOT.glob("*/queue-state.json"))
    # No state is not a reservation.  An active Hutter state prevents this plan
    # from claiming the shared four-core lane.
    terminal = {"TERMINAL", "COMPLETE", "FAILED_STATIC_BUILD", "FAILED_BEFORE_FULL_ENCODE"}
    return all(json.loads(path.read_text()).get("status") in terminal for path in states)


def actual_status(receipt_path: Path) -> dict:
    work = receipt_path.parent / "work"
    values = {}
    for phase in ("encode", "decode"):
        path = work / f"{phase}.exit-status.txt"
        try:
            values[phase] = int(path.read_text().strip())
        except (OSError, ValueError):
            values[phase] = None
    return values


def mandatory_gnu_time(path: Path) -> tuple[dict, bool]:
    value = gnu_time(path)
    return value, value.get("available") is True and REQUIRED_GNU_TIME.issubset(value)


def selector_ledger(receipt_path: Path, input_bytes: int, final_archive_bytes: int | None,
                    expected_descriptors: list[str], expected_native: list[str]) -> tuple[dict, bool]:
    log = selector_log(receipt_path)
    if not log.is_file():
        return {"path": rel(receipt_path.parent), "available": False, "typed_whole_archive": {"status": "missing_log"}}, False
    text = log.read_text(errors="replace")
    parsed = typed_whole_archive_ledger(text)
    records, malformed = packaging_records(text)
    outcomes = candidate_outcomes(parsed, records, expected_descriptors + expected_native)
    ledger = {"path": rel(log), "sha256": sha256(log), "available": True, "typed_whole_archive": parsed,
              "packaging_candidates": records, "candidate_outcomes": outcomes, "malformed_packaging_lines": malformed}
    required = input_bytes <= 128 * 1024 * 1024
    return ledger, (not required or coverage_valid(parsed, records, malformed, final_archive_bytes,
                                                   expected_descriptors, expected_native))


def packaging_records(text: str) -> tuple[dict[str, dict], list[str]]:
    records, malformed = {}, []
    pattern = re.compile(r"^cix:\s+packaging_candidate=(\S+)(?:\s+backend=(\S+)\s+version=(\S+))?\s+archive_bytes=(\d+)\s*$")
    for line in text.splitlines():
        if "packaging_candidate=" not in line: continue
        match = pattern.fullmatch(line)
        if match is None or match.group(1) in records:
            malformed.append(line); continue
        records[match.group(1)] = {"archive_bytes": int(match.group(4)), "backend": match.group(2), "version": match.group(3)}
    return records, malformed


def omitted_reason(omissions: str, candidate: str) -> str | None:
    # Candidate IDs are exact tokens emitted before their parenthesised reason.
    match = re.search(r"(?:^|,)" + re.escape(candidate) + r"\s*\(([^)]*\S[^)]*)\)(?=,|$)", omissions)
    return match.group(1) if match else None


def candidate_outcomes(summary: dict, records: dict[str, dict], expected: list[str]) -> dict[str, dict]:
    """Classify materialised-but-validation-omitted candidates without hiding them.

    The selector emits a physical archive size immediately after encoding. A
    later aggregate-memory/decode-validation admission can reject that same
    archive.  This is a measured, nonselectable outcome, not an encoder error.
    """
    omissions = summary.get("omissions") if isinstance(summary.get("omissions"), str) else ""
    result = {}
    for candidate in expected:
        record, reason = records.get(candidate), omitted_reason(omissions, candidate)
        if record is not None and reason is not None:
            result[candidate] = {"status": "measured_validation_omitted", "archive_bytes": record["archive_bytes"], "reason": reason}
        elif record is not None:
            result[candidate] = {"status": "measured_admitted", "archive_bytes": record["archive_bytes"]}
        elif reason is not None:
            result[candidate] = {"status": "omitted", "reason": reason}
        else:
            result[candidate] = {"status": "unaccounted"}
    return result


def coverage_valid(summary: dict, records: dict[str, dict], malformed: list[str], final_archive_bytes: int | None,
                   expected_external: list[str], expected_native: list[str]) -> bool:
    if summary.get("status") != "parsed" or malformed: return False
    try: summary_bytes = int(re.search(r"\barchive_bytes=(\d+)\b", summary["line"]).group(1))
    except (AttributeError, KeyError, TypeError, ValueError): return False
    expected = expected_external + expected_native
    omissions = summary.get("omissions")
    if not isinstance(omissions, str): return False
    for candidate in expected:
        record = records.get(candidate)
        omission = omitted_reason(omissions, candidate)
        if record is None and omission is None: return False
        if candidate in expected_external and record is not None and (not record["backend"] or not record["version"]): return False
    selected = summary.get("selected")
    legal = set(expected) | {"cixg2:raw-baseline"}
    if any(candidate not in legal for candidate in records): return False
    selected_record = records.get(selected)
    if (selected not in legal or selected_record is None or omitted_reason(omissions, selected) is not None
            or selected_record["archive_bytes"] != summary_bytes
            or final_archive_bytes is None or summary_bytes != final_archive_bytes): return False
    # `evaluated=1 omitted=none` proves only a raw fallback was considered.
    if summary.get("evaluated") == 1 and omissions == "none": return False
    return True


def collect(area: Path) -> dict:
    plan = json.loads((area / "cells.json").read_text()); scheduler = WaveScheduler(ROOT)
    rows = []
    for cell in plan["cells"]:
        terminal = scheduler._terminal_path(cell["cell_id"])
        row = {key: cell[key] for key in ("cell_id", "label", "catalog_id", "stage", "profile")}
        if not terminal.is_file(): rows.append({**row, "status": "PENDING"}); continue
        terminal_row = json.loads(terminal.read_text()); receipt_name = terminal_row.get("runner_result", {}).get("receipt")
        if not receipt_name or not Path(receipt_name).is_file(): rows.append({**row, "status": terminal_row.get("runner_status", "FAILED")}); continue
        receipt_path = Path(receipt_name); receipt = json.loads(receipt_path.read_text()); exits = actual_status(receipt_path)
        bound = scheduler._plan(cell)
        authentic = scheduler._verified_receipt(receipt_path, bound)
        work = receipt_path.parent / "work"; encode, encode_ok = mandatory_gnu_time(work / "encode.gnu-time.txt"); decode, decode_ok = mandatory_gnu_time(work / "decode.gnu-time.txt")
        ledger, ledger_ok = selector_ledger(receipt_path, receipt["identity"]["input"]["length"], receipt.get("archive_bytes"),
                                             cell["expected_descriptor_ids"], cell["expected_native_trial_ids"])
        runner_status = terminal_row.get("runner_status")
        runner_or_receipt_verified = runner_status in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} or receipt.get("status") == "VERIFIED_SCREENING"
        verified = authentic and runner_or_receipt_verified and receipt.get("verification", {}).get("matched") and exits == {"encode": 0, "decode": 0} and encode_ok and decode_ok and ledger_ok
        rows.append({**row, "status": "VERIFIED_SCREENING" if verified else "UNQUALIFIED", "runner_status": receipt.get("status"),
                     "child_exit_status": exits, "archive_bytes": receipt.get("archive_bytes"), "archive_sha256": receipt.get("archive_sha256"),
                     "verification": receipt.get("verification"), "receipt": rel(receipt_path),
                     "terminal_runner_status": runner_status, "encode": encode, "decode": decode, "selector_ledger": ledger,
                     "qualification_checks": {"gnu_time_encode_complete": encode_ok, "gnu_time_decode_complete": decode_ok,
                                                "typed_whole_archive_required": receipt["identity"]["input"]["length"] <= 128 * 1024 * 1024,
                                                "typed_whole_archive_parsed": ledger_ok}})
    counts = {}; [counts.__setitem__(x["status"], counts.get(x["status"], 0) + 1) for x in rows]
    report = {"collected_at": now(), "counts": counts, "rows": rows}
    write_json(area / "results.json", report); return report


def queue(area: Path) -> None:
    lock_path = area / "queue-controller.lock"
    with lock_path.open("a+") as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error: raise RuntimeError("expanded BEST queue is already controlled") from error
        plan = json.loads((area / "cells.json").read_text()); scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
        while not hutter_terminal():
            write_json(area / "queue-state.json", {"status": "WAITING_FOR_HUTTER", "updated_at": now()}); time.sleep(30)
        for stage in ("gate", "catalog"):
            if stage == "catalog":
                gate = [r for r in collect(area)["rows"] if r["stage"] == "gate"]
                if len(gate) != 33 or any(r["status"] != "VERIFIED_SCREENING" for r in gate): raise RuntimeError("CCA gate has not independently verified every input")
            for cell in (x for x in plan["cells"] if x["stage"] == stage):
                result = scheduler.run_wave([cell])[0]; report = collect(area)
                row = next(item for item in report["rows"] if item["cell_id"] == cell["cell_id"])
                result_verified = (result.get("runner_status") in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}
                                   or result.get("status") in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}
                                   or row.get("terminal_runner_status") in {"VERIFIED_SCREENING", "REUSED_VERIFIED"})
                if not result_verified or row["status"] != "VERIFIED_SCREENING":
                    write_json(area / "queue-state.json", {"status": "STOPPED_UNQUALIFIED", "cell_id": cell["cell_id"], "updated_at": now()}); return
        report = collect(area)
        if len(report["rows"]) != 50 or any(r["status"] != "VERIFIED_SCREENING" for r in report["rows"]): raise RuntimeError("cannot mark incomplete qualification COMPLETE")
        write_json(area / "queue-state.json", {"status": "COMPLETE", "updated_at": now()})


def phase(status_path: Path, command: list[str]) -> int:
    result = subprocess.run(command, check=False)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = status_path.with_suffix(status_path.suffix + ".tmp"); temporary.write_text(f"{result.returncode}\n"); temporary.replace(status_path)
    return result.returncode


def self_test() -> None:
    """Regression checks for evidence parsing; no codec or scheduler is run."""
    # A short or malformed ledger must never be upgraded to a BEST result.
    records, malformed = packaging_records("cix: packaging_candidate=broken archive_bytes=nope\n")
    assert not records and malformed
    summary = {"status": "parsed", "line": "cix: effort=best whole_archive=yes selected=cixg2:raw-baseline archive_bytes=9 candidates_evaluated=1 omitted=none",
               "selected": "cixg2:raw-baseline", "evaluated": 1, "omissions": "none"}
    records = {"cixg2:raw-baseline": {"archive_bytes": 9, "backend": None, "version": None}}
    assert not coverage_valid(summary, records, [], 9, [], [])
    summary["evaluated"], summary["omissions"] = 2, "missing (explicit reason)"
    assert not coverage_valid(summary, records, [], 8, [], [])
    summary["omissions"] = "external (validation memory reserve exhausted)"
    records["external"] = {"archive_bytes": 7, "backend": "zstd", "version": "test"}
    assert coverage_valid(summary, records, [], 9, ["external"], [])
    outcomes = candidate_outcomes(summary, records, ["external"])
    assert outcomes["external"]["status"] == "measured_validation_omitted"
    print(json.dumps({"self_test": "passed", "malformed_ledgers": "rejected"}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)
    prep = sub.add_parser("prepare"); prep.add_argument("--id", required=True); prep.add_argument("--artifacts", type=Path, required=True)
    queued = sub.add_parser("queue"); queued.add_argument("--id", required=True)
    listed = sub.add_parser("collect"); listed.add_argument("--id", required=True)
    sub.add_parser("self-test")
    wrapped = sub.add_parser("phase"); wrapped.add_argument("status", type=Path); wrapped.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.op == "phase": return phase(args.status, args.command)
    if args.op == "self-test": self_test(); return 0
    if not args.id.replace("-", "").isalnum(): parser.error("--id must contain only letters, digits and hyphens")
    area = AREA_ROOT / args.id
    if args.op == "prepare":
        created = prepare(args.id, args.artifacts); print(json.dumps({"prepared": rel(created), "execution": "not started", "cells": 50}, sort_keys=True)); return 0
    if not area.is_dir(): parser.error("unknown immutable plan")
    if args.op == "collect": print(json.dumps(collect(area)["counts"], sort_keys=True)); return 0
    queue(area); return 0


if __name__ == "__main__":
    raise SystemExit(main())
