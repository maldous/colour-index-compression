#!/usr/bin/env python3
"""Independently audit and render the frozen moderate Wikipedia structure stage.

This reads receipts and already-written archives only.  It never encodes,
decodes, selects candidates, or launches a workload.  The generated report is
deliberately incomplete until all twelve predeclared rows are verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from collections import defaultdict
from pathlib import Path


HEADER = struct.Struct(">8sBQQI")
MAGIC = b"CIXSTR1\0"
MODES = ("original", "B", "C", "D")
REGIONS = ("dev0", "dev100M", "dev400M")
OFFSETS = {"dev0": 0, "dev100M": 100000000, "dev400M": 400000000}
LENGTH = 4 * 1024 * 1024


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def link(path: str, root: Path, moderate: Path) -> str:
    target = root / path
    relative = os.path.relpath(target, moderate)
    return f"[{relative}]({relative})"


def read_row(row: dict, root: Path) -> dict:
    receipt_path = root / row["receipt"]
    receipt = json.loads(receipt_path.read_text())
    identity = receipt["identity"]
    source = identity["input"]
    mode = identity["configuration"]["mode"]
    region = row["region"]
    if region not in OFFSETS or mode not in MODES or source["offset"] != OFFSETS[region] or source["length"] != LENGTH:
        raise ValueError(f"region/mode/input manifest mismatch: {receipt_path}")
    basic = {"region": region, "mode": mode, "status": receipt["status"], "input": source,
             "receipt": rel(receipt_path, root), "phases": receipt.get("phases", []),
             "budget": receipt["budget"], "build_sha256": identity["build_sha256"],
             "configuration": identity["configuration"]}
    if receipt["status"] != "VERIFIED_SCREENING" or row["status"] != "VERIFIED_SCREENING":
        return {**basic, "failure": {"verification": receipt.get("verification"),
                                       "archive_bytes": receipt.get("archive_bytes"),
                                       "phases": receipt.get("phases", [])}}
    archive = Path(receipt["artifacts"]["archive"])
    restored = Path(receipt["artifacts"]["restored"])
    if not archive.is_file() or not restored.is_file():
        raise ValueError(f"missing physical artifact: {receipt_path}")
    archive_sha, restored_sha = digest(archive), digest(restored)
    if archive_sha != receipt["archive_sha256"] or archive.stat().st_size != receipt["archive_bytes"]:
        raise ValueError(f"archive identity mismatch: {receipt_path}")
    if restored_sha != source["sha256"] or restored_sha != receipt["verification"]["restored_sha256"]:
        raise ValueError(f"independent restoration mismatch: {receipt_path}")
    blob = archive.read_bytes()
    if len(blob) < HEADER.size:
        raise ValueError(f"short structure archive: {receipt_path}")
    magic, outer_mode, original_bytes, transformed_bytes, metadata_bytes = HEADER.unpack_from(blob)
    if magic != MAGIC or outer_mode not in (0, 1, 2, 3):
        raise ValueError(f"invalid structure outer header: {receipt_path}")
    payload_bytes = len(blob) - HEADER.size - metadata_bytes
    if payload_bytes < 0 or HEADER.size + metadata_bytes + payload_bytes != len(blob):
        raise ValueError(f"physical-size conservation failure: {receipt_path}")
    metadata = json.loads(blob[HEADER.size:HEADER.size + metadata_bytes])
    expected_code = {"original": 0, "C": 1, "D": 2, "B": 3}[mode]
    if outer_mode != expected_code or original_bytes != source["length"]:
        raise ValueError(f"outer mode/input mismatch: {receipt_path}")
    phases = receipt["phases"]
    if len(phases) != 2 or not all(phase and phase["exit_code"] == 0 for phase in phases):
        raise ValueError(f"unverified phase record: {receipt_path}")
    accounting = metadata if mode == "B" else metadata
    return {
        **basic, "archive": rel(archive, root), "restored": rel(restored, root), "archive_sha256": archive_sha,
        "restored_sha256": restored_sha, "total_bytes": len(blob),
        "outer_header_bytes": HEADER.size, "outer_metadata_bytes": metadata_bytes,
        "paq_payload_bytes": payload_bytes, "original_bytes": original_bytes,
        "transformed_bytes": transformed_bytes, "outer_mode": outer_mode,
        "transform_accounting": accounting,
        "mode_b_actual_transform_mode": accounting.get("mode") if mode == "B" else None,
        "mode_b_literal_fallback": (mode == "B" and accounting.get("mode") == 0),
        "phases": phases, "budget": receipt["budget"],
        "build_sha256": identity["build_sha256"], "configuration": identity["configuration"],
        "physical_size_conserved": True,
    }


def summaries(rows: list[dict]) -> dict:
    pairs = [(row["region"], row["mode"]) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise ValueError("duplicate (region, mode) result rows")
    by_region = defaultdict(list)
    for row in rows:
        by_region[row["region"]].append(row)
    for region, members in by_region.items():
        hashes = {member["input"]["sha256"] for member in members}
        if len(hashes) != 1:
            raise ValueError(f"mismatched input hashes within {region}")
    index = {(row["region"], row["mode"]): row for row in rows}
    expected = {(r, m) for r in REGIONS for m in MODES}
    all_present = len(index) == len(expected) and set(index) == expected
    failures = [f"{row['region']}/{row['mode']}" for row in rows if row["status"] != "VERIFIED_SCREENING"]
    complete = all_present and not failures
    result = {"all_12_verified": complete, "missing": [f"{r}/{m}" for r in REGIONS for m in MODES if (r, m) not in index], "failed": failures, "candidates": {}}
    if not complete:
        return result
    original_total = sum(index[(region, "original")]["total_bytes"] for region in REGIONS)
    for mode in MODES[1:]:
        total = sum(index[(region, mode)]["total_bytes"] for region in REGIONS)
        wins = sum(index[(region, mode)]["total_bytes"] < index[(region, "original")]["total_bytes"] for region in REGIONS)
        saving = original_total - total
        saving_percent = saving / original_total * 100
        result["candidates"][mode] = {
            "aggregate_total_bytes": total, "original_total_bytes": original_total,
            "aggregate_saving_bytes": saving, "aggregate_saving_percent": saving_percent,
            "region_wins": wins, "permits_16m": saving > 0 and wins >= 2,
            "holdout_size_threshold_met": saving / original_total >= 0.005,
            "holdout_region_wins_met": wins >= 2,
            "holdout_size_criterion_met": saving / original_total >= 0.005 and wins >= 2,
            "holdout_note": "Size and two-region criteria only; candidate must also be frozen. No holdout launch is implied.",
        }
    return result


def render(rows: list[dict], aggregate: dict, root: Path, moderate: Path) -> str:
    lines = ["# Frozen moderate Wikipedia structure report", "", "This is a physical-size audit of predeclared 4 MiB contiguous development runs. It is not an actual-segment cost, full-enwik9 score, Hutter score, or qualification claim.", "", "## Completion", "", f"- All 12 predeclared rows verified: **{aggregate['all_12_verified']}**."]
    if aggregate["missing"]:
        lines.append("- Missing or non-verified rows: " + ", ".join(aggregate["missing"]) + ".")
        lines.append("- Aggregate promotion is intentionally not calculated until every required row is verified.")
    if aggregate["failed"]:
        lines.append("- Failed rows: " + ", ".join(aggregate["failed"]) + ". Their physical totals are not eligible for comparison or promotion.")
    lines += ["", "## Preselection physical results", "", "| Region | Candidate | Total bytes | PAQ payload | Outer metadata | Outer header | Transform input bytes | B transform mode / fallback | Exact restore |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for row in rows:
        if row["status"] != "VERIFIED_SCREENING":
            lines.append(f"| {row['region']} | {row['mode']} | FAILED — no eligible bytes | — | — | — | — | Not verified |")
            continue
        b = "—" if row["mode"] != "B" else f"{row['mode_b_actual_transform_mode']} / {row['mode_b_literal_fallback']}"
        lines.append(f"| {row['region']} | {row['mode']} | {row['total_bytes']:,} | {row['paq_payload_bytes']:,} | {row['outer_metadata_bytes']:,} | {row['outer_header_bytes']} | {row['transformed_bytes']:,} | {b} | SHA-256 matched |")
    lines += ["", "Each total is independently rehashed and checked as `29-byte CIXSTR1 outer header + outer JSON metadata + PAQ payload`. Transform frames and their component accounting are inputs *inside* the compressed PAQ payload; they are reported below for audit and are not added a second time to archive bytes.", "", "## Transform accounting, provenance and resources", ""]
    for row in rows:
        if row["status"] != "VERIFIED_SCREENING":
            lines += [f"### {row['region']} / {row['mode']} — FAILED", "", f"- Receipt: {link(row['receipt'], root, moderate)}.", f"- Verification state: `{json.dumps(row['failure']['verification'], sort_keys=True)}`.", f"- Phase records: `{json.dumps(row['failure']['phases'], sort_keys=True)}`.", ""]
            continue
        transform = json.dumps(row["transform_accounting"], sort_keys=True)
        build = ", ".join(f"`{name}` `{value}`" for name, value in sorted(row["build_sha256"].items()))
        enc, dec = row["phases"]
        lines += [f"### {row['region']} / {row['mode']}", "", f"- Input: `{row['input']['path']}` offset {row['input']['offset']:,}, length {row['input']['length']:,}, SHA-256 `{row['input']['sha256']}`.", f"- Artifacts: {link(row['archive'], root, moderate)}; {link(row['restored'], root, moderate)}; {link(row['receipt'], root, moderate)}.", f"- Archive SHA-256: `{row['archive_sha256']}`. Restored SHA-256: `{row['restored_sha256']}`.", f"- Transform accounting (paid before PAQ, not additive to the finished archive): `{transform}`.", f"- Encode: {enc['elapsed_seconds']:.3f}s, CPU {row['budget']['cpu']}, CPU time {enc['cpu_usage_seconds']:.3f}s, sampled cgroup memory lower bound {enc['sampled_cgroup_memory_high_water_bytes']:,} B, temporary disk {enc['peak_temp_bytes']:,} B.", f"- Decode: {dec['elapsed_seconds']:.3f}s, CPU {row['budget']['cpu']}, CPU time {dec['cpu_usage_seconds']:.3f}s, sampled cgroup memory lower bound {dec['sampled_cgroup_memory_high_water_bytes']:,} B, temporary disk {dec['peak_temp_bytes']:,} B.", f"- Immutable build identities: {build}.", f"- Exact commands: encode `{enc['command']}`; decode `{dec['command']}`.", ""]
    if aggregate["all_12_verified"]:
        lines += ["## Promotion calculation", "", "| Candidate | Aggregate saving | Saving % | Region wins | 16 MiB permitted | Holdout size criterion |", "| --- | ---: | ---: | ---: | --- | --- |"]
        for mode, value in aggregate["candidates"].items():
            lines.append(f"| {mode} | {value['aggregate_saving_bytes']:,} B | {value['aggregate_saving_percent']:.4f}% | {value['region_wins']}/3 | {value['permits_16m']} | {value['holdout_size_criterion_met']} |")
        lines += ["", "A true 16 MiB follow-up requires a positive aggregate physical saving and at least two region wins. Holdout size eligibility also requires both at least 0.5% aggregate saving and two region wins; it does not launch a holdout or override the frozen-candidate requirement."]
    return "\n".join(lines) + "\n"


def generate(root: Path) -> dict:
    root = root.resolve(); moderate = root / "docs/research/2026-09-30-wikipedia-structure/moderate"
    completed = moderate / "completed-results.json"
    if not completed.is_file():
        raise FileNotFoundError("collect completed-results.json before generating a report")
    listed = json.loads(completed.read_text())
    rows = [read_row(row, root) for row in listed]
    rows.sort(key=lambda row: (REGIONS.index(row["region"]), MODES.index(row["mode"])))
    aggregate = summaries(rows)
    report = {"schema": "cix-structure-moderate-report-v1", "rows": rows, "aggregate": aggregate,
              "limitations": ["Nested-prefix totals are not segment costs or full-corpus projections.", "Research concurrency timings are not qualification timings.", "Transform accounting is inside PAQ payload and is not added twice."],
              "report_sha256_input": hashlib.sha256(json.dumps({"rows": rows, "aggregate": aggregate}, sort_keys=True).encode()).hexdigest()}
    # Publication is deliberately all-or-nothing: do not overwrite a prior report
    # with different evidence.
    for path, content in ((moderate / "report.json", json.dumps(report, indent=2, sort_keys=True) + "\n"), (moderate / "report.md", render(rows, aggregate, root, moderate))):
        if path.exists() and path.read_text() != content:
            raise ValueError(f"immutable report differs: {path}")
        path.write_text(content)
    return report


def self_test() -> None:
    """Small no-I/O fixture checks for incomplete and invalid aggregation paths."""
    base = {"region": "dev0", "mode": "original", "status": "FAILED", "input": {"offset": 0, "length": LENGTH, "sha256": "x"}}
    assert not summaries([base])["all_12_verified"]
    try:
        summaries([base, base])
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate rows accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(); print("self-test passed"); return 0
    report = generate(args.root)
    print(json.dumps({"rows": len(report["rows"]), "all_12_verified": report["aggregate"]["all_12_verified"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
