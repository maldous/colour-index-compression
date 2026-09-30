#!/usr/bin/env python3
"""Regeneratable physical-evidence report for bounded Wikipedia column trials."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/research/2026-09-30-wikipedia-columns"
RUNS = BASE / "runs"
HEADER = struct.Struct(">8sBQQI")
WRAPPERS = {b"CIXSTR1\0": range(4), b"CIXWCOL1": range(3)}
EXPECTED = {"small": {"original", "raw", "remaining", "rank"}, "dev0": {"raw", "remaining", "rank"}}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rpath(path: Path) -> str:
    return os.path.relpath(path, BASE)


def parse_archive(path: Path, expected_sha: str | None, expected_bytes: int | None) -> dict:
    actual_sha, size = sha(path), path.stat().st_size
    if expected_sha is not None and actual_sha != expected_sha:
        raise ValueError(f"archive SHA mismatch: {path}")
    if expected_bytes is not None and size != expected_bytes:
        raise ValueError(f"archive size mismatch: {path}")
    blob = path.read_bytes()
    if len(blob) < HEADER.size:
        raise ValueError(f"short archive: {path}")
    magic, mode, original, transformed, metadata = HEADER.unpack_from(blob)
    payload = len(blob) - HEADER.size - metadata
    if magic not in WRAPPERS or mode not in WRAPPERS[magic] or payload < 0 or HEADER.size + metadata + payload != len(blob):
        raise ValueError(f"outer physical-size conservation failure: {path}")
    if blob[HEADER.size + metadata:HEADER.size + metadata + 6] != b"paq8px":
        raise ValueError(f"archive payload is not a PAQ stream: {path}")
    return {"archive": rpath(path), "archive_sha256": actual_sha, "total_bytes": size,
            "outer_header_bytes": HEADER.size, "outer_metadata_bytes": metadata,
            "paq_payload_bytes": payload, "original_bytes": original, "transformed_bytes": transformed,
            "outer_magic": magic.decode("ascii"), "outer_mode": mode, "physical_size_conserved": True}


def load_control() -> dict:
    ref = json.loads((BASE / "control-reference.json").read_text())
    receipt_path = Path(ref["receipt"]); receipt = json.loads(receipt_path.read_text())
    if receipt["status"] != "VERIFIED_SCREENING" or not receipt["verification"]["matched"]:
        raise ValueError("dev0 control reference is not verified")
    archive = parse_archive(Path(receipt["artifacts"]["archive"]), ref["archive_sha256"], ref["archive_bytes"])
    restored = Path(receipt["artifacts"]["restored"])
    if sha(restored) != ref["input"]["sha256"]:
        raise ValueError("dev0 control restored SHA mismatch")
    return {"reference": ref, "receipt": receipt, "archive": archive}


def terminal_record(directory: Path) -> dict | None:
    files = [directory / name for name in ("receipt.json", "size-rejected.json", "failed.json")]
    path = next((item for item in files if item.is_file()), None)
    if path is None:
        return None
    row = json.loads(path.read_text()); identity = row["identity"]
    configuration, input_id = identity["configuration"], identity["input"]
    mode, phase = configuration["mode"], configuration.get("experiment_phase", "unknown")
    archive_path = Path(row["artifacts"]["archive"])
    archive = None
    if archive_path.is_file():
        archive = parse_archive(archive_path, row.get("archive_sha256"), row.get("archive_bytes"))
    verified = row["status"] == "VERIFIED_SCREENING" and row["verification"].get("matched")
    restored_sha = None
    if verified:
        restored = Path(row["artifacts"]["restored"])
        if not restored.is_file():
            raise ValueError(f"verified row lacks restored artifact: {path}")
        restored_sha = sha(restored)
        if restored_sha != input_id["sha256"] or restored_sha != row["verification"]["restored_sha256"]:
            raise ValueError(f"verified restored SHA mismatch: {path}")
    stdout = next(directory.glob("*-encode.stdout.log"), None)
    accounting = None
    if stdout and stdout.is_file():
        for line in stdout.read_text(errors="replace").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict) and "transform_accounting" in value:
                    accounting = value["transform_accounting"]
            except json.JSONDecodeError:
                pass
    return {"id": directory.name, "status": row["status"], "phase": phase, "mode": mode,
            "input": input_id, "configuration": configuration, "build_sha256": identity["build_sha256"],
            "record": rpath(path), "archive": archive, "restored_sha256": restored_sha,
            "verification": row["verification"], "decode_skipped": row["status"] == "SIZE_REJECTED_UNVERIFIED",
            "decode_size_gate": row.get("decode_size_gate"), "phases": row.get("phases", []),
            "transform_accounting": accounting, "footprint_note": "Program/runtime footprint is recorded only by immutable build identities and the pinned PAQ binary; it is not a Hutter score."}


def matched_control(row: dict, dev_control: dict, small_controls: dict[str, dict]) -> tuple[dict | None, str | None]:
    if row["phase"] == "dev0":
        reference = dev_control["reference"]["input"]
        control = dev_control["archive"]
        config = dev_control["receipt"]["identity"]["configuration"]
    elif row["phase"] == "small":
        control_row = small_controls.get("original")
        if not control_row or not control_row["archive"] or control_row["status"] != "VERIFIED_SCREENING":
            return None, "small original control pending"
        reference, control, config = control_row["input"], control_row["archive"], control_row["configuration"]
    else:
        return None, "unknown phase"
    if any(row["input"].get(key) != reference.get(key) for key in ("offset", "length", "sha256")):
        return None, "input identity differs from control"
    for key in ("paq_binary_sha256", "paq_options", "source_filename"):
        if row["configuration"].get(key) != config.get(key):
            return None, f"configuration differs: {key}"
    return control, None


def collect() -> dict:
    dev_control = load_control()
    records = [record for directory in sorted(RUNS.iterdir()) if directory.is_dir() if (record := terminal_record(directory))]
    small = {record["mode"]: record for record in records if record["phase"] == "small"}
    for record in records:
        control, reason = matched_control(record, dev_control, small)
        record["control"] = control
        record["control_match_reason"] = reason
        if control and record["archive"]:
            record["difference_vs_control_bytes"] = record["archive"]["total_bytes"] - control["total_bytes"]
        else:
            record["difference_vs_control_bytes"] = None
    pending = {phase: sorted(EXPECTED[phase] - {row["mode"] for row in records if row["phase"] == phase}) for phase in EXPECTED}
    return {"schema": "cix-wikipedia-columns-report-v1", "control_reference": dev_control["archive"], "records": records,
            "pending_expected": pending, "limitations": ["Small synthetic results are shown separately and are not extrapolated to Wikipedia.", "Size-rejected archives are complete physical archives but are not round-trip verified.", "No aggregate promotion, segment-cost, full-enwik9, footprint score, or Hutter-score claim is calculated."],
            "all_dev0_verified": all(row["status"] == "VERIFIED_SCREENING" for row in records if row["phase"] == "dev0") and not pending["dev0"]}


def phase_resources(phases: list) -> str:
    if not phases:
        return "—"
    values = []
    for phase in phases:
        if phase:
            values.append(f"{phase['phase'].rsplit('-',1)[-1]} {phase['elapsed_seconds']:.3f}s / CPU {phase.get('cpu_usage_seconds', 0):.3f}s / sampled cgroup high-water {phase.get('sampled_cgroup_memory_high_water_bytes', 0):,} B / tmp {phase.get('peak_temp_bytes', 0):,} B")
    return "; ".join(values) or "decode skipped"


def markdown(report: dict) -> str:
    lines = ["# Wikipedia column trial comparison", "", "All totals are independently rehashed completed outer archives: 29-byte wrapper header + outer metadata + PAQ payload. Inner transform accounting is compressed inside the PAQ payload and is displayed for audit only; it is never added again."]

    def table(phase: str, title: str) -> None:
        lines.extend(["", f"## {title}", "", "| Mode | Status | Total | Payload | Metadata | Header | Difference vs matched control | Verification | Decode |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"])
        for row in (item for item in report["records"] if item["phase"] == phase):
            archive = row["archive"]
            if archive:
                values = f"{archive['total_bytes']:,} | {archive['paq_payload_bytes']:,} | {archive['outer_metadata_bytes']:,} | 29"
            else:
                values = "— | — | — | —"
            diff = "—" if row["difference_vs_control_bytes"] is None else f"{row['difference_vs_control_bytes']:+,} B"
            verification = "SHA-256 exact" if row["status"] == "VERIFIED_SCREENING" else "NOT ROUND-TRIP VERIFIED"
            decode = "skipped after completed size gate" if row["decode_skipped"] else ("completed" if row["status"] == "VERIFIED_SCREENING" else "not completed")
            lines.append(f"| {row['mode']} | {row['status']} | {values} | {diff} | {verification} | {decode} |")
        missing = report["pending_expected"].get(phase, [])
        if missing:
            lines.append(f"| {', '.join(missing)} | PENDING — no eligible bytes | — | — | — | — | — | — | — |")

    table("dev0", "Wikipedia dev0 candidate totals")
    table("small", "Synthetic fixture results only")
    lines.extend(["", "The synthetic fixture is a correctness and mechanism screen only. It is not extrapolated to Wikipedia or used for promotion."])
    lines += ["", "## Evidence detail", ""]
    for row in report["records"]:
        artifacts = []
        if row["archive"]:
            artifacts.append(f"archive [{row['archive']['archive']}]({row['archive']['archive']})")
        restored = row.get("restored_sha256")
        if restored:
            artifacts.append(f"restored SHA-256 `{restored}`")
        commands = "; ".join(f"`{phase['command']}`" for phase in row["phases"] if phase)
        lines += [f"### {row['phase']} / {row['mode']} / {row['status']}", "", f"- Record: [{row['record']}]({row['record']}).", f"- Input: offset {row['input']['offset']:,}, length {row['input']['length']:,}, SHA-256 `{row['input']['sha256']}`.", f"- Control compatibility: {row['control_match_reason'] or 'matched input and pinned PAQ configuration'}.", f"- Transform accounting from encoder stdout (paid inside PAQ): `{json.dumps(row['transform_accounting'], sort_keys=True)}`.", f"- Resources: {phase_resources(row['phases'])}.", f"- Build identities: `{json.dumps(row['build_sha256'], sort_keys=True)}`.", f"- {row['footprint_note']}", ""]
        lines[-2:-2] = [f"- Artifacts: {'; '.join(artifacts) or 'none retained'}.", f"- Immutable commands: {commands or 'not available'}."]
    lines += ["## Interpretation limits", ""] + [f"- {item}" for item in report["limitations"]]
    return "\n".join(lines) + "\n"


def generate() -> dict:
    report = collect()
    (BASE / "columns-comparison.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (BASE / "columns-comparison.md").write_text(markdown(report))
    return report


def self_test() -> None:
    """Exercise both wrapper magics and corruption refusal without evidence writes."""
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        for magic, modes in WRAPPERS.items():
            archive = folder / magic.hex()
            metadata, payload = b"{}", b"paq8px-test"
            archive.write_bytes(HEADER.pack(magic, min(modes), 9, 8, len(metadata)) + metadata + payload)
            parsed = parse_archive(archive, sha(archive), archive.stat().st_size)
            assert parsed["outer_magic"] == magic.decode("ascii")
            try:
                parse_archive(archive, "0" * 64, archive.stat().st_size)
            except ValueError as error:
                assert "SHA" in str(error)
            else:
                raise AssertionError("corrupt expected SHA accepted")
    assert "SIZE_REJECTED_UNVERIFIED" != "VERIFIED_SCREENING"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--self-test", action="store_true"); args = parser.parse_args()
    if args.self_test: self_test(); print("self-test passed"); return 0
    report = generate(); print(json.dumps({"terminal_rows": len(report["records"]), "all_dev0_verified": report["all_dev0_verified"]}, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
