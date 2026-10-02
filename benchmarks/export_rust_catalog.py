#!/usr/bin/env python3
"""Export the native CIX full-catalog study without leaking private evidence.

This is deliberately an exporter, not a benchmark runner.  It reads the
immutable study plan and scheduler terminals, revalidates every published
receipt through the scheduler's own binding and artifact checks, then writes a
small public JSON/CSV pair.  Failed, pending, and budget-limited cells remain
visible as non-ranked statuses; this tool never substitutes an older result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.hutter_experiment_scheduler import WaveScheduler

SOURCE_REVISION = "d66739120c40fc409f2bf011b165389fc1062c2b"
CIX_SHA256 = "c1ce98c218207cd1b9b9b4aac3efa04ec133e9d716e3fe288d52c0dac910f65a"
UNCIX_SHA256 = "acd2764a2184f000f6147c29372e793765787b8bc4d5b3fdcf4522cd916753de"
PROFILES = ("fast", "default", "best")
PUBLIC_STATUS = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
KEY_VALUE = re.compile(r"([a-z][a-z0-9_]*)=([^\s]+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    temporary.replace(path)


def safe_status(value: object) -> str:
    text = str(value or "UNKNOWN").upper()
    return text if PUBLIC_STATUS.fullmatch(text) else "UNKNOWN"


def require_file(path: Path) -> Path:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"required file is absent: {path}")
    return path


def read_json(path: Path) -> dict:
    value = json.loads(require_file(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def exact_artifact(plan: dict) -> dict:
    configuration = plan["manifest"]["configuration"]
    artifact = configuration.get("artifact")
    binaries = artifact.get("binaries") if isinstance(artifact, dict) else None
    if (not isinstance(binaries, dict) or artifact.get("source_revision") != SOURCE_REVISION
            or binaries.get("cix", {}).get("sha256") != CIX_SHA256
            or binaries.get("uncix", {}).get("sha256") != UNCIX_SHA256):
        raise ValueError(f"cell is not bound to the reviewed d667 native binary pair: {plan['cell_id']}")
    return artifact


def gnu_time(receipt: dict, phase_name: str) -> dict | None:
    """Extract numeric timing and RSS values without publishing private paths."""
    artifacts = receipt.get("artifacts")
    archive = Path(artifacts.get("archive", "")) if isinstance(artifacts, dict) else None
    time_name = "encode.gnu-time.txt" if phase_name == "-encode" else "decode.gnu-time.txt"
    parsed: dict[str, int | float] = {}
    if archive is not None and archive.is_file():
        time_file = archive.parent / time_name
        if time_file.is_file():
            for line in time_file.read_text(errors="replace").splitlines():
                if line.startswith("\tUser time (seconds):"):
                    parsed["user_seconds"] = float(line.rsplit(":", 1)[1].strip())
                elif line.startswith("\tSystem time (seconds):"):
                    parsed["system_seconds"] = float(line.rsplit(":", 1)[1].strip())
                elif line.startswith("\tMaximum resident set size (kbytes):"):
                    parsed["max_rss_kib"] = int(line.rsplit(":", 1)[1].strip())
                elif line.startswith("\tElapsed (wall clock) time"):
                    values = [float(value) for value in line.split("):", 1)[1].strip().split(":")]
                    parsed["wall_seconds"] = sum(value * 60 ** index for index, value in enumerate(reversed(values)))
    for phase in receipt.get("phases", []):
        if not isinstance(phase, dict) or phase.get("phase", "").endswith(phase_name) is False:
            continue
        user, system = parsed.get("user_seconds"), parsed.get("system_seconds")
        return {
            "wall_seconds": parsed.get("wall_seconds", phase.get("elapsed_seconds")),
            "cpu_seconds": (user + system if isinstance(user, (int, float)) and isinstance(system, (int, float))
                            else phase.get("cpu_usage_seconds")),
            "max_rss_kib": parsed.get("max_rss_kib"),
            "sampled_cgroup_memory_high_water_bytes": phase.get("sampled_cgroup_memory_high_water_bytes"),
            "peak_temp_bytes": phase.get("peak_temp_bytes"),
            "memory_note": "sampled cgroup high-water lower bound; not a true process peak RSS",
        }
    return None


def selector_summary(receipt_path: Path, archive: Path) -> dict:
    """Return a compact, path-free selection summary plus actual archive magic."""
    receipt = read_json(receipt_path)
    experiment_id = receipt.get("experiment_id")
    candidates = list(receipt_path.parent.glob("*encode.stderr.log"))
    if not isinstance(experiment_id, str):
        candidates = []
    else:
        expected = receipt_path.parent / f"cix-bounded-{experiment_id[:12]}-encode.stderr.log"
        candidates = [expected] if expected.is_file() else []
    safe_keys = {
        "effort", "format", "parallelism", "workers", "queue_capacity", "peak_outstanding",
        "reserved_buffers", "peak_scratch_reserved", "source_bytes", "blocks", "candidates",
        "memory_skips", "budget_skips", "analyse_seconds", "candidate_seconds", "search_seconds",
        "archive_bytes", "selected", "candidates_evaluated", "native_search_budget_seconds",
        "whole_archive", "backend", "version", "packaging_candidate", "omitted",
    }
    extracted: dict[str, str] = {}
    if candidates:
        for line in candidates[0].read_text(errors="replace").splitlines():
            if not line.startswith("cix:"):
                continue
            for key, value in KEY_VALUE.findall(line):
                if key in safe_keys and len(value) <= 256 and "/" not in value and "\\" not in value:
                    extracted[key] = value
    with archive.open("rb") as stream:
        magic = stream.read(16).hex()
    return {"archive_magic_hex": magic, "selector": extracted or None}


def terminal_record(scheduler: WaveScheduler, cell: dict, plan: dict) -> tuple[str, Path | None]:
    terminal = scheduler._terminal_path(cell["cell_id"])
    if not terminal.is_file():
        return "PENDING", None
    try:
        row = read_json(terminal)
    except (OSError, ValueError, json.JSONDecodeError):
        return "UNREADABLE_TERMINAL", None
    status = safe_status(row.get("runner_status"))
    result = row.get("runner_result")
    receipt_value = result.get("receipt") if isinstance(result, dict) else None
    receipt = Path(receipt_value) if isinstance(receipt_value, str) else None
    if status in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}:
        if receipt is not None and receipt.is_file() and scheduler._verified_receipt(receipt, plan):
            return status, receipt
        return "UNQUALIFIED_TERMINAL", None
    return status, None


def nonranked_row(cell: dict, status: str) -> dict:
    return {
        "dataset": cell["catalog_id"], "profile": cell["profile"], "status": status,
        "ranked": False, "input_bytes": None, "input_sha256": None,
        "archive_bytes": None, "archive_sha256": None, "encode": None, "decode": None,
        "selection": None,
    }


def verified_row(cell: dict, plan: dict, receipt_path: Path, status: str) -> dict:
    receipt = read_json(receipt_path)
    artifact = exact_artifact(plan)
    identity = receipt.get("identity")
    if not isinstance(identity, dict) or identity.get("manifest_sha256") != plan["manifest_sha256"]:
        raise ValueError(f"receipt identity changed after scheduler verification: {cell['cell_id']}")
    source = identity.get("input")
    artifacts = receipt.get("artifacts")
    if not isinstance(source, dict) or not isinstance(artifacts, dict):
        raise ValueError(f"receipt lacks source/artifact binding: {cell['cell_id']}")
    archive = Path(artifacts.get("archive", ""))
    if not archive.is_file():
        raise ValueError(f"verified scheduler receipt lost its archive: {cell['cell_id']}")
    selection = selector_summary(receipt_path, archive)
    profile = cell["profile"]
    eligible = profile == "best" and int(source["length"]) <= 64 * 1024 * 1024
    if profile == "best":
        search = {"whole_archive_native_search_bound_seconds": 900 if eligible else None,
                  "whole_archive_search_eligible_by_input_size": eligible,
                  "exclusion": None if eligible else "input exceeds 64 MiB; ordinary BEST used the bounded CIXG2/block path"}
    else:
        search = {"whole_archive_native_search_bound_seconds": None,
                  "whole_archive_search_eligible_by_input_size": False,
                  "exclusion": "not a BEST profile"}
    return {
        "dataset": cell["catalog_id"], "profile": profile, "status": status, "ranked": True,
        "input_bytes": int(source["length"]), "input_sha256": source["sha256"],
        "archive_bytes": int(receipt["archive_bytes"]), "archive_sha256": receipt["archive_sha256"],
        "verification": "fresh native archive-only decode SHA-256 matched input",
        "encode": gnu_time(receipt, "-encode"), "decode": gnu_time(receipt, "-decode"),
        "selection": selection, "search": search,
        "current_code": {"source_revision": artifact["source_revision"],
                         "cix_sha256": artifact["binaries"]["cix"]["sha256"],
                         "uncix_sha256": artifact["binaries"]["uncix"]["sha256"],
                         "native_release_metadata_sha256": artifact["metadata_sha256"]},
    }


def catalog_provenance(catalog_manifest: Path, acquisition: Path, registry: Path) -> dict:
    catalog = read_json(catalog_manifest)
    datasets = catalog.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 28:
        raise ValueError("catalog manifest must contain exactly 28 datasets")
    sources = []
    for dataset in datasets:
        if not isinstance(dataset, dict) or not isinstance(dataset.get("id"), str):
            raise ValueError("catalog dataset lacks an id")
        url = dataset.get("source_url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError(f"catalog dataset lacks a public source URL: {dataset.get('id')}")
        sources.append({"dataset": dataset["id"], "source": dataset.get("source"), "source_url": url,
                        "original_bytes": dataset.get("original_bytes")})
    return {
        "catalog_manifest_sha256": sha256(catalog_manifest),
        "catalog_upstream_commit": catalog.get("upstream_commit"),
        "catalog_upstream_commit_url": catalog.get("upstream_commit_url"),
        "acquisition_extension_sha256": sha256(acquisition),
        "frozen_input_registry_sha256": sha256(registry),
        "dataset_sources": sorted(sources, key=lambda row: row["dataset"]),
    }


def export(study: Path, output: Path, catalog_manifest: Path, *, force: bool) -> dict:
    study = study.resolve()
    if ROOT / "docs/research/2026-10-02-rust-full-catalog" not in study.parents:
        raise ValueError("study must be inside the native full-catalog evidence area")
    cells_doc = read_json(study / "cells.json")
    results_doc = read_json(study / "results.json")
    registry_spec = cells_doc.get("qualification_registry")
    if not isinstance(registry_spec, dict):
        raise ValueError("study lacks qualification registry")
    registry = require_file(Path(registry_spec.get("path", "")))
    if sha256(registry) != registry_spec.get("sha256"):
        raise ValueError("frozen qualification registry drift")
    acquisition = require_file(ROOT / "docs/research/2026-10-02-rust-full-catalog/acquisition-extension.json")
    cells = cells_doc.get("cells")
    if not isinstance(cells, list) or len(cells) != 150:
        raise ValueError("study must preserve all 150 frozen gate and catalog cells")
    result_rows = results_doc.get("rows")
    if not isinstance(result_rows, list) or len(result_rows) != 150:
        raise ValueError("results ledger must report every frozen cell before public export")
    results_by_cell = {row.get("cell_id"): row for row in result_rows if isinstance(row, dict)}
    if set(results_by_cell) != {cell.get("cell_id") for cell in cells}:
        raise ValueError("results ledger does not bind exactly to the frozen cell set")
    catalog_cells = [cell for cell in cells if isinstance(cell, dict) and cell.get("catalog_id") is not None]
    expected = {(dataset, profile) for dataset in {cell["catalog_id"] for cell in catalog_cells} for profile in PROFILES}
    actual = {(cell.get("catalog_id"), cell.get("profile")) for cell in catalog_cells}
    if len(catalog_cells) != 84 or len(expected) != 84 or actual != expected:
        raise ValueError("study must contain exactly 28 datasets × FAST/DEFAULT/BEST")
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    records = []
    for cell in sorted(catalog_cells, key=lambda row: (row["catalog_id"], PROFILES.index(row["profile"]))):
        plan = scheduler._plan(cell)  # immutable manifest and declared build hashes
        exact_artifact(plan)
        status, receipt = terminal_record(scheduler, cell, plan)  # receipt rehashes archive/restored
        reported = safe_status(results_by_cell[cell["cell_id"]].get("status"))
        equivalent_verified = {status, reported} <= {"VERIFIED_SCREENING", "REUSED_VERIFIED"}
        if status != reported and not equivalent_verified:
            raise ValueError(f"results ledger is stale for {cell['cell_id']}; collect before exporting")
        records.append(verified_row(cell, plan, receipt, status) if receipt else nonranked_row(cell, status))
    if len(records) != 84:
        raise AssertionError("catalog export lost cells")
    verified = sum(row["ranked"] for row in records)
    document = {
        "schema": "cix-native-full-catalog-public-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "study_identity": study.name,
        "scope": "Native Rust CIX FAST, DEFAULT and BEST on one frozen local run per catalog cell.",
        "measurement_note": "Compressed bytes are complete archives. Local wall/CPU measurements are single-run evidence and must not be ranked against imported Squash CPU timings.",
        "qualification_note": "Only rows revalidated from the immutable scheduler plan and a fresh archive/restored SHA-256 receipt are ranked. Other statuses are retained but non-ranked.",
        "coverage": {"datasets": 28, "profiles": list(PROFILES), "cells": 84,
                     "verified_cells": verified, "nonranked_cells": 84 - verified},
        "provenance": {**catalog_provenance(require_file(catalog_manifest), acquisition, registry),
                       "results_ledger_sha256": sha256(study / "results.json")},
        "records": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output / "rust-full-catalog.json", output / "rust-full-catalog.csv"
    if not force and any(path.exists() for path in (json_path, csv_path)):
        raise FileExistsError("public export already exists; use --force only after reviewing the new frozen state")
    write_json(json_path, document)
    fields = ["dataset", "profile", "status", "ranked", "input_bytes", "input_sha256", "archive_bytes", "archive_sha256",
              "encode_wall_seconds", "encode_cpu_seconds", "encode_max_rss_kib", "encode_sampled_cgroup_memory_high_water_bytes",
              "decode_wall_seconds", "decode_cpu_seconds", "decode_max_rss_kib", "decode_sampled_cgroup_memory_high_water_bytes",
              "archive_magic_hex", "source_revision", "cix_sha256", "uncix_sha256", "whole_archive_native_search_bound_seconds",
              "whole_archive_search_eligible_by_input_size", "whole_archive_search_exclusion"]
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in records:
            selection, code, search = row.get("selection") or {}, row.get("current_code") or {}, row.get("search") or {}
            encode, decode = row.get("encode") or {}, row.get("decode") or {}
            writer.writerow({
                "dataset": row["dataset"], "profile": row["profile"], "status": row["status"], "ranked": row["ranked"],
                "input_bytes": row["input_bytes"], "input_sha256": row["input_sha256"],
                "archive_bytes": row["archive_bytes"], "archive_sha256": row["archive_sha256"],
                "encode_wall_seconds": encode.get("wall_seconds"), "encode_cpu_seconds": encode.get("cpu_seconds"),
                "encode_max_rss_kib": encode.get("max_rss_kib"),
                "encode_sampled_cgroup_memory_high_water_bytes": encode.get("sampled_cgroup_memory_high_water_bytes"),
                "decode_wall_seconds": decode.get("wall_seconds"), "decode_cpu_seconds": decode.get("cpu_seconds"),
                "decode_max_rss_kib": decode.get("max_rss_kib"),
                "decode_sampled_cgroup_memory_high_water_bytes": decode.get("sampled_cgroup_memory_high_water_bytes"),
                "archive_magic_hex": selection.get("archive_magic_hex"), "source_revision": code.get("source_revision"),
                "cix_sha256": code.get("cix_sha256"), "uncix_sha256": code.get("uncix_sha256"),
                "whole_archive_native_search_bound_seconds": search.get("whole_archive_native_search_bound_seconds"),
                "whole_archive_search_eligible_by_input_size": search.get("whole_archive_search_eligible_by_input_size"),
                "whole_archive_search_exclusion": search.get("exclusion"),
            })
    return {"json": str(json_path), "csv": str(csv_path), "verified_cells": verified, "cells": 84}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--catalog-manifest", type=Path,
                        default=ROOT.parent / "cix-benchmark-site/dist/data/squash/manifest.json")
    parser.add_argument("--force", action="store_true", help="replace a prior public export after review")
    args = parser.parse_args()
    result = export(args.study_dir, args.output_dir, args.catalog_manifest, force=args.force)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
