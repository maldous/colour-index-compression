#!/usr/bin/env python3
"""Freeze and run the native CIX FAST/DEFAULT/BEST Squash-catalog plan.

Preparation copies already-built native artifacts, hashes cached inputs, and
writes immutable manifests.  It never builds, downloads, or benchmarks.  The
optional ``--run`` path is deliberately serial: every native cell owns the
same four physical CPUs as the normal four-worker CIX invocation.  All codec
execution remains inside the repository's bounded runner and WaveScheduler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_MANIFEST = Path("/home/user/src/cix-benchmark-site/dist/data/squash/manifest.json")
ACQUISITION_EXTENSION = ROOT / "docs/research/2026-10-02-rust-full-catalog/acquisition-extension.json"
HOST_RUNTIME = ROOT / "docs/research/2026-10-02-rust-full-catalog/host-runtime.json"
sys.path.insert(0, str(ROOT))

from benchmarks.cix_fast_opportunity import gnu_time
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

CPUS = [16, 17, 18, 19]
RSS_BYTES, TEMP_BYTES = 3_000_000_000, 1_000_000_000
PROFILES = {
    "fast": {"flags": ["--fast", "--verbose"], "wall_seconds": 1800},
    "default": {"flags": ["--verbose"], "wall_seconds": 1800},
    "best": {"flags": ["--best", "--verbose"], "wall_seconds": 7200},
}
MISSING = {"enwik8", "fireworks.jpeg", "geo.protodata", "paper-100k.pdf", "urls.10K"}
# This study is deliberately tied to the reviewed current native release.  A
# later release needs a new plan identity and a consciously updated adapter,
# rather than accidentally joining this evidence under a different executable.
CURRENT_SOURCE_REVISION = "d66739120c40fc409f2bf011b165389fc1062c2b"
CURRENT_CIX_SHA256 = "c1ce98c218207cd1b9b9b4aac3efa04ec133e9d716e3fe288d52c0dac910f65a"
CURRENT_UNCIX_SHA256 = "acd2764a2184f000f6147c29372e793765787b8bc4d5b3fdcf4522cd916753de"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    """Write a ledger atomically; prior completed ledgers are never edited in place."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def rel(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)) if ROOT in path.parents else str(path)


def require_cpus() -> None:
    missing = set(CPUS) - os.sched_getaffinity(0)
    if missing:
        raise RuntimeError(f"required CPUs unavailable: {sorted(missing)}")
    seen: set[tuple[int, int]] = set()
    for cpu in CPUS:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            core = (int((topology / "physical_package_id").read_text()), int((topology / "core_id").read_text()))
        except (OSError, ValueError):
            core = (0, cpu)
        if core in seen:
            raise RuntimeError("fixed reservation contains sibling logical CPUs")
        seen.add(core)


def input_row(path: Path, label: str, *, stage: str, catalog_id: str | None) -> dict:
    if not path.is_file() or path.stat().st_size < 1:
        raise RuntimeError(f"missing or empty cached input: {path}")
    return {"label": label, "path": path, "bytes": path.stat().st_size, "sha256": sha256(path),
            "stage": stage, "catalog_id": catalog_id}


def frozen_references() -> dict:
    """Load fixed identities; never replace them with a newly computed baseline."""
    cca_path = ROOT / "docs/research/2026-10-02-fast-opportunity/fast-lz-cca-v2/input-census.json"
    silesia_path = ROOT / "docs/research/2026-10-01-complete-benchmarks/silesia-v3/results.json"
    cutoff_path = ROOT / "docs/research/2026-09-30-generic-pipeline/acquisition-cutoff.json"
    cca, silesia, cutoff = (json.loads(path.read_text()) for path in (cca_path, silesia_path, cutoff_path))
    cca_members = {row["label"]: row for row in cca.get("inputs", [])}
    silesia_members = {row["name"]: row for row in silesia.get("members", [])}
    if len(cca_members) != 33 or len(silesia_members) != 12 or not cutoff.get("cutoff_utc"):
        raise RuntimeError("frozen CCA/Silesia/acquisition references are incomplete")
    return {"cca": cca_members, "silesia": silesia_members,
            "sources": {rel(cca_path): sha256(cca_path), rel(silesia_path): sha256(silesia_path),
                        rel(cutoff_path): sha256(cutoff_path)}, "acquisition_cutoff_utc": cutoff["cutoff_utc"]}


def require_reference_identity(row: dict, expected: dict, *, label: str) -> None:
    expected_bytes = expected.get("length", expected.get("bytes"))
    expected_hash = expected.get("sha256", expected.get("full_sha256"))
    if row["bytes"] != expected_bytes or row["sha256"] != expected_hash:
        raise RuntimeError(f"cached input differs from frozen verified identity: {label}")


def catalog_inputs(references: dict) -> tuple[list[dict], list[dict], dict]:
    if not SITE_MANIFEST.is_file():
        raise RuntimeError(f"catalog manifest missing: {SITE_MANIFEST}")
    catalog = json.loads(SITE_MANIFEST.read_text())
    datasets = catalog.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 28:
        raise RuntimeError("expected exactly 28 catalog datasets")
    if not ACQUISITION_EXTENSION.is_file():
        raise RuntimeError("new catalog inputs are not ready: acquisition-extension.json is required before freezing")
    extension = json.loads(ACQUISITION_EXTENSION.read_text())
    snappy = extension.get("snappy_testdata", {}).get("fixtures", [])
    enwik8 = extension.get("existing_enwik8", {})
    additions = {item.get("path", "").removeprefix("testdata/"): {"path": item.get("local_path"), "bytes": item.get("bytes"),
                                                                      "sha256": item.get("sha256"), "provenance": item}
                 for item in snappy if isinstance(item, dict)}
    additions["enwik8"] = {"path": enwik8.get("raw_path"), "bytes": enwik8.get("raw_bytes"),
                            "sha256": enwik8.get("raw_sha256"), "source_archive_sha256": enwik8.get("zip_sha256"),
                            "provenance": enwik8}
    if set(additions) != MISSING or any(not isinstance(value.get("path"), str) for value in additions.values()):
        raise RuntimeError("acquisition extension must declare exactly the five authorized catalog fixtures")
    cached, unavailable = [], []
    for dataset in datasets:
        name, expected_bytes = dataset.get("id"), dataset.get("original_bytes")
        if not isinstance(name, str) or not isinstance(expected_bytes, int):
            raise RuntimeError("catalog dataset identity is invalid")
        added = additions.get(name)
        if name in MISSING:
            path = Path(added.get("path", ""))
            if not path.is_absolute(): path = ROOT / path
            stratum = "enwik8" if name == "enwik8" else "snappy"
        else:
            canterbury = ROOT / "benchmark-work/canterbury" / name
            silesia = ROOT / "benchmark-work/silesia" / name
            path = canterbury if canterbury.is_file() else silesia
            stratum = "canterbury" if path.parent.name == "canterbury" else "silesia"
        if not path.is_file() or path.stat().st_size != expected_bytes:
            raise RuntimeError(f"catalog cached identity mismatch: {name}")
        stage = "gate" if stratum == "canterbury" else "catalog"
        row = input_row(path, f"{stratum}/{name}", stage=stage, catalog_id=name)
        if name in MISSING:
            if row["sha256"] != added.get("sha256") or row["bytes"] != added.get("bytes"):
                raise RuntimeError(f"authorized acquired fixture identity mismatch: {name}")
            if name == "enwik8" and not added.get("source_archive_sha256"):
                raise RuntimeError("enwik8 extension requires documented verified source archive hash")
        else:
            expected = references["cca"].get(row["label"]) if stratum == "canterbury" else references["silesia"].get(name)
            if expected is None:
                raise RuntimeError(f"cached catalog input is absent from its frozen identity registry: {row['label']}")
            require_reference_identity(row, expected, label=row["label"])
        cached.append(row)
    if len(cached) != 28 or unavailable or {row["catalog_id"] for row in cached} != {row["id"] for row in datasets}:
        raise RuntimeError("catalog cache census is inconsistent")
    return cached, unavailable, {"path": str(SITE_MANIFEST), "sha256": sha256(SITE_MANIFEST), "datasets": datasets,
                                  "acquisition_extension": {"path": rel(ACQUISITION_EXTENSION), "sha256": sha256(ACQUISITION_EXTENSION)}}


def cca_inputs(catalog: list[dict], references: dict) -> list[dict]:
    rows = {row["label"]: row for row in catalog if row["stage"] == "gate"}
    for stratum, expected in (("canterbury", 11), ("calgary", 18), ("artificial", 4)):
        directory = ROOT / "benchmark-work" / stratum
        files = sorted(path for path in directory.iterdir() if path.is_file()) if directory.is_dir() else []
        if len(files) != expected:
            raise RuntimeError(f"expected {expected} cached {stratum} gate files")
        for path in files:
            label = f"{stratum}/{path.name}"
            new = input_row(path, label, stage="gate", catalog_id=path.name if stratum == "canterbury" else None)
            if label not in references["cca"]:
                raise RuntimeError(f"gate input is absent from frozen CCA identity registry: {label}")
            require_reference_identity(new, references["cca"][label], label=label)
            old = rows.get(label)
            if old and (old["bytes"], old["sha256"], old["path"]) != (new["bytes"], new["sha256"], new["path"]):
                raise RuntimeError(f"catalog/gate source mismatch: {label}")
            rows[label] = new
    if len(rows) != 33:
        raise RuntimeError(f"expected 33 unique CCA gate inputs, got {len(rows)}")
    return [rows[label] for label in sorted(rows)]


def freeze_artifacts(origin: Path, identity: str) -> dict:
    """Copy every declared native artifact before writing any manifest."""
    origin = origin.resolve()
    if ROOT not in origin.parents:
        raise ValueError("artifact source must be inside the repository")
    metadata = origin / "native-release.json"
    value = json.loads(metadata.read_text()) if metadata.is_file() else None
    if not isinstance(value, dict) or not isinstance(value.get("binaries"), dict):
        raise ValueError("artifact source lacks native-release.json binaries")
    if value.get("source_revision") != CURRENT_SOURCE_REVISION:
        raise ValueError("full catalog is pinned to the reviewed d66739120c native release")
    if (value["binaries"].get("cix", {}).get("sha256") != CURRENT_CIX_SHA256
            or value["binaries"].get("uncix", {}).get("sha256") != CURRENT_UNCIX_SHA256):
        raise ValueError("full catalog is pinned to the reviewed c1ce native binary pair")
    for required in ("cix", "uncix"):
        binary, declared = origin / required, value["binaries"].get(required, {})
        if not binary.is_file() or not os.access(binary, os.X_OK) or sha256(binary) != declared.get("sha256"):
            raise ValueError(f"source artifact does not match metadata: {required}")
    destination = ROOT / "benchmark-work/cix-full-catalog" / identity / "final"
    if destination.exists():
        raise RuntimeError(f"frozen artifact directory exists: {destination}")
    destination.mkdir(parents=True)
    for name, declared in value["binaries"].items():
        source = origin / name
        if not source.is_file() or sha256(source) != declared.get("sha256"):
            raise ValueError(f"declared artifact unavailable or changed: {name}")
        shutil.copy2(source, destination / name)
        if sha256(destination / name) != declared["sha256"]:
            raise RuntimeError(f"artifact copy hash mismatch: {name}")
    shutil.copy2(metadata, destination / "native-release.json")
    if sha256(destination / "native-release.json") != sha256(metadata):
        raise RuntimeError("metadata copy hash mismatch")
    return {"origin": rel(origin), "directory": rel(destination), "metadata": rel(destination / "native-release.json"),
            "metadata_sha256": sha256(destination / "native-release.json"), "source_revision": value.get("source_revision"),
            "binaries": {name: {"path": rel(destination / name), "sha256": sha256(destination / name),
                                  "bytes": (destination / name).stat().st_size}
                         for name in value["binaries"]}}


def manifest(row: dict, profile: str, artifact: dict, identity: str, registry: dict) -> dict:
    policy = PROFILES[profile]
    whole_archive_eligible = profile == "best" and row["bytes"] <= 64 * 1024 * 1024
    return {
        "hypothesis": "Measure complete native CIX FAST, DEFAULT and BEST archives across cached catalog inputs after the complete CCA gate; preserve generic automatic selection and exact archive-only restoration.",
        "matched_control": "Each profile uses the same frozen native binaries, complete input bytes, public effort interface, four physical CPUs and fresh archive-only native decoder. No route, backend, format, block, history, memory or thread override is supplied.",
        "input": {"path": str(row["path"].resolve()), "offset": 0, "length": row["bytes"], "sha256": row["sha256"],
                  "label": row["label"], "catalog_id": row["catalog_id"]},
        "study_identity": identity,
        "configuration": {"profile": profile, "flags": policy["flags"], "automatic_selection": True,
                          "advanced_overrides": [], "artifact": artifact,
                          "native_search_budget_seconds": 900 if whole_archive_eligible else None,
                          "whole_archive_eligible_by_input_size": whole_archive_eligible,
                          "selector_observability": "verbose stderr retained; report selected whole package and omitted trials/budget skips",
                          "host_runtime_evidence": {"path": rel(HOST_RUNTIME), "sha256": sha256(HOST_RUNTIME)}},
        "initial_state": "fresh native encoder and archive-only native decoder; host cache and unrelated host load are uncontrolled",
        "mechanism": "Complete CIX archive bytes include framing, route metadata and integrity footer. Encoding time includes selector probes and discarded trials. DEFAULT per-block selection can vary with elapsed effort budgets.",
        "budget": {"cpu": CPUS, "max_rss_bytes": RSS_BYTES, "max_temp_bytes": TEMP_BYTES,
                   "wall_seconds": policy["wall_seconds"], "swap_bytes": 0},
        "stage": "native_catalog_qualification",
        "authorization": "2026-10-02-user-full-cix-catalog-benchmark",
        "longer_budget_justification": "User explicitly authorized the complete bounded native catalog study; each complete file is at most 100,000,000 bytes and the runner enforces its declared no-swap resource budget.",
        "promotion_criteria": "Fresh native archive-only decode must restore the declared SHA-256. Verification mismatch stops the plan. Budget failures are retained as non-ranked terminal evidence and do not silently substitute a setting.",
        "resource_accounting": "One serial cell leases CPUs 16,17,18,19; WaveScheduler aggregate cap remains four cores, decimal 12 GB RAM, 4 GB temporary space and no swap.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(ROOT / artifact["binaries"]["cix"]["path"]),
                           *policy["flags"], "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(ROOT / artifact["binaries"]["uncix"]["path"]),
                           "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": [*(entry["path"] for entry in artifact["binaries"].values()), artifact["metadata"],
                        "benchmarks/cix_full_catalog.py", "benchmarks/cix_fast_opportunity.py", "benchmarks/cix_dickens_best_compare.py",
                        "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py", registry["build_path"], rel(HOST_RUNTIME)],
        "qualification_registry": registry,
    }


def prepare(identity: str, origin: Path) -> Path:
    require_cpus()
    area = ROOT / "docs/research/2026-10-02-rust-full-catalog" / identity
    if area.exists():
        raise RuntimeError(f"immutable evidence area exists: {area}")
    if not HOST_RUNTIME.is_file():
        raise RuntimeError("host runtime identity evidence must be recorded before preparing the study")
    references = frozen_references()
    catalog, unavailable, catalog_meta = catalog_inputs(references)
    gate = cca_inputs(catalog, references)
    catalog_after_gate = [row for row in catalog if row["stage"] == "catalog"]
    registry_rows = [{"label": row["label"], "path": str(row["path"].resolve()), "offset": 0,
                      "length": row["bytes"], "sha256": row["sha256"]} for row in gate + catalog_after_gate]
    if len(registry_rows) != 50 or len({row["label"] for row in registry_rows}) != 50:
        raise RuntimeError("full catalog registry must contain 50 unique complete input identities")
    # Validate every authorized input and every frozen source identity before
    # materializing the immutable binary copy.
    artifact = freeze_artifacts(origin, identity)
    area.mkdir(parents=True)
    (area / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    registry_path = area / "input-registry.json"
    # The runner validates each input against this registry.  Its hash is also
    # part of every cell's build identity, so the external site manifest and
    # the authorized-acquisition evidence cannot later be swapped under an
    # already prepared study.
    write_json(registry_path, {
        "authorization": "2026-10-02-user-full-cix-catalog-benchmark",
        "inputs": registry_rows,
        "frozen_references": references["sources"],
        "catalog_manifest": {key: value for key, value in catalog_meta.items() if key != "datasets"},
    })
    registry = {"path": str(registry_path.resolve()), "build_path": rel(registry_path), "sha256": sha256(registry_path)}
    write_json(area / "catalog-availability.json", {"manifest": {key: value for key, value in catalog_meta.items() if key != "datasets"},
                                                       "cached": [{**row, "path": rel(row["path"])} for row in catalog], "missing": unavailable})
    write_json(area / "input-census.json", {"cca_gate": [{**row, "path": rel(row["path"])} for row in gate],
                                               "catalog_after_gate": [{**row, "path": rel(row["path"])} for row in catalog_after_gate]})
    manifests = area / "manifests"; manifests.mkdir()
    cells = []
    for row in gate + catalog_after_gate:
        for profile in PROFILES:
            frozen = manifest(row, profile, artifact, identity, registry)
            prewrite_sha = hashlib.sha256(canonical(frozen)).hexdigest()
            cell_id = f"cix-full-{hashlib.sha256(identity.encode()).hexdigest()[:12]}-{profile}-{prewrite_sha}"
            path = manifests / f"{cell_id}.json"
            if path.exists():
                raise RuntimeError(f"refuse to overwrite manifest: {path}")
            path.write_bytes(canonical(frozen) + b"\n")
            loaded, manifest_sha = load_manifest(path)
            if manifest_sha != prewrite_sha:
                raise RuntimeError("manifest canonical identity changed while freezing")
            cell = {"cell_id": cell_id, "owner": "/root", "label": row["label"], "catalog_id": row["catalog_id"],
                          "stage": row["stage"], "profile": profile, "manifest_path": rel(path),
                          "output_dir": rel(area / "runs" / cell_id), "cpu": CPUS,
                          "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build_identity(loaded, ROOT),
                          "fresh_justification": "Predeclared full-catalog cell; no retry or profile substitution."}
            validate_cell_binding(cell, loaded)
            cells.append(cell)
    validate_cell_set(cells, registry_rows)
    write_json(area / "cells.json", {"schema": 1, "artifact": artifact, "cells": cells, "unavailable_catalog_inputs": unavailable,
                                       "counts": {"total": len(cells), "gate": sum(c["stage"] == "gate" for c in cells),
                                                  "catalog_after_gate": sum(c["stage"] == "catalog" for c in cells), "fresh": len(cells)},
                                       "frozen_references": references["sources"], "acquisition_cutoff_utc": references["acquisition_cutoff_utc"],
                                       "qualification_registry": registry})
    write_json(area / "plan.json", {"identity": identity, "status": "PREPARED_NOT_EXECUTED", "artifact": artifact,
                                      "counts": {"catalog_datasets": 28, "available_catalog": 28, "missing_catalog": 0,
                                                 "cca_inputs": 33, "catalog_after_gate_inputs": 17, "cells": len(cells), "fresh_cells": len(cells)},
                                      "frozen_references": references["sources"], "acquisition_cutoff_utc": references["acquisition_cutoff_utc"],
                                      "qualification_registry": registry,
                                      "ordering": "all 99 CCA profile cells must be freshly verified before any Silesia dispatch"})
    return area


def validate_cell_set(cells: list[dict], registry_rows: list[dict]) -> None:
    """Reject incomplete plans before dispatch and avoid vacuous gate success."""
    labels = {row["label"] for row in registry_rows}
    if len(labels) != 50 or len(cells) != 150 or len({cell["cell_id"] for cell in cells}) != 150:
        raise RuntimeError("full catalog must freeze exactly 150 uniquely identified cells for 50 inputs")
    grouped: dict[str, list[dict]] = {}
    for cell in cells:
        grouped.setdefault(cell["label"], []).append(cell)
    if set(grouped) != labels or any({cell["profile"] for cell in group} != set(PROFILES) or len(group) != 3
                                     for group in grouped.values()):
        raise RuntimeError("each frozen input must have exactly FAST, DEFAULT and BEST cells")
    gate = [cell for cell in cells if cell["stage"] == "gate"]
    catalog = [cell for cell in cells if cell["stage"] == "catalog"]
    if len(gate) != 99 or len(catalog) != 51 or len({cell["label"] for cell in gate}) != 33 or len({cell["label"] for cell in catalog}) != 17:
        raise RuntimeError("full catalog must contain 33 CCA gate inputs and 17 post-gate catalog inputs")
    expected_gate = {"canterbury": 11, "calgary": 18, "artificial": 4}
    gate_by_stratum = {name: {cell["label"] for cell in gate if cell["label"].startswith(name + "/")}
                       for name in expected_gate}
    if ({name: len(values) for name, values in gate_by_stratum.items()} != expected_gate
            or any(cell["label"].split("/", 1)[0] in expected_gate for cell in catalog)):
        raise RuntimeError("CCA gate stage does not match its frozen Canterbury/Calgary/Artificial identities")


def validate_cell_binding(cell: dict, frozen: dict) -> None:
    """Bind mutable plan-row labels to the immutable manifest contents."""
    inp, configuration = frozen["input"], frozen["configuration"]
    label, profile, catalog_id = inp.get("label"), configuration.get("profile"), inp.get("catalog_id")
    if (cell.get("label"), cell.get("profile"), cell.get("catalog_id")) != (label, profile, catalog_id):
        raise RuntimeError(f"cell metadata does not match immutable manifest: {cell.get('cell_id')}")
    if not isinstance(label, str) or "/" not in label:
        raise RuntimeError("native catalog manifest has invalid input label")
    expected_stage = "gate" if label.split("/", 1)[0] in {"canterbury", "calgary", "artificial"} else "catalog"
    if cell.get("stage") != expected_stage:
        raise RuntimeError(f"cell stage does not match immutable CCA classification: {cell.get('cell_id')}")


def selector_summary(receipt_path: Path) -> dict:
    receipt = json.loads(receipt_path.read_text())
    stderr = receipt_path.parent / f"cix-bounded-{receipt['experiment_id'][:12]}-encode.stderr.log"
    if not stderr.is_file():
        return {"available": False}
    lines = stderr.read_text(errors="replace").splitlines()
    selected = [line for line in lines if re.search(r"(?i)(effort|selector|candidate|selected|route|backend|packag)", line)]
    # Keep both ends: selectors commonly report trials first and the selected
    # final package last.  The source log remains the authoritative complete
    # record, while this JSON stays bounded for dashboard ingestion.
    truncated = len(selected) > 200
    excerpt = (selected[:100] + [f"[... {len(selected) - 200} matching diagnostics omitted; see source log ...]"]
               + selected[-100:]) if truncated else selected
    return {"available": True, "path": rel(stderr), "sha256": sha256(stderr),
            "matching_line_count": len(selected), "parsed_lines": excerpt, "truncated": truncated}


def row_from_receipt(cell: dict, receipt_path: Path, status: str) -> dict:
    receipt = json.loads(receipt_path.read_text())
    work = receipt_path.parent / "work"
    row = {key: cell[key] for key in ("cell_id", "label", "catalog_id", "stage", "profile")}
    config, source = receipt["identity"]["configuration"], receipt["identity"]["input"]
    artifact = config["artifact"]
    encode, decode = gnu_time(work / "encode.gnu-time.txt"), gnu_time(work / "decode.gnu-time.txt")
    # GNU time reports user and system CPU separately.  Retain both values
    # and record their sum so later evidence never mistakes user CPU alone
    # for complete CPU time.
    for timing in (encode, decode):
        user, system = timing.get("user_seconds"), timing.get("system_seconds")
        if isinstance(user, (int, float)) and isinstance(system, (int, float)):
            timing["cpu_seconds"] = user + system
    return {**row, "dataset": cell["catalog_id"], "stratum": cell["label"].split("/", 1)[0],
            "status": status, "receipt": rel(receipt_path), "input_bytes": source["length"], "input_sha256": source["sha256"],
            "source_revision": artifact.get("source_revision"), "encoder_sha256": artifact["binaries"]["cix"]["sha256"],
            "decode_sha256": artifact["binaries"]["uncix"]["sha256"], "archive_bytes": receipt.get("archive_bytes"),
            "archive_sha256": receipt.get("archive_sha256"), "verification": receipt.get("verification"),
            "encode": encode, "decode": decode,
            "selector": selector_summary(receipt_path), "phases": receipt.get("phases")}


def collect(area: Path, cells: list[dict], receipt_cache: dict[str, tuple[str, bool]] | None = None,
            binding_cache: set[str] | None = None) -> dict:
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    receipt_cache = receipt_cache if receipt_cache is not None else {}
    binding_cache = binding_cache if binding_cache is not None else set()
    rows = []
    for cell in cells:
        if cell["cell_id"] not in binding_cache:
            frozen, _ = load_manifest(ROOT / cell["manifest_path"])
            validate_cell_binding(cell, frozen)
            binding_cache.add(cell["cell_id"])
        terminal = scheduler._terminal_path(cell["cell_id"])
        if not terminal.is_file():
            rows.append({**{key: cell[key] for key in ("cell_id", "label", "catalog_id", "stage", "profile")},
                         "dataset": cell["catalog_id"], "stratum": cell["label"].split("/", 1)[0], "status": "PENDING"})
            continue
        terminal_digest = sha256(terminal)
        terminal_row = json.loads(terminal.read_text())
        runner_result = terminal_row.get("runner_result", {})
        receipt = runner_result.get("receipt") if isinstance(runner_result, dict) else None
        status = terminal_row.get("runner_status", "UNKNOWN")
        receipt_path = Path(receipt) if isinstance(receipt, str) else None
        cached = receipt_cache.get(cell["cell_id"])
        if cached and cached[0] == terminal_digest:
            receipt_valid = cached[1]
        elif status in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}:
            # Do not infer validity merely from a global terminal filename.
            # The scheduler recomputes the manifest/build claim; its receipt
            # check rehashes source, archive, restored bytes and identity.
            plan = scheduler._plan(cell)
            receipt_valid = bool(receipt_path and receipt_path.is_file() and scheduler._verified_receipt(receipt_path, plan))
            receipt_cache[cell["cell_id"]] = (terminal_digest, receipt_valid)
        else:
            receipt_valid = False
        if receipt_valid:
            rows.append(row_from_receipt(cell, receipt_path, status))
        else:
            rows.append({**{key: cell[key] for key in ("cell_id", "label", "catalog_id", "stage", "profile")},
                         "dataset": cell["catalog_id"], "stratum": cell["label"].split("/", 1)[0],
                         "status": "UNQUALIFIED_TERMINAL" if status in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} else status,
                         "terminal": rel(terminal), "receipt_validated": False,
                         "runner_result": runner_result})
    status_counts: dict[str, int] = {}
    for row in rows: status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    gate_rows = [row for row in rows if row["stage"] == "gate"]
    report = {"schema": 1, "rows": rows, "counts": status_counts,
              "gate_verified": len(gate_rows) == 99 and all(row["status"] in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} for row in gate_rows),
              "note": "complete archive sizes are comparable within this frozen local plan; imported Squash CPU timings are not local timing controls"}
    write_json(area / "results.json", report)
    return report


def terminal_is_verification_mismatch(outcome: dict) -> bool:
    result = outcome.get("runner_result", {})
    verification = result.get("verification", {}) if isinstance(result, dict) else {}
    return bool(verification) and verification.get("matched") is False and not budget_limited(result)


def claimed_terminal_is_verification_mismatch(scheduler: WaveScheduler, cell: dict) -> bool:
    terminal = scheduler._terminal_path(cell["cell_id"])
    if not terminal.is_file():
        return False
    terminal_row = json.loads(terminal.read_text())
    result = terminal_row.get("runner_result", {})
    verification = result.get("verification", {}) if isinstance(result, dict) else {}
    return bool(verification) and verification.get("matched") is False and not budget_limited(result)


def budget_limited(result: object) -> bool:
    """A declared resource stop is recorded, then other cells may proceed.

    It is not evidence that a completed decoder produced wrong bytes, so it
    must not trigger the verification-mismatch stop path.
    """
    if not isinstance(result, dict):
        return False
    phases = result.get("phases", [])
    return any(isinstance(phase, dict) and phase.get("stop_reason") in {
        "wall_budget_exhausted", "memory_budget_exhausted", "temp_budget_exhausted"
    } for phase in phases)


def run(area: Path) -> int:
    plan = json.loads((area / "cells.json").read_text())
    cells, artifact = plan["cells"], plan["artifact"]
    registry = plan.get("qualification_registry", {})
    registry_path = Path(registry.get("path", "")).resolve() if isinstance(registry, dict) else ROOT
    if not isinstance(registry, dict) or not registry_path.is_file() or sha256(registry_path) != registry.get("sha256"):
        raise RuntimeError("frozen qualification registry drift")
    registry_value = json.loads(registry_path.read_text())
    registry_rows = registry_value.get("inputs") if isinstance(registry_value, dict) else None
    if not isinstance(registry_rows, list):
        raise RuntimeError("frozen qualification registry lacks input identities")
    validate_cell_set(cells, registry_rows)
    # Reject any drift in the frozen copied artifacts, manifests, or harness.
    for cell in cells:
        frozen, manifest_sha = load_manifest(ROOT / cell["manifest_path"])
        if manifest_sha != cell["expected_manifest_sha256"] or build_identity(frozen, ROOT) != cell["expected_build_sha256"]:
            raise RuntimeError(f"frozen plan drift: {cell['cell_id']}")
        validate_cell_binding(cell, frozen)
    if sha256(ROOT / artifact["binaries"]["cix"]["path"]) != artifact["binaries"]["cix"]["sha256"]:
        raise RuntimeError("frozen cix binary drift")
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    receipt_cache: dict[str, tuple[str, bool]] = {}
    binding_cache = {cell["cell_id"] for cell in cells}
    for stage in ("gate", "catalog"):
        if stage == "catalog":
            report = collect(area, cells, receipt_cache, binding_cache)
            if not report["gate_verified"]:
                write_json(area / "run-state.json", {"status": "HALTED_CCA_GATE", "reason": "not every CCA profile cell verified", "counts": report["counts"]})
                return 2
        for cell in (item for item in cells if item["stage"] == stage):
            # Always ask WaveScheduler to validate an existing claim/terminal
            # against this exact manifest and build identity. It returns a
            # rehashed REUSED_VERIFIED terminal only for this frozen study.
            outcome = scheduler.run_wave([cell])[0]
            collect(area, cells, receipt_cache, binding_cache)
            if terminal_is_verification_mismatch(outcome) or claimed_terminal_is_verification_mismatch(scheduler, cell):
                write_json(area / "run-state.json", {"status": "STOPPED_VERIFICATION_MISMATCH", "cell_id": cell["cell_id"], "stage": stage})
                return 3
            # Other terminal failures, including declared budget exhaustion, remain recorded and do not erase later cells.
    report = collect(area, cells, receipt_cache, binding_cache)
    write_json(area / "run-state.json", {"status": "COMPLETE" if report["gate_verified"] else "HALTED_CCA_GATE", "counts": report["counts"]})
    return 0 if report["gate_verified"] else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="new immutable catalog-plan identity")
    parser.add_argument("--artifacts", type=Path, required=True, help="current native artifact directory to freeze")
    parser.add_argument("--prepare", action="store_true", help="copy artifacts and write immutable plan; no codec execution")
    parser.add_argument("--run", action="store_true", help="serially dispatch the frozen plan through WaveScheduler")
    args = parser.parse_args()
    if not args.id.replace("-", "").isalnum():
        parser.error("--id must use letters, numbers and hyphens")
    if not args.prepare and not args.run:
        parser.error("choose --prepare and/or --run")
    area = ROOT / "docs/research/2026-10-02-rust-full-catalog" / args.id
    if args.prepare:
        area = prepare(args.id, ROOT / args.artifacts)
        print(json.dumps({"prepared": rel(area), "execution": "not started"}, sort_keys=True))
    if args.run:
        if not area.is_dir():
            raise RuntimeError("--run requires an existing frozen area; run --prepare first")
        return run(area)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
