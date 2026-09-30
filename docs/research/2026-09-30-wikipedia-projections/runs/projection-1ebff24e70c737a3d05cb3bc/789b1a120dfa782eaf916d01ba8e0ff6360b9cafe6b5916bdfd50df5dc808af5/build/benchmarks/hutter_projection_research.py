#!/usr/bin/env python3
"""Declarative bounded research cells for self-contained CIX projections.

This module prepares and reports projection experiments only.  It never makes a
PAQ fallback candidate: PAQ is retained solely as a separately identified,
rehash-validated original-byte size control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from benchmarks.hutter_bounded_runner import build_identity, load_manifest
from benchmarks.hutter_experiment_registry import Registry, canonical, digest
from benchmarks.hutter_experiment_scheduler import WaveScheduler
from benchmarks.hutter_matrix_evidence import parse_complete_archive

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/research/2026-09-30-wikipedia-projections")
REGISTRY_REL = Path("docs/research/2026-09-30-wikipedia-matrix/registry")
RECIPES = ("p1", "p2", "p3")
CONTROL_KEYS = ("paq_binary_sha256", "paq_options", "source_filename")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def immutable(path: Path, value: dict) -> None:
    data = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"immutable record differs: {path}")
        return
    with path.open("xb") as out:
        out.write(data)
    path.chmod(0o444)


def _source(source: dict) -> dict:
    if not isinstance(source, dict) or set(("path", "offset", "length", "sha256", "dataset_sha256")) - set(source):
        raise ValueError("source requires canonical dataset_sha256 plus path, offset, length, sha256")
    path = Path(source["path"]).resolve()
    offset, length = source["offset"], source["length"]
    if not path.is_file() or not isinstance(offset, int) or offset < 0 or not isinstance(length, int) or length <= 0:
        raise ValueError("invalid source range")
    if offset + length > path.stat().st_size:
        raise ValueError("source range exceeds input")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        stream.seek(offset); remaining = length
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            if not block: raise ValueError("source range truncated")
            h.update(block); remaining -= len(block)
    if h.hexdigest() != source["sha256"]:
        raise ValueError("source range hash mismatch")
    if not isinstance(source["dataset_sha256"], str) or len(source["dataset_sha256"]) != 64:
        raise ValueError("source dataset_sha256 is invalid")
    return {"path": str(path), "offset": offset, "length": length, "sha256": source["sha256"], "dataset_sha256": source["dataset_sha256"]}


def _freeze_control(freeze: dict) -> dict:
    """Find the frozen raw-PAQ comparison identifiers without guessing names."""
    def walk(value):
        if isinstance(value, dict):
            if value.get("mode") == "original" and all(isinstance(value.get(k), str) and value[k] for k in CONTROL_KEYS):
                return value
            for child in value.values():
                found = walk(child)
                if found: return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found: return found
        return None
    control = walk(freeze)
    if control is None:
        raise ValueError("freeze.json must declare mode=original PAQ binary/options/basename identifiers")
    return {"mode": "original", **{key: control[key] for key in CONTROL_KEYS}}


def _control(receipt_path: Path, source: dict, frozen: dict) -> dict:
    try:
        row = json.loads(receipt_path.read_text())
        identity, verification, artifacts = row["identity"], row["verification"], row["artifacts"]
        original = identity["input"]; config = identity["configuration"]
        archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise ValueError("invalid PAQ control receipt") from error
    if row.get("status") != "VERIFIED_SCREENING" or not verification.get("matched"):
        raise ValueError("PAQ control must be VERIFIED_SCREENING")
    if any(original.get(key) != source[key] for key in ("path", "offset", "length", "sha256")):
        raise ValueError("PAQ control input does not exactly match projection source")
    if verification.get("source_sha256") != source["sha256"] or verification.get("restored_sha256") != source["sha256"]:
        raise ValueError("PAQ control verification does not match source")
    if not archive.is_file() or not restored.is_file() or archive.stat().st_size != row.get("archive_bytes"):
        raise ValueError("PAQ control artifacts are incomplete")
    if sha(archive) != row.get("archive_sha256") or restored.stat().st_size != source["length"] or sha(restored) != source["sha256"]:
        raise ValueError("PAQ control rehash failed")
    try:
        physical = parse_complete_archive(archive, row["archive_sha256"], row["archive_bytes"])
    except ValueError as error:
        raise ValueError("PAQ control is not a complete raw PAQ outer archive") from error
    if physical["outer_mode"] != 0 or physical["original_bytes"] != source["length"] or physical["transformed_bytes"] != source["length"]:
        raise ValueError("PAQ control is not an original-byte mode-0 archive")
    if config.get("mode") != "original" or any(config.get(key) != frozen[key] for key in CONTROL_KEYS):
        raise ValueError("PAQ control is not the frozen original-byte PAQ configuration")
    initial = identity.get("initial_state")
    if not isinstance(initial, str) or "empty" not in initial.lower():
        raise ValueError("PAQ control lacks explicit empty-state context")
    return {"receipt": str(receipt_path.resolve()), "archive_bytes": row["archive_bytes"], "archive_sha256": row["archive_sha256"], "archive_physical": physical,
            "identifiers": {key: config[key] for key in CONTROL_KEYS}, "initial_state": initial,
            "verification": "rehash-validated original-byte PAQ bounded receipt"}


def _build_paths(root: Path, area: Path) -> list[str]:
    cix = sorted(str(path.relative_to(root)) for path in (root / "cix").rglob("*.py"))
    required = ["benchmarks/volume_image_codec.py", "benchmarks/hutter_projection_probe.py",
                "benchmarks/hutter_wikipedia_projections.py", "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_projection_research.py",
                str((area / "runtime-manifest.json").relative_to(root)), str((area / "freeze.json").relative_to(root))]
    paths = cix + required
    if any(not (root / name).is_file() for name in paths):
        missing = [name for name in paths if not (root / name).is_file()]
        raise ValueError("projection freeze incomplete: " + ", ".join(missing))
    return paths


def prepare(source: dict, recipe: str, cpu: int, control_receipt: str | Path | None = None,
            stratum: str = "fixed_development", *, root: Path = ROOT) -> dict:
    """Freeze one not-yet-run projection cell and record its registry identity."""
    if recipe not in RECIPES or cpu not in (4, 6):
        raise ValueError("recipe must be p1/p2/p3 and cpu must be 4 or 6")
    root = root.resolve(); area = root / REL; area.mkdir(parents=True, exist_ok=True)
    source = _source(source)
    freeze_path = area / "freeze.json"
    try:
        freeze = json.loads(freeze_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("projection freeze.json is required and must be valid") from error
    allowed = set(freeze.get("allowed_dataset_sha256", [])) | {freeze.get("dataset_sha256")}
    if source["dataset_sha256"] not in allowed:
        raise ValueError("declared source dataset_sha256 is not allowlisted by freeze")
    for name, expected in freeze["sources_sha256"].items():
        if sha(root / name) != expected:
            raise ValueError(f"frozen projection pipeline changed: {name}")
    if sha(area / "runtime-manifest.json") != freeze["runtime_manifest_sha256"]:
        raise ValueError("frozen runtime manifest changed")
    frozen_control = _freeze_control(freeze)
    control = _control(Path(control_receipt), source, frozen_control) if control_receipt else None
    build_paths = _build_paths(root, area)
    registry = Registry(root / REGISTRY_REL)
    input_id = registry.register_input(source["dataset_sha256"], source["offset"], source["length"], source["sha256"])
    registry.record_exposure(input_id, {"kind": "development", "evidence_refs": [str(REL / "freeze.json")],
                                        "userdirective_refs": ["fixed projection research wave"]})
    config = {"backend": "CIX projection probe only; PAQ is not invoked", "recipe": recipe,
              "wrapper_magic": "CIXPROJ1", "wrapper_header_bytes": 29, "wrapper_fixed_metadata_bytes": 37,
              "inner_format": "CIXV1 mode5/JXL9,width256,z1,bytevalueswidenuint16,pad0", "paq_fallback": "FORBIDDEN",
              **(control["identifiers"] if control else {})}
    manifest = {"hypothesis": f"Self-contained projection {recipe} changes CIX structural regularity; all wrapper and inner bytes are charged.",
                "matched_control": "Rehash-validated original-byte PAQ receipt" if control else "NO_CONTROL_DECLARED",
                "mechanism": f"CIXPROJ1/{recipe} only; no PAQ fallback", "promotion_criteria": "Physical archive plus independent archive-only exact decode. This prepared cell is not a qualification or gain claim.",
                "input": source, "configuration": config, "initial_state": "empty; no external state, model, dictionary or PAQ fallback",
                "budget": {"cpu": cpu, "wall_seconds": 300, "max_rss_bytes": 3_000_000_000, "max_temp_bytes": 1_000_000_000},
                "artifacts": {"archive": "{workdir}/candidate.cixproj", "restored": "{workdir}/restored.bin"}, "build_paths": build_paths,
                "encode_command": ["/usr/bin/env", "OMP_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "MKL_NUM_THREADS=1", sys.executable,
                    str(root / "benchmarks/hutter_projection_probe.py"), "encode", "{source}", "{workdir}/candidate.cixproj", "--recipe", recipe,
                    "--runtime-manifest", str(area / "runtime-manifest.json")],
                "decode_command": ["/usr/bin/env", "OMP_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "MKL_NUM_THREADS=1", sys.executable,
                    str(root / "benchmarks/hutter_projection_probe.py"), "decode", "{workdir}/candidate.cixproj", "{workdir}/restored.bin",
                    "--runtime-manifest", str(area / "runtime-manifest.json")],
                "stage": "screening", "stratum": stratum, "prepared_not_run": True}
    fixture_sha = "dece3fc9570a1ff1288f2259bb004d013959170c0c387dedd28db66fd4c1ad26"
    if control and source["sha256"] != fixture_sha:
        manifest["decode_size_gate"] = {"control_receipt": control["receipt"], "archive_sha256": control["archive_sha256"], "control_bytes": control["archive_bytes"],
                                         "matching_configuration_keys": list(CONTROL_KEYS)}
    # Hash current declared build content before creating the immutable cell.
    # Both this map and the full manifest participate in identity, so source or
    # option changes cannot collide with an earlier prepared trial.
    build = build_identity(manifest, root)
    key = digest({"input_id": input_id, "recipe": recipe, "build_sha256": build, "manifest": manifest, "stratum": stratum})
    trial = "projection-" + key[:24]; path = area / "manifests" / f"{trial}.json"; immutable(path, manifest)
    loaded, manifest_sha = load_manifest(path); build = build_identity(loaded, root)
    cell = {"cell_id": trial, "owner": "/root/paragraph_trials", "input_id": input_id, "recipe": recipe, "stratum": stratum,
            "state": "PREPARED_NOT_RUN", "manifest_path": str(path), "expected_manifest_sha256": manifest_sha, "expected_build_sha256": build,
            "output_dir": str(area / "runs" / trial), "control": control, "resource_lease": manifest["budget"]}
    immutable(area / "cells" / f"{trial}.json", cell)
    return cell


def _terminal(output: Path) -> tuple[Path | None, dict | None]:
    found = []
    for name in ("receipt.json", "size-rejected.json", "failed.json"):
        found.extend(output.glob("*/" + name))
    if len(found) > 1:
        raise ValueError("multiple terminal records for one immutable projection cell")
    return (found[0], json.loads(found[0].read_text())) if found else (None, None)


def _probe_accounting(value: dict, terminal_path: Path | None) -> dict:
    """Read declared encode JSON without treating it as a separate result."""
    if terminal_path is None: return {}
    for log in terminal_path.parent.glob("*.stdout.log"):
        for line in reversed(log.read_text(errors="replace").splitlines()):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and "inner_total_bytes" in row:
                return row
    return {}


def _projection_physical(archive: Path) -> dict:
    """Account a complete CIXPROJ1 archive directly, never from stdout alone."""
    from benchmarks import hutter_projection_probe as probe
    blob = archive.read_bytes()
    if len(blob) < probe.HEADER.size + len(probe.METADATA):
        raise ValueError("short projection archive")
    magic, recipe, original, projected, metadata = probe.HEADER.unpack_from(blob)
    if magic != probe.MAGIC or recipe not in (1, 2, 3) or metadata != len(probe.METADATA):
        raise ValueError("invalid projection outer frame")
    if blob[probe.HEADER.size:probe.HEADER.size + metadata] != probe.METADATA:
        raise ValueError("projection fixed metadata mismatch")
    inner = probe.inner_accounting(blob[probe.HEADER.size + metadata:])
    if len(blob) != probe.HEADER.size + metadata + inner["inner_total_bytes"]:
        raise ValueError("projection physical size mismatch")
    return {"wrapper_bytes": len(blob), "archive_sha256": sha(archive), "outer_framing_bytes": probe.HEADER.size,
            "outer_metadata_bytes": metadata, "original_bytes": original, "projected_bytes": projected, **inner}


def report(*, root: Path = ROOT) -> dict:
    root = root.resolve(); area = root / REL; rows = []
    for path in sorted((area / "cells").glob("*.json")):
        cell = json.loads(path.read_text()); terminal_path, value = _terminal(Path(cell["output_dir"]))
        build_bytes = sum((root / name).stat().st_size for name in cell["expected_build_sha256"] if (root / name).is_file())
        row = {"cell_id": cell["cell_id"], "recipe": cell["recipe"], "stratum": cell["stratum"], "state": cell["state"],
               "input": json.loads(Path(cell["manifest_path"]).read_text())["input"], "control": cell.get("control"), "control_cached_timings": "NOT_REPORTED_AS_MATCHED_SPEED",
               "wrapper_bytes": None, "inner_payload_bytes": None, "inner_total_bytes": None, "metadata_bytes": 37,
               "framing_bytes": 29, "program_source_bytes": build_bytes, "program_package_bytes": "NOT_MEASURED",
               "verification": "NOT_RUN", "size_delta_vs_control_bytes": None, "decode_skipped": False,
               "encode_seconds": None, "decode_seconds": None, "memory_lower_bound_bytes": None, "terminal_record": str(terminal_path) if terminal_path else None}
        if value is not None:
            row["state"] = value.get("status", "FAILED")
            row["input"] = value.get("identity", {}).get("input")
            row["wrapper_bytes"] = None
            row["decode_skipped"] = row["state"] == "SIZE_REJECTED_UNVERIFIED"
            verification = value.get("verification", {})
            artifacts = value.get("artifacts", {}); archive, restored = Path(artifacts.get("archive", "")), Path(artifacts.get("restored", ""))
            # A size-gated archive is a complete physical observation, but it
            # remains unverified and is never promoted or ranked as a win.
            if row["state"] in ("VERIFIED_SCREENING", "SIZE_REJECTED_UNVERIFIED") and archive.is_file():
                try:
                    physical = _projection_physical(archive)
                    if physical['archive_sha256'] != value.get('archive_sha256') or physical['wrapper_bytes'] != value.get('archive_bytes'):
                        raise ValueError('terminal archive identity mismatch')
                    row.update(physical)
                except ValueError:
                    row["state"] = "FAILED_INVALID_ARCHIVE"
                    row["wrapper_bytes"] = None
            if row["state"] == "VERIFIED_SCREENING" and verification.get("matched"):
                source = row["input"] or {}
                if archive.is_file() and restored.is_file() and sha(archive) == value.get("archive_sha256") and restored.stat().st_size == source.get("length") and sha(restored) == source.get("sha256"):
                    row["verification"] = "SHA256_MATCHED_REHASHED"
                else: row["verification"] = "VERIFICATION_ARTIFACT_MISMATCH"
            else: row["verification"] = row["state"]
            phases = [x for x in value.get("phases", []) if x]
            row["encode_seconds"] = next((x.get("elapsed_seconds") for x in phases if str(x.get("phase", "")).endswith("-encode")), None)
            row["decode_seconds"] = next((x.get("elapsed_seconds") for x in phases if str(x.get("phase", "")).endswith("-decode")), None)
            row["memory_lower_bound_bytes"] = max((x.get("sampled_cgroup_memory_high_water_bytes", 0) for x in phases), default=None)
            row["temporary_disk_high_water_bytes"] = max((x.get("peak_temp_bytes", 0) for x in phases), default=None)
            if cell.get("control") and row["wrapper_bytes"] is not None: row["size_delta_vs_control_bytes"] = row["wrapper_bytes"] - cell["control"]["archive_bytes"]
            accounting = _probe_accounting(value, terminal_path)
            row["projection_diagnostics"] = accounting
            row["inner_payload_bytes"] = row.get("jxl_payload_bytes")
        rows.append(row)
    rows.sort(key=lambda r: (r['stratum'], r['input']['sha256'], r['wrapper_bytes'] if r['wrapper_bytes'] is not None else float('inf'), r['recipe']))
    groups = {}
    for row in rows:
        group = (row['stratum'], row['input']['sha256'])
        if row['wrapper_bytes'] is not None:
            groups[group] = groups.get(group, 0) + 1
            row['observed_size_order_within_input'] = groups[group]
        row['verified_gain'] = row['verification'] == 'SHA256_MATCHED_REHASHED' and row['size_delta_vs_control_bytes'] is not None and row['size_delta_vs_control_bytes'] < 0
    result = {"schema": 2, "projection_cells": rows, "speed_note": "PAQ control timings are cached historical measurements; CIX projection timings are separate and no matched speed claim is made.",
              "cost_note": "No PAQ fallback exists. Every terminal status, including size-rejected decode skips and failures, remains visible."}
    (area / "projection-report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = ["# CIX projection research", "", "| Recipe | Priority | Input range | Control bytes | Complete bytes | Δ | Verification | Encode / decode s | Memory lower bound | Decision |", "|---|---|---|---:|---:|---:|---|---:|---:|---|"]
    for row in rows:
        inp = row["input"] or {}; name = f"{inp.get('offset','—')}+{inp.get('length','—')} {inp.get('sha256','')[:12]}"
        control = (row.get("control") or {}).get("archive_bytes", "—")
        times = f"{row['encode_seconds'] if row['encode_seconds'] is not None else '—'} / {row['decode_seconds'] if row['decode_seconds'] is not None else '—'}"
        decision = "verified gain; holdout/scaling still required" if row['verified_gain'] else "verified loss" if row['verification'] == 'SHA256_MATCHED_REHASHED' and row['size_delta_vs_control_bytes'] is not None else "correctness only; no size control" if row['verification'] == 'SHA256_MATCHED_REHASHED' else "size loss; decode skipped" if row["decode_skipped"] else "not run" if row["state"] == "PREPARED_NOT_RUN" else "failure retained"
        lines.append(f"| {row['recipe']} | {row['recipe']} priority | {name} | {control} | {row['wrapper_bytes'] if row['wrapper_bytes'] is not None else '—'} | {row['size_delta_vs_control_bytes'] if row['size_delta_vs_control_bytes'] is not None else '—'} | {row['verification']} | {times} | {row['memory_lower_bound_bytes'] if row['memory_lower_bound_bytes'] is not None else '—'} | {decision} |")
    lines += ["", "PAQ controls are historical size references only. CIX and PAQ timing measurements are not presented as a matched speed comparison. Program package size is not measured here.", ""]
    (area / "projection-report.md").write_text("\n".join(lines))
    return result


def run_wave(cells: list[dict] | list[str], *, root: Path = ROOT) -> list[dict]:
    root = root.resolve(); decoded = [json.loads(Path(cell).read_text()) if isinstance(cell, str) else cell for cell in cells]
    if any(cell.get("state") != "PREPARED_NOT_RUN" for cell in decoded): raise ValueError("only prepared cells may be dispatched")
    return WaveScheduler(root, max_jobs=2, max_memory_bytes=6_000_000_000, max_temp_bytes=2_000_000_000).run_wave(decoded)


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--source-json", type=Path, required=True); p.add_argument("--recipe", choices=RECIPES, required=True); p.add_argument("--cpu", type=int, required=True); p.add_argument("--control-receipt", type=Path); p.add_argument("--stratum", default="fixed_development")
    p = sub.add_parser("run-wave"); p.add_argument("cells", nargs="+")
    sub.add_parser("report"); args = parser.parse_args()
    if args.command == "prepare": result = prepare(json.loads(args.source_json.read_text()), args.recipe, args.cpu, args.control_receipt, args.stratum)
    elif args.command == "run-wave": result = run_wave(args.cells)
    else: result = report()
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
