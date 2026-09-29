#!/usr/bin/env python3
"""Fail-closed local preflight for a possible Hutter Prize submission.

This is an evidence gate, not a submission tool and not a statement of official
eligibility.  It deliberately requires a manifest with measured whole-run
process-tree limits and a locally verified canonical enwik9 input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ENWIK9_BYTES = 1_000_000_000
ENWIK9_SHA256 = "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc"
CURRENT_RECORD_BYTES = 110_793_128
# The prize condition is strict: S < 0.99 * L.  With integer bytes the largest
# admissible S is floor(0.99 * L), because this particular product is noninteger.
HURDLE_BYTES = 109_685_196
RAM_LIMIT_BYTES = 10_000_000_000
TEMP_LIMIT_BYTES = 100_000_000_000
RULES_URL = "https://www.hutter1.net/prize/hrules.htm"
FAQ_URL = "https://www.hutter1.net/prize/hfaq.htm"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: Any, field: str, failures: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        failures.append(f"{field}: missing path")
        return None
    path = Path(value)
    if not path.is_file():
        failures.append(f"{field}: file does not exist: {path}")
        return None
    return path


def _artifact(value: Any, field: str, failures: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        failures.append(f"{field}: missing artifact record")
        return None
    path = _path(value.get("path"), f"{field}.path", failures)
    if path is None:
        return None
    expected = value.get("sha256")
    actual_hash = sha256_file(path)
    if expected != actual_hash:
        failures.append(f"{field}: SHA-256 is missing or does not match the file")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": actual_hash}


def _json_evidence(value: Any, field: str, failures: list[str]) -> dict[str, Any] | None:
    record = _artifact(value, field, failures)
    if record is None:
        return None
    try:
        payload = json.loads(Path(record["path"]).read_text())
    except (OSError, json.JSONDecodeError):
        failures.append(f"{field}: not valid JSON")
        return None
    if not isinstance(payload, dict):
        failures.append(f"{field}: JSON must be an object")
        return None
    record["payload"] = payload
    return record


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _resource(stage: str, value: Any, failures: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        failures.append(f"measurements.{stage}: missing whole-run resource record")
        return None
    required = ("wall_seconds", "peak_process_tree_rss_bytes", "peak_temp_bytes",
                "cpu_cores", "gpu_used", "geekbench5_single_core")
    missing = [key for key in required if key not in value]
    if missing:
        failures.append(f"measurements.{stage}: missing {', '.join(missing)}")
        return None
    if value.get("measurement_scope") != "whole_enwik9_process_tree":
        failures.append(f"measurements.{stage}: scope must be whole_enwik9_process_tree")
    if type(value["cpu_cores"]) is not int or value["cpu_cores"] != 1:
        failures.append(f"measurements.{stage}: must use one CPU core")
    if value["gpu_used"] is not False:
        failures.append(f"measurements.{stage}: GPU use is not permitted")
    if (type(value["geekbench5_single_core"]) not in (int, float)
            or type(value["wall_seconds"]) not in (int, float)):
        failures.append(f"measurements.{stage}: time and Geekbench score must be numeric, not strings or booleans")
        return None
    try:
        score = float(value["geekbench5_single_core"])
        elapsed = float(value["wall_seconds"])
        rss = value["peak_process_tree_rss_bytes"]
        temp = value["peak_temp_bytes"]
    except (TypeError, ValueError):
        failures.append(f"measurements.{stage}: invalid numeric value")
        return None
    if not math.isfinite(score) or score <= 0:
        failures.append(f"measurements.{stage}: Geekbench 5 single-core score must be finite and positive")
    if not math.isfinite(elapsed) or elapsed <= 0:
        failures.append(f"measurements.{stage}: wall time must be finite and positive")
    elif math.isfinite(score) and score > 0 and elapsed >= 70_000 * 3600 / score:
        failures.append(f"measurements.{stage}: does not satisfy strict 70,000/T hour rule")
    if not _nonnegative_int(rss):
        failures.append(f"measurements.{stage}: process-tree RSS must be a nonnegative integer")
    elif rss > RAM_LIMIT_BYTES:
        failures.append(f"measurements.{stage}: process-tree RSS exceeds 10,000,000,000 bytes")
    if not _nonnegative_int(temp):
        failures.append(f"measurements.{stage}: temporary disk must be a nonnegative integer")
    elif temp > TEMP_LIMIT_BYTES:
        failures.append(f"measurements.{stage}: temporary disk exceeds 100,000,000,000 bytes")
    return dict(value)


def _bound_run_evidence(
    stage: str, record: dict[str, Any] | None, *, input_hash: str | None,
    compressor: dict[str, Any] | None, decompressor: dict[str, Any] | None,
    archive: dict[str, Any] | None, measurement: dict[str, Any] | None,
    failures: list[str],
) -> None:
    if record is None:
        return
    payload = record["payload"]
    required = {"completed": True, "exit_code": 0, "input_sha256": input_hash,
                "input_bytes": ENWIK9_BYTES, "measurement": measurement,
                "compressor_sha256": compressor["sha256"] if compressor else None,
                "decompressor_sha256": decompressor["sha256"] if decompressor else None,
                "archive_sha256": archive["sha256"] if archive else None}
    for key, expected in required.items():
        if payload.get(key) != expected:
            failures.append(f"evidence.{stage}: {key} is absent or not bound to the counted artifact")


def _review_evidence(value: Any, failures: list[str]) -> dict[str, Any] | None:
    record = _json_evidence(value, "evidence.packaging_review", failures)
    if record is None:
        return None
    for key in ("offline_execution_verified", "public_source_access_verified", "osi_license_verified",
                "license_completeness_verified"):
        if record["payload"].get(key) is not True:
            failures.append(f"evidence.packaging_review: {key} is not independently recorded")
    return record


def evaluate(manifest: dict[str, Any], *, verify_input: bool = True) -> dict[str, Any]:
    """Evaluate a manifest and return every failed gate, without assertions."""
    failures: list[str] = []
    if manifest.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    input_path = _path(manifest.get("input", {}).get("path") if isinstance(manifest.get("input"), dict) else None,
                       "input.path", failures)
    input_observation: dict[str, Any] = {}
    if input_path is not None:
        input_observation["path"] = str(input_path)
        input_observation["bytes"] = input_path.stat().st_size
        input_observation["sha256"] = sha256_file(input_path) if verify_input else None
        if input_path.stat().st_size != ENWIK9_BYTES:
            failures.append("input: not exactly 1,000,000,000 bytes")
        if not verify_input:
            failures.append("input: SHA-256 verification was skipped; fail closed")
        elif input_observation["sha256"] != ENWIK9_SHA256:
            failures.append("input: SHA-256 is not canonical enwik9")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
        failures.append("artifacts: missing")
    compressor = _artifact(artifacts.get("compressor"), "artifacts.compressor", failures)
    decompressor = _artifact(artifacts.get("decompressor"), "artifacts.decompressor", failures)
    archive = _artifact(artifacts.get("archive"), "artifacts.archive", failures)
    mode = manifest.get("mode")
    if mode != "split":
        failures.append("mode: only documented split submissions are accepted by this preflight")

    options = manifest.get("required_options")
    if not isinstance(options, list) or not all(isinstance(option, str) for option in options):
        failures.append("required_options: provide every required option as exact UTF-8 text")
        option_bytes = 0
    else:
        option_bytes = sum(len(option.encode("utf-8")) for option in options)
    package_bytes: int | None = None
    multiplier: int | None = None
    if compressor and decompressor and archive:
        # Identical binaries still appear as compressor + one decoder: two copies total.
        multiplier = 1 if compressor["sha256"] == decompressor["sha256"] else 2
        package_bytes = compressor["bytes"] + multiplier * decompressor["bytes"] + archive["bytes"] + option_bytes
        if package_bytes > HURDLE_BYTES:
            failures.append(f"package: {package_bytes} bytes exceeds strict Hutter hurdle {HURDLE_BYTES}")

    measurements = manifest.get("measurements") if isinstance(manifest.get("measurements"), dict) else {}
    compression = _resource("compression", measurements.get("compression"), failures)
    decompression = _resource("decompression", measurements.get("decompression"), failures)

    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), dict) else {}
    encode_evidence = _json_evidence(evidence.get("encode"), "evidence.encode", failures)
    decode_evidence = _json_evidence(evidence.get("decode"), "evidence.decode", failures)
    _bound_run_evidence("encode", encode_evidence, input_hash=input_observation.get("sha256"), compressor=compressor,
                        decompressor=decompressor, archive=archive, measurement=compression, failures=failures)
    _bound_run_evidence("decode", decode_evidence, input_hash=input_observation.get("sha256"), compressor=compressor,
                        decompressor=decompressor, archive=archive, measurement=decompression, failures=failures)
    restored = _artifact(evidence.get("restored"), "evidence.restored", failures)
    if restored is not None:
        if restored["bytes"] != ENWIK9_BYTES or restored["sha256"] != input_observation.get("sha256"):
            failures.append("evidence.restored: does not exactly match the verified canonical input")
        if decode_evidence is not None:
            payload = decode_evidence["payload"]
            if payload.get("restored_sha256") != restored["sha256"] or payload.get("restored_bytes") != restored["bytes"]:
                failures.append("evidence.decode: restored identity is not bound to the restored artifact")

    packaging = manifest.get("packaging") if isinstance(manifest.get("packaging"), dict) else {}
    if packaging.get("offline_self_contained") is not True:
        failures.append("packaging.offline_self_contained must be true")
    if not isinstance(packaging.get("public_source_url"), str) or not packaging["public_source_url"].startswith("https://"):
        failures.append("packaging.public_source_url must be a public HTTPS URL")
    if not isinstance(packaging.get("osi_license"), str) or not packaging["osi_license"].strip():
        failures.append("packaging.osi_license is missing")
    source_root = Path(packaging["source_root"]) if isinstance(packaging.get("source_root"), str) else None
    for field in ("root_license_path", "dependency_license_manifest_path", "usage_document_path", "algorithm_document_path"):
        relative = packaging.get(field)
        candidate = source_root / relative if source_root and isinstance(relative, str) else None
        if candidate is None or not candidate.is_file():
            failures.append(f"packaging.{field}: missing readable evidence file")
    _review_evidence(evidence.get("packaging_review"), failures)

    return {
        "schema_version": 1,
        "status": "LOCAL_ELIGIBILITY_CANDIDATE" if not failures else "NOT_YET_QUALIFIED",
        "official_approval": False,
        "official_approval_note": "Only Hutter Prize reviewers can approve a submission.",
        "rules": {"rules_url": RULES_URL, "faq_url": FAQ_URL, "record_bytes": CURRENT_RECORD_BYTES,
                  "strict_hurdle_bytes": HURDLE_BYTES, "ram_limit_bytes": RAM_LIMIT_BYTES,
                  "temp_limit_bytes": TEMP_LIMIT_BYTES},
        "input_observation": input_observation,
        "package": {"formula": "compressor + (1 if same SHA-256 else 2) * decompressor + archive + UTF-8 required option bytes",
                    "decoder_multiplier": multiplier, "required_option_bytes": option_bytes, "total_bytes": package_bytes},
        "measurements": {"compression": compression, "decompression": decompression},
        "evidence_hashes": {"encode": encode_evidence["sha256"] if encode_evidence else None,
                            "decode": decode_evidence["sha256"] if decode_evidence else None,
                            "packaging_review": evidence.get("packaging_review", {}).get("sha256") if isinstance(evidence.get("packaging_review"), dict) else None},
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-input-hash", action="store_true", help="diagnostic only; always reports NOT_YET_QUALIFIED")
    parser.add_argument("--strict", action="store_true", help="return nonzero unless local preflight passes")
    args = parser.parse_args()
    report = evaluate(json.loads(args.manifest.read_text()), verify_input=not args.skip_input_hash)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    return 0 if not args.strict or report["status"] == "LOCAL_ELIGIBILITY_CANDIDATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
