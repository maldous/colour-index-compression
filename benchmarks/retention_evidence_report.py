#!/usr/bin/env python3
"""Generate conservative, reproducible route-retention evidence exports.

This is a reader of frozen collection receipts, never an experiment runner.  It
keeps a route's physical archive, its three full leaf-process timings, trace
identity and matched-control eligibility separate so a partial matrix cannot
turn into a compression claim by accident.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/research/2026-10-01-retention-round-v2/results.json"
BACKEND = ROOT / "docs/research/2026-10-01-backend-retention/results.json"
OUT = ROOT / "docs/research/2026-10-01-retention-audit"
LEGACY_PROFILE = ROOT / "docs/research/2026-09-30-codec-profiles/results.json"
LEGACY_GENERIC = ROOT / "docs/research/2026-09-30-generic-pipeline/results.json"
ROUTES = ("raw", "runs", "composition", "lz", "predictor", "bwt", "stride",
          "phrases", "ppm", "mixture", "deflate")
PROFILES = ("current", "speed", "size")
DIRECT_FIXED_MODEL_ROUTES = {"ppm", "mixture"}


def _execution_signature(original: dict[str, Any]) -> str:
    """Comparable limits, deliberately excluding the leased CPU ordinal."""
    budget = original.get("budget", {})
    configuration = original.get("configuration", {})
    value = {
        "budget": {key: budget.get(key) for key in
                   ("wall_seconds", "max_rss_bytes", "max_temp_bytes", "rss_bytes", "memory_bytes", "temp_bytes", "disk_bytes")
                   if key in budget},
        "measurement": {key: configuration.get(key) for key in
                        ("repetitions", "warmups", "history_bytes", "block_bytes", "offline")
                        if key in configuration},
        # Every bounded receipt leases exactly one physical CPU.  Keep that
        # resource *type/count* comparable without treating CPU 16 and CPU 18
        # as different experimental conditions.
        "cpu_allocation": {"type": "single-pinned-cpu", "count": 1} if "cpu" in budget else None,
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def effective_backend(route: str | None, backend: str | None) -> str | None:
    """Backend which actually writes the route payload, not its CLI label."""
    if route == "composition":
        return "cix"
    if route == "deflate":
        return "deflate"
    if route in DIRECT_FIXED_MODEL_ROUTES:
        return "fixed-arithmetic-model"
    return backend


def comparison_scope(route: str | None) -> str:
    if route == "raw":
        return "raw-self-anchor"
    if route == "runs":
        return "rle-route-cost-vs-unchanged-original"
    if route in DIRECT_FIXED_MODEL_ROUTES:
        return "fixed-context-model-vs-original"
    return "backend-matched-original"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": 1, "status": "MISSING", "rows": []}
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("rows", []), list):
        raise ValueError(f"results file has no rows list: {path}")
    return value


def legacy_references(path: Path, family: str) -> list[dict[str, Any]]:
    """Preserve old receipts as historical references, never as controls."""
    if not path.is_file():
        return []
    value = json.loads(path.read_text())
    if not isinstance(value, list):
        return []
    result = []
    for row in value:
        if not isinstance(row, dict):
            continue
        config = row.get("config", {})
        result.append({"family": family, "cell_id": row.get("cell_id"), "label": row.get("label"),
                       "input_sha256": row.get("input_sha256") or row.get("verification", {}).get("source_sha256"),
                       "original_bytes": row.get("original_bytes"), "archive_bytes": row.get("bytes"),
                       "archive_sha256": row.get("archive_sha256"), "status": row.get("status"),
                       "profile": config.get("profile"), "method": config.get("method") or config.get("mode"),
                       "receipt": row.get("receipt"),
                       "comparison_status": "HISTORICAL_ONLY",
                       "reason": "different frozen implementation/harness/resource provenance; never a current matched control"})
    return result


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _trace_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Rehash the three actual adaptive traces where collection retained them."""
    repetitions = row.get("encode_repetitions", [])
    traces = []
    for repetition in repetitions:
        trace = Path(repetition.get("trace", ""))
        if not trace.is_file():
            traces.append({"index": repetition.get("index"), "status": "MISSING"})
            continue
        content = trace.read_bytes()
        routes = []; failures = []; accounting_total = 54
        for line in content.splitlines():
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                routes.append("INVALID_JSONL")
                continue
            routes.append(block.get("route"))
            # `encode_file` starts from raw bytes without running a raw worker.
            # Charge its identical FRAME descriptor here, otherwise a valid raw
            # selection would falsely fail the minimum assertion.
            complete = [int(block.get("source_bytes", 0)) + 41]
            complete += [trial.get("bytes") for trial in block.get("trials", [])
                        if trial.get("status") == "COMPLETE" and isinstance(trial.get("bytes"), int)]
            selected = block.get("complete_block_bytes")
            accounting_total += selected if isinstance(selected, int) else 0
            if not isinstance(selected, int):
                failures.append("missing complete_block_bytes")
            elif complete and selected != min(complete):
                failures.append(f"selected {selected} != min complete trial {min(complete)}")
            elif not complete and block.get("route") != "raw":
                failures.append("no complete selected trial")
        traces.append({"index": repetition.get("index"), "path": str(trace),
                       "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                       "routes": routes, "selected_route_counts": dict(Counter(routes)),
                       "physical_accounting_bytes": accounting_total,
                       "minimum_selection_assertion": not failures,
                       "minimum_selection_failures": failures,
                       "archive_bytes": repetition.get("bytes"),
                       "archive_accounting_matches": accounting_total == repetition.get("bytes")})
    present = [item for item in traces if item.get("status") != "MISSING"]
    return {"repetitions": traces,
            "complete_three_trace_set": len(repetitions) == 3 and len(present) == 3,
            "stable_trace_hashes": len({item["sha256"] for item in present}) == 1 if present else None,
            "minimum_asserted_all_repetitions": bool(present) and all(
                item["minimum_selection_assertion"] and item["archive_accounting_matches"] for item in present)}


def _physical(row: dict[str, Any]) -> dict[str, Any]:
    """Use receipt size only after checking all retained repetition archives."""
    repetitions = row.get("encode_repetitions", [])
    checks = []
    for rep in repetitions:
        archive = Path(rep.get("archive", ""))
        valid = archive.is_file() and archive.stat().st_size == rep.get("bytes")
        if valid:
            valid = sha256(archive) == rep.get("sha256")
        checks.append({"index": rep.get("index"), "valid": valid,
                       "bytes": rep.get("bytes"), "sha256": rep.get("sha256")})
    primary = next((item for item in repetitions if item.get("index") == 0), None)
    archive_bytes = row.get("archive_bytes")
    valid = (row.get("status") == "VERIFIED_SCREENING" and len(repetitions) == 3
             and all(item["valid"] for item in checks) and primary is not None
             and archive_bytes == primary.get("bytes"))
    return {"archive_bytes": archive_bytes, "archive_sha256": row.get("archive_sha256"),
            "repetition_archives": checks, "physical_primary_verified": valid}


def _timing(row: dict[str, Any], phase: str) -> dict[str, Any]:
    repetitions = row.get(phase + "_repetitions", [])
    values = [item.get("measurement", {}).get("seconds") for item in repetitions]
    values = [float(value) for value in values if isinstance(value, (int, float))]
    # Leaf time includes startup, source/archive I/O, profiling and every trial
    # discarded by selector search.  Never replace it with selected-trial time.
    return {"median_seconds": _median(values), "min_seconds": min(values) if values else None,
            "max_seconds": max(values) if values else None,
            "samples": len(values), "policy": "full leaf command; startup and discarded trials included"}


def _coder_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Read selected accounting, so a backend name never stands in for use."""
    rep = next((item for item in row.get("encode_repetitions", []) if item.get("index") == 0), None)
    if not rep or not Path(rep.get("codec", "")).is_file():
        return {"status": "MISSING"}
    try:
        codec = json.loads(Path(rep["codec"]).read_text())
    except (OSError, json.JSONDecodeError):
        return {"status": "INVALID"}
    coders: Counter[str] = Counter(); blocks = 0
    for block in codec.get("blocks", []):
        blocks += 1
        coders.update(block.get("accounting", {}).get("coders", []))
    return {"status": "MEASURED", "format": codec.get("format"), "selected_blocks": blocks,
            "selected_coders": dict(sorted(coders.items())),
            "contains_exact_rank": any("cix" in name or "count-range" in name for name in coders),
            "contains_count_range": any("count-range" in name for name in coders),
            "contains_deflate": "deflate" in coders,
            "codec_path": rep.get("codec")}


def normalise(source_name: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for original in source.get("rows", []):
        config = original.get("configuration", {})
        profile = {"fast": "speed"}.get(config.get("profile"), config.get("profile"))
        route = config.get("route")
        kind = config.get("kind")
        item = {"source": source_name, "cell_id": original.get("cell_id"),
                "label": original.get("label"), "stage": original.get("matrix_stage"),
                "status": original.get("status"), "profile": profile,
                "effort": config.get("effort"), "kind": kind, "route": route,
                "backend": config.get("backend"), "effective_backend": effective_backend(route, config.get("backend")),
                "comparison_scope": comparison_scope(route), "disable": config.get("disable", []),
                "input_sha256": original.get("verification", {}).get("source_sha256"),
                "budget_signature": _execution_signature(original),
                "failure_class": original.get("failure_class"),
                "failure_reason": original.get("failure_reason"),
                "raw": original}
        item["physical"] = _physical(original)
        item["encode"] = _timing(original, "encode")
        item["decode"] = _timing(original, "decode")
        item["coder_evidence"] = _coder_evidence(original)
        if kind == "adaptive":
            item["adaptive_trace"] = _trace_evidence(original)
        rows.append(item)
    return rows


def control_index(rows: list[dict[str, Any]]) -> dict[tuple, dict[str, Any]]:
    controls: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        if row["status"] != "VERIFIED_SCREENING" or row["kind"] != "original-control":
            continue
        # Backend-retention candidates are allowed to use the frozen baseline
        # original control only when all decoder-relevant input/profile/backend
        # fields match.  The evidence-file name itself is not a codec setting.
        key = (row["label"], row["input_sha256"], row["profile"], row["effort"], row["backend"], row["budget_signature"])
        # The frozen plan has exactly one original control per key.  Keeping an
        # explicit collision marker makes an ambiguous control unavailable.
        controls[key] = row if key not in controls else {"ambiguous": True}
    return controls


def matched_gain(row: dict[str, Any], controls: dict[tuple, dict[str, Any]]) -> dict[str, Any]:
    if row["status"] == "PENDING":
        return {"status": "NOT MEASURED", "reason": "frozen cell has not reached a terminal receipt"}
    if row["status"] != "VERIFIED_SCREENING" or not row["physical"]["physical_primary_verified"]:
        return {"status": "UNQUALIFIED", "reason": row.get("failure_reason") or "attempted cell has no complete three-repetition physical evidence",
                "failure_class": row.get("failure_class")}
    if row["route"] == "raw":
        # Raw is the paid, directly framed self anchor.  It establishes no
        # independent compression gain and therefore must never be compared
        # to a hybrid original stream with different payload semantics.
        return {"status": "MATCHED", "outcome": "TIE", "scope": "raw-self-anchor",
                "control_cell_id": row["cell_id"], "control_bytes": row["physical"]["archive_bytes"],
                "delta_bytes": 0, "delta_percent": 0.0, "improvement_percent": 0.0,
                "reason": "self anchor; not an independent matched gain"}
    # composition and deflate ignore their forced command's backend option, so
    # they match the original encoder that actually uses CIX/deflate.  PPM and
    # mixture are fixed arithmetic models: comparison is useful, but is a
    # context/model result rather than a backend result.
    target_backend = row["effective_backend"] if row["route"] in {"composition", "deflate"} else row["backend"]
    key = (row["label"], row["input_sha256"], row["profile"], row["effort"], target_backend, row["budget_signature"])
    control = controls.get(key)
    if not control:
        return {"status": "UNAVAILABLE", "reason": "no same-profile/same-backend original control"}
    if control.get("ambiguous"):
        return {"status": "UNAVAILABLE", "reason": "ambiguous same-profile/same-backend original control"}
    if not control["physical"]["physical_primary_verified"]:
        return {"status": "UNAVAILABLE", "reason": "original control is not physically qualified"}
    candidate = row["physical"]["archive_bytes"]
    baseline = control["physical"]["archive_bytes"]
    delta = candidate - baseline
    if delta < 0: outcome = "WIN"
    elif delta > 0: outcome = "LOSS"
    else: outcome = "TIE"
    return {"status": "MATCHED", "outcome": outcome, "scope": row["comparison_scope"],
            "control_cell_id": control["cell_id"], "control_bytes": baseline,
            "delta_bytes": delta, "delta_percent": delta * 100 / baseline,
            "improvement_percent": -delta * 100 / baseline}


def matrix(rows: list[dict[str, Any]], controls: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["source"] == "baseline" and row["kind"] == "forced" and row["route"] in ROUTES:
            grouped[(row["label"], row["profile"], row["route"])].append(row)
    output = []
    for label in sorted({row["label"] for row in rows if row["source"] == "baseline" and row["label"]}):
        for profile in PROFILES:
            for route in ROUTES:
                choices = grouped.get((label, profile, route), [])
                # The forced matrix is invoked with hybrid; composition and
                # deflate still record their effective payload backend above.
                chosen = next((row for row in choices if row["backend"] == "hybrid"), None)
                if chosen is None:
                    output.append({"evidence_set": _evidence_set(label, rows), "label": label, "profile": profile, "route": route,
                                   "status": "NOT MEASURED", "reason": "no forced hybrid receipt", "archive_bytes": None})
                else:
                    matched = matched_gain(chosen, controls)
                    status = ("UNQUALIFIED" if matched["status"] == "UNQUALIFIED" else
                              matched.get("outcome", matched["status"]))
                    output.append({"evidence_set": _evidence_set(label, rows), "label": label, "profile": profile, "route": route,
                                   "cell_id": chosen["cell_id"], "status": status,
                                   "archive_bytes": chosen["physical"]["archive_bytes"],
                                   "effective_backend": chosen["effective_backend"],
                                   "selected_coders": chosen["coder_evidence"].get("selected_coders"),
                                   "matched": matched})
    return output


def _evidence_set(label: str, rows: list[dict[str, Any]]) -> str:
    stages = {str(row.get("stage", "")).lower() for row in rows if row.get("label") == label}
    return "fresh-16kib-replication" if any("replication" in stage or "fresh" in stage for stage in stages) else "prior-exposure-development"


def ablation_matrix(rows: list[dict[str, Any]], controls: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    """One removal-ablation cell per profile/slice/route; absent cells stay absent."""
    grouped = {(row["label"], row["profile"], tuple(row["disable"])): row for row in rows
               if row["kind"] == "removal-ablation"}
    output = []
    # Replication was intentionally planned without removal ablations.  Do not
    # manufacture a large fresh "not measured" matrix for cells never proposed.
    labels = sorted({row["label"] for row in rows if row["kind"] == "removal-ablation" and row["label"]})
    for label in labels:
        for profile in PROFILES:
            for route in ROUTES:
                row = grouped.get((label, profile, (route,)))
                if row is None:
                    output.append({"label": label, "profile": profile, "removed_route": route,
                                   "status": "NOT MEASURED", "reason": "no removal-ablation receipt", "archive_bytes": None})
                else:
                    matched = matched_gain(row, controls)
                    adaptive = next((candidate for candidate in rows
                                     if candidate["label"] == label and candidate["profile"] == profile
                                     and candidate["kind"] == "adaptive"), None)
                    if adaptive is None or adaptive["status"] == "PENDING":
                        contribution = {"status": "NOT MEASURED", "reason": "no terminal matched adaptive selector"}
                    elif (adaptive["status"] != "VERIFIED_SCREENING"
                          or not adaptive["physical"]["physical_primary_verified"]):
                        contribution = {"status": "UNQUALIFIED", "reason": "matched adaptive selector is not physically qualified"}
                    elif row["status"] != "VERIFIED_SCREENING" or not row["physical"]["physical_primary_verified"]:
                        contribution = {"status": "UNQUALIFIED", "reason": "removal archive is not physically qualified"}
                    else:
                        delta = row["physical"]["archive_bytes"] - adaptive["physical"]["archive_bytes"]
                        contribution = {"status": "MEASURED", "adaptive_cell_id": adaptive["cell_id"],
                                        "adaptive_bytes": adaptive["physical"]["archive_bytes"],
                                        "removal_minus_adaptive_bytes": delta,
                                        "interpretation": "positive: removed component contributed under this selector; negative: pruning/search-order counterfactual, not a selection defect"}
                    status = contribution["status"]
                    output.append({"label": label, "profile": profile, "removed_route": route,
                                   "cell_id": row["cell_id"], "status": status,
                                   "archive_bytes": row["physical"]["archive_bytes"],
                                   "matched_original_diagnostic": matched,
                                   "removal_contribution": contribution})
    return output


def selected_minimum(rows: list[dict[str, Any]], label: str, profile: str) -> dict[str, Any]:
    """Minimum verified eligible forced route, deliberately excluding wrapper choices."""
    candidates = [row for row in rows if row["label"] == label and row["profile"] == profile
                  and row["kind"] == "forced" and row["route"] in ROUTES
                  and row["backend"] == "hybrid"
                  and row["status"] == "VERIFIED_SCREENING" and row["physical"]["physical_primary_verified"]]
    if not candidates:
        return {"status": "UNAVAILABLE"}
    winner = min(candidates, key=lambda row: row["physical"]["archive_bytes"])
    return {"status": "VERIFIED", "route": winner["route"], "backend": winner["backend"],
            "bytes": winner["physical"]["archive_bytes"], "cell_id": winner["cell_id"]}


def coder_attribution_pairs(rows: list[dict[str, Any]], controls: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    """Matched CIX/count-range *size* pairs; times are expressly non-comparable."""
    grouped: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["kind"] != "forced" or row["route"] not in ROUTES:
            continue
        key = (row["label"], row["input_sha256"], row["profile"], row["effort"], row["route"], row["budget_signature"])
        if row["backend"] in ("cix", "count-range"):
            grouped[key][row["backend"]] = row
    output = []
    for key, pair in sorted(grouped.items()):
        cix, count_range = pair.get("cix"), pair.get("count-range")
        base = {"label": key[0], "input_sha256": key[1], "profile": key[2], "route": key[4]}
        if not cix or not count_range:
            output.append(base | {"status": "NOT MEASURED", "reason": "missing CIX or same-information count-range forced receipt"})
            continue
        if (cix["status"] != "VERIFIED_SCREENING" or count_range["status"] != "VERIFIED_SCREENING"
                or not cix["physical"]["physical_primary_verified"] or not count_range["physical"]["physical_primary_verified"]):
            output.append(base | {"status": "UNQUALIFIED", "reason": "one or both attempted paired archives lack complete verified evidence",
                                  "cix_cell_id": cix["cell_id"], "count_range_cell_id": count_range["cell_id"]})
            continue
        delta = count_range["physical"]["archive_bytes"] - cix["physical"]["archive_bytes"]
        output.append(base | {"status": "MEASURED", "cix_cell_id": cix["cell_id"], "count_range_cell_id": count_range["cell_id"],
                              "cix_bytes": cix["physical"]["archive_bytes"], "count_range_bytes": count_range["physical"]["archive_bytes"],
                              "count_range_minus_cix_bytes": delta,
                              "count_range_minus_cix_percent": delta * 100 / cix["physical"]["archive_bytes"],
                              "cix_transform_benefit": matched_gain(cix, controls),
                              "count_range_transform_benefit": matched_gain(count_range, controls),
                              "cix_coder_usage": cix["coder_evidence"], "count_range_coder_usage": count_range["coder_evidence"],
                              "timing_attribution": "NOT_COMPARABLE: count-range constructs exact rank to reuse identical paid count/alphabet header; do not infer CIX speed from this pair"})
    return output


def portfolio_evidence(backend_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Audit CIXB1 wrappers and portfolio selection without calling them CIX gains."""
    baselines = {row["cell_id"]: row for row in baseline_rows}
    output = []
    for row in backend_rows:
        raw = row["raw"]; config = raw.get("configuration", {})
        base = {"cell_id": row["cell_id"], "label": row["label"], "profile": row["profile"],
                "mode": config.get("mode"), "status": "NOT MEASURED"}
        if config.get("mode") not in {"integrated", "scaling-integrated"}:
            base |= {"status": "NOT APPLICABLE", "reason": "handled by dedicated native-recode, diagnostic, or scaling-baseline evidence view"}; output.append(base); continue
        if row["status"] == "PENDING":
            base["reason"] = "frozen integrated portfolio cell not terminal"; output.append(base); continue
        if row["status"] != "VERIFIED_SCREENING" or not row["physical"]["physical_primary_verified"]:
            base |= {"status": "UNQUALIFIED", "reason": row.get("failure_reason") or "portfolio archive not physically qualified"}; output.append(base); continue
        reports = raw.get("portfolio_reports", [])
        rep_audits = []; all_valid = len(reports) == 3
        selected_bytes = []
        for report in reports:
            attempts = report.get("attempts", []); verified = [item for item in attempts if item.get("status") == "VERIFIED"]
            failures = []
            for attempt in verified:
                for field in ("artifact", "standalone_artifact"):
                    artifact = attempt.get(field, {})
                    path = Path(artifact.get("path", ""))
                    if not path.is_file() or path.stat().st_size != artifact.get("bytes") or sha256(path) != artifact.get("sha256"):
                        failures.append(f"{attempt.get('name')} {field} hash/size mismatch")
            minimum = min((item.get("archive_bytes") for item in verified), default=None)
            selected = report.get("compressed_bytes")
            raw_present = any(item.get("name") == "cix-route:raw" and item.get("status") == "VERIFIED" for item in attempts)
            assertion = selected == minimum and raw_present and not failures
            all_valid &= assertion
            selected_bytes.append(selected)
            rep_audits.append({"selected_bytes": selected, "verified_attempt_count": len(verified),
                               "failed_attempts": [{"name": item.get("name"), "status": item.get("status")} for item in attempts if item.get("status") != "VERIFIED"],
                               "raw_fallback_present": raw_present, "selected_equals_minimum_verified_attempt": selected == minimum,
                               "artifact_hashes_verified": not failures, "failures": failures})
        primary = reports[0] if reports else {}
        attempts = [item for item in primary.get("attempts", []) if item.get("status") == "VERIFIED"]
        external = [item for item in attempts if item.get("kind") == "external"]
        standalone_best = min(external, key=lambda item: item["standalone_artifact"]["bytes"], default=None)
        framed_best = min(external, key=lambda item: item["archive_bytes"], default=None)
        framed_best_all = min(attempts, key=lambda item: item["archive_bytes"], default=None)
        selected = raw.get("selected")
        baseline = baselines.get(raw.get("matched_v2_baseline_cell_id"))
        baseline_match = None
        if baseline and baseline["status"] == "VERIFIED_SCREENING":
            same_limits = all(baseline["raw"].get("budget", {}).get(key) == raw.get("budget", {}).get(key)
                              for key in ("wall_seconds", "max_rss_bytes", "max_temp_bytes"))
            baseline_match = {"cell_id": baseline["cell_id"], "bytes": baseline["physical"]["archive_bytes"],
                              "same_resource_limits": same_limits,
                              "delta_bytes": row["physical"]["archive_bytes"] - baseline["physical"]["archive_bytes"] if same_limits else None,
                              "reason": ("outer resource limits differ; no delta attributed" if not same_limits else
                                         "size profile uses a distinct integrated search budget; any delta is portfolio evidence, not a native-forced-route gain" if row["profile"] == "size" else
                                         "integrated portfolio versus v2 adaptive baseline; not an attribution to a single native route")}
        receipt_assertion = raw.get("minimum_selection_assertion")
        receipt_assertion = receipt_assertion.get("passed") if isinstance(receipt_assertion, dict) else receipt_assertion
        base |= {"status": "MEASURED" if all_valid and receipt_assertion else "UNQUALIFIED",
                 "selected_name": selected, "selected_bytes": row["physical"]["archive_bytes"],
                 "three_repetition_audit": rep_audits,
                 "minimum_selection_assertion_receipt": raw.get("minimum_selection_assertion"),
                 "best_external_standalone": None if not standalone_best else {"name": standalone_best["name"], "bytes": standalone_best["standalone_artifact"]["bytes"], "sha256": standalone_best["standalone_artifact"]["sha256"]},
                 "best_external_framed": None if not framed_best else {"name": framed_best["name"], "bytes": framed_best["archive_bytes"], "sha256": framed_best["archive_sha256"], "wrapper_bytes": framed_best.get("detail", {}).get("wrapper_bytes")},
                 "best_framed_all_verified_candidates": None if not framed_best_all else {"name": framed_best_all["name"], "bytes": framed_best_all["archive_bytes"], "sha256": framed_best_all["archive_sha256"]},
                 "selected_minus_best_framed_all_bytes": None if not framed_best_all else row["physical"]["archive_bytes"] - framed_best_all["archive_bytes"],
                 "selected_minus_best_framed_external_bytes": None if not framed_best else row["physical"]["archive_bytes"] - framed_best["archive_bytes"],
                 "primary_attempt_accounting": [{"name": item.get("name"), "kind": item.get("kind"), "backend": item.get("backend"),
                                                 "route": item.get("route"), "status": item.get("status"), "archive_bytes": item.get("archive_bytes"),
                                                 "standalone_payload_bytes": item.get("detail", {}).get("standalone_payload_bytes", item.get("standalone_artifact", {}).get("bytes")),
                                                 "wrapper_bytes": item.get("detail", {}).get("wrapper_bytes", item.get("standalone_artifact", {}).get("wrapper_bytes")),
                                                 "preset": item.get("detail", {}).get("preset"),
                                                 "native_accounting": item.get("detail", {}).get("accounting"),
                                                 "program_cost_bytes": None,
                                                 "program_cost_note": "runtime/program footprint is not included in archive bytes; no Hutter package claim"}
                                               for item in primary.get("attempts", [])],
                 "matched_v2_baseline": baseline_match,
                 "scope": "portfolio selection among verified eligible candidates; external CIXB1 wrapper and standalone payload remain distinct"}
        output.append(base)
    return output


def _resource_key(row: dict[str, Any]) -> str:
    budget = row["raw"].get("budget", {})
    return json.dumps({key: budget.get(key) for key in ("wall_seconds", "max_rss_bytes", "max_temp_bytes")}, sort_keys=True)


def offline_oracle(backend_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """All completed comparable evidence, intentionally broader than a profile plan."""
    pool: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        if row["status"] != "VERIFIED_SCREENING" or not row["physical"]["physical_primary_verified"]:
            continue
        if row["kind"] not in {"forced", "original-control", "adaptive"}:
            continue
        key = (row["label"], row["input_sha256"], row["profile"], _resource_key(row))
        pool[key].append({"name": f"v2:{row['kind']}:{row['route']}:{row['backend']}", "bytes": row["physical"]["archive_bytes"],
                          "cell_id": row["cell_id"], "source": "v2", "backend": row["backend"], "route": row["route"]})
    output = []
    for row in backend_rows:
        key = (row["label"], row["input_sha256"], row["profile"], _resource_key(row))
        base = {"cell_id": row["cell_id"], "label": row["label"], "profile": row["profile"],
                "status": "NOT MEASURED", "scope": "OFFLINE_ORACLE: all completed comparable candidates, broader than the production profile plan"}
        if row["raw"].get("configuration", {}).get("mode") != "integrated":
            base["reason"] = "diagnostic/recode mode is outside the production integrated portfolio universe"; output.append(base); continue
        if row["status"] == "PENDING":
            base["reason"] = "integrated portfolio not terminal"; output.append(base); continue
        if row["status"] != "VERIFIED_SCREENING" or not row["physical"]["physical_primary_verified"]:
            base |= {"status": "UNQUALIFIED", "reason": row.get("failure_reason") or "integrated portfolio unqualified"}; output.append(base); continue
        candidates = list(pool.get(key, []))
        reports = row["raw"].get("portfolio_reports", [])
        if reports:
            for attempt in reports[0].get("attempts", []):
                if attempt.get("status") == "VERIFIED":
                    candidates.append({"name": f"integrated:{attempt.get('name')}", "bytes": attempt.get("archive_bytes"),
                                       "source": "integrated-plan", "backend": attempt.get("backend"), "route": attempt.get("route")})
        candidates = [candidate for candidate in candidates if isinstance(candidate.get("bytes"), int)]
        if not candidates:
            base |= {"status": "NOT MEASURED", "reason": "no completed comparable candidate"}; output.append(base); continue
        winner = min(candidates, key=lambda candidate: candidate["bytes"])
        selected = row["physical"]["archive_bytes"]
        missing = winner["bytes"] < selected and winner["source"] == "v2" and winner.get("backend") in {"range", "count-range"}
        base |= {"status": "MEASURED", "production_selected_bytes": selected,
                 "offline_oracle_best": winner, "production_minus_oracle_bytes": selected - winner["bytes"],
                 "production_coverage": ("MISSING_AUTOMATIC_STREAM_BACKEND_CONFIGURATION" if missing else
                                         "COVERS_COMPLETED_ORACLE_MINIMUM" if selected == winner["bytes"] else
                                         "BROADER_ORACLE_WIN_NOT_IN_PRODUCTION_PLAN"),
                 "limitations": "CIXM6 and other unmeasured modes are outside this oracle; this is not a global-best claim"}
        output.append(base)
    return output


def targeted_backend_summaries(backend_rows: list[dict[str, Any]]) -> dict[str, Any]:
    recodes = []; diagnostics = []; scaling: dict[tuple, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in backend_rows:
        mode = row["raw"].get("configuration", {}).get("mode")
        if mode == "optional-native-recode":
            reports = row["raw"].get("adaptive_reports", [])
            values = [report.get("optional_native_cix_recode") for report in reports]
            if row["status"] != "VERIFIED_SCREENING" or len(values) != 3 or any(not value for value in values):
                recodes.append({"cell_id": row["cell_id"], "label": row["label"], "profile": row["profile"], "status": "UNQUALIFIED"}); continue
            selected = [value.get("selected_bytes") for value in values]; baseline = [value.get("baseline_bytes") for value in values]; recode = [value.get("recode_bytes") for value in values]
            strict = all(value.get("selected") == "native-cix-recode" for value in values)
            recodes.append({"cell_id": row["cell_id"], "label": row["label"], "profile": row["profile"], "status": "MEASURED",
                            "selected": [value.get("selected") for value in values], "baseline_bytes": baseline, "recode_bytes": recode,
                            "selected_bytes": selected, "native_recode_strict_wins": strict,
                            "native_recode_ties_or_rejections": not strict,
                            "policy": "recode is accepted only when strictly smaller than unchanged candidate; equal/larger recodes are retained as unchanged"})
        elif mode == "fast-shortlist-diagnostic":
            reports = row["raw"].get("diagnostic_reports", [])
            diagnostics.append({"cell_id": row["cell_id"], "label": row["label"], "backend": row["raw"].get("configuration", {}).get("diagnostic_backend"),
                                "status": row["status"], "reports": reports,
                                "scope": "shortlisted-out external backend diagnostic; payload and CIXB1 wrapper remain separate"})
        elif mode in {"scaling-baseline", "scaling-integrated"}:
            scaling[(row["label"], row["profile"])][mode] = row
    recode_counts = Counter("STRICT_WIN" if row.get("native_recode_strict_wins") else "UNCHANGED_OR_REJECTED" for row in recodes if row["status"] == "MEASURED")
    scale_pairs = []
    for (label, profile), pair in sorted(scaling.items()):
        baseline, integrated = pair.get("scaling-baseline"), pair.get("scaling-integrated")
        if not baseline or not integrated or baseline["status"] != "VERIFIED_SCREENING" or integrated["status"] != "VERIFIED_SCREENING":
            scale_pairs.append({"label": label, "profile": profile, "status": "NOT MEASURED", "reason": "requires paired 64 KiB scaling-baseline and scaling-integrated results"}); continue
        scale_pairs.append({"label": label, "profile": profile, "status": "MEASURED", "input_bytes": (baseline["raw"].get("decode_repetitions") or [{}])[0].get("bytes"),
                            "baseline_bytes": baseline["physical"]["archive_bytes"], "integrated_bytes": integrated["physical"]["archive_bytes"],
                            "delta_bytes": integrated["physical"]["archive_bytes"] - baseline["physical"]["archive_bytes"],
                            "scope": "matched 64 KiB backend scaling pair; not a comparison to v2 16 KiB evidence"})
    return {"optional_native_recode": {"rows": recodes, "counts": dict(recode_counts)},
            "fast_shortlist_diagnostics": diagnostics, "scaling_pairs": scale_pairs}


def adaptive_selection(rows: list[dict[str, Any]], label: str, profile: str,
                       forced: dict[str, Any]) -> dict[str, Any]:
    adaptive = next((row for row in rows if row["label"] == label and row["profile"] == profile
                     and row["kind"] == "adaptive" and row["status"] == "VERIFIED_SCREENING"
                     and row["physical"]["physical_primary_verified"]), None)
    if adaptive is None:
        return {"status": "UNAVAILABLE"}
    trace = adaptive.get("adaptive_trace", {})
    if not trace.get("minimum_asserted_all_repetitions"):
        return {"status": "UNQUALIFIED", "cell_id": adaptive["cell_id"],
                "reason": "adaptive traces do not prove selected physical blocks were the complete-attempt minimum",
                "trace": trace}
    selected = adaptive["physical"]["archive_bytes"]
    result = {"status": "VERIFIED", "cell_id": adaptive["cell_id"], "bytes": selected,
              "trace": trace}
    if forced.get("status") == "VERIFIED":
        # Both are complete physical archives.  A negative result means the
        # adaptive search found a candidate not represented by a completed
        # forced cell; it is not a selector-minimum defect.
        result["gap_against_verified_forced_bytes"] = selected - forced["bytes"]
        result["minimum_verified_forced_cell_id"] = forced["cell_id"]
    else:
        result["gap_against_verified_forced_bytes"] = None
    return result


def flat_rows(rows: list[dict[str, Any]], controls: dict[tuple, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        gain = matched_gain(row, controls) if row["kind"] in ("forced", "adaptive", "removal-ablation") else {"status": "NOT_APPLICABLE"}
        result.append({"source": row["source"], "cell_id": row["cell_id"], "label": row["label"],
                       "stage": row["stage"], "profile": row["profile"], "kind": row["kind"],
                       "route": row["route"], "backend": row["backend"], "effective_backend": row["effective_backend"],
                       "comparison_scope": row["comparison_scope"], "status": row["status"],
                       "failure_class": row["failure_class"], "failure_reason": row["failure_reason"],
                       "archive_bytes": row["physical"]["archive_bytes"],
                       "selected_coders": json.dumps(row["coder_evidence"].get("selected_coders"), sort_keys=True),
                       "physical_primary_verified": row["physical"]["physical_primary_verified"],
                       "encode_median_seconds": row["encode"]["median_seconds"],
                       "decode_median_seconds": row["decode"]["median_seconds"],
                       "matched_status": gain["status"], "control_bytes": gain.get("control_bytes"),
                       "delta_bytes": gain.get("delta_bytes"), "delta_percent": gain.get("delta_percent"),
                       "improvement_percent": gain.get("improvement_percent"),
                       "matched_reason": gain.get("reason")})
    return result


def write_report(baseline: Path, backend: Path, output: Path) -> dict[str, Any]:
    baseline_source, backend_source = read_json(baseline), read_json(backend)
    rows = normalise("baseline", baseline_source) + normalise("backend", backend_source)
    baseline_rows = [row for row in rows if row["source"] == "baseline"]
    backend_rows = [row for row in rows if row["source"] == "backend"]
    controls = control_index(rows)
    cells = matrix(rows, controls)
    ablations = ablation_matrix(rows, controls)
    coder_pairs = coder_attribution_pairs(rows, controls)
    portfolios = portfolio_evidence(backend_rows, baseline_rows)
    oracle = offline_oracle(backend_rows, baseline_rows)
    targeted = targeted_backend_summaries(backend_rows)
    selected = []
    for label in sorted({row["label"] for row in rows if row["label"]}):
        for profile in PROFILES:
            forced = selected_minimum(rows, label, profile)
            selected.append({"label": label, "profile": profile, "minimum_verified_forced": forced,
                             "adaptive": adaptive_selection(rows, label, profile, forced)})
    flat = flat_rows(rows, controls)
    historical = legacy_references(LEGACY_PROFILE, "codec-profiles") + legacy_references(LEGACY_GENERIC, "generic-pipeline")
    counts = {"sources": {"baseline": baseline_source.get("status", "COLLECTED"), "backend": backend_source.get("status", "COLLECTED")},
              "rows": len(rows), "status": dict(Counter(row["status"] for row in rows)),
              "failure_class": dict(Counter(row["failure_class"] for row in rows if row["failure_class"])),
              "matched": dict(Counter(row["matched_status"] for row in flat)),
              "matrix": dict(Counter(row["status"] for row in cells))}
    report = {"schema": 1, "purpose": "retention evidence reporting only; never an experiment result generator",
              "input_files": {"baseline": str(baseline), "backend": str(backend)}, "counts": counts,
              "policies": {"physical": "primary repetition archive only after all three retained archives rehash",
                           "timing": "median of three full leaf-process timings; startup, I/O, profiling and discarded trials included",
                           "matched_control": "same source identity, profile, effective backend and resource limits; CPU ordinal is excluded",
                           "route_semantics": {"composition": "compares to CIX original control", "deflate": "compares to deflate original control", "ppm_mixture": "fixed context/model comparison, not backend attribution", "raw": "self anchor; tie is expected", "runs": "route-cost comparison versus unchanged original, not a forced-hybrid claim"},
                           "coder_attribution": "CIX/count-range pairs are matched-information SIZE controls only. Count-range computes exact rank before arithmetic sequence coding, so their timings are not a fair CIX speed comparison. Accounting names actual selected raw/runs/CIX/deflate coders.",
                           "old_references": "not combined with current results; hardware/configuration provenance must remain separate"},
              "rows": rows, "flat_rows": flat, "matrix": cells, "ablation_matrix": ablations,
              "coder_attribution_pairs": coder_pairs,
              "portfolio_evidence": portfolios,
              "offline_oracle": oracle,
              "targeted_backend_summaries": targeted,
              "historical_references": historical,
              "selected_vs_forced": selected}
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    with (output / "matrix.json").open("w") as stream:
        json.dump({"schema": 1, "forced_cells": cells, "ablation_cells": ablations,
                   "forced_by_evidence_set": {name: [cell for cell in cells if cell["evidence_set"] == name]
                                               for name in sorted({cell["evidence_set"] for cell in cells})}}, stream, indent=2, sort_keys=True); stream.write("\n")
    fieldnames = list(flat[0]) if flat else ["source", "cell_id", "label", "stage", "profile", "kind", "route", "backend", "effective_backend", "comparison_scope", "status", "archive_bytes", "physical_primary_verified", "encode_median_seconds", "decode_median_seconds", "matched_status", "control_bytes", "delta_bytes", "delta_percent", "improvement_percent", "matched_reason"]
    with (output / "rows.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator='\n'); writer.writeheader(); writer.writerows(flat)
    lines = ["# Route-retention evidence report", "", "This report is generated only from frozen collection receipts. Missing, failed and unqualified cells remain visible; no historic reference is merged into current-hardware comparisons.", "", "| Status | Count |", "|---|---:|"]
    for name, value in sorted(counts["status"].items()): lines.append(f"| {name} | {value} |")
    lines += ["", "## Route matrices", "", "Each evidence set is separate. A cell status is `WIN`, `TIE`, `LOSS`, `UNQUALIFIED`, or `NOT MEASURED`; the latter includes a stated missing-control reason. Percent deltas use `(candidate − control) / control`, so a smaller archive has a negative delta.", "", "| Evidence set | Input | Profile | Route | Archive bytes | Status | Δ bytes | Δ % |", "|---|---|---|---|---:|---|---:|---:|"]
    for cell in cells:
        matched = cell.get("matched", {}); lines.append(f"| {cell['evidence_set']} | {cell['label']} | {cell['profile']} | {cell['route']} | {cell.get('archive_bytes') if cell.get('archive_bytes') is not None else '—'} | {cell['status']} | {matched.get('delta_bytes', '—')} | {matched.get('delta_percent', '—')} |")
    lines += ["", "Timing uses the median of all three complete leaf encoder/decoder processes. It includes startup, I/O, profiling, and all selector trials, including discarded candidates. Physical sizes include outer framing and all metadata retained in the selected archive.", ""]
    measured_portfolios = [item for item in portfolios if item["status"] == "MEASURED" and item.get("mode") == "integrated"]
    lines += ["## Integrated portfolio before/after", "", "Each row is one frozen integrated CIX portfolio result. The v2 delta has equal outer caps (180 s, 2 GB RSS, 100 MB temporary disk); it is a complete-archive portfolio comparison, not a claim for a particular native route.", "", "| Input | Profile | v2 bytes | Selected bytes | Δ bytes | Selected candidate | Best framed external |", "|---|---|---:|---:|---:|---|---:|"]
    for item in measured_portfolios:
        baseline = item.get("matched_v2_baseline") or {}; framed = item.get("best_external_framed") or {}
        lines.append(f"| {item['label']} | {item['profile']} | {baseline.get('bytes', '—')} | {item['selected_bytes']} | {baseline.get('delta_bytes', '—')} | {item.get('selected_name', '—')} | {framed.get('bytes', '—')} |")
    lines += ["", "The fast profile has a fixed shortlist. Its bzip2/XZ diagnostics are reported separately and are not silently treated as production candidates. The offline oracle records whether a completed wider candidate set beat the integrated plan; CIXM6 remains outside the integrated portfolio universe.", "", "## Optional native recode", "", f"Strict native-recode wins: {targeted['optional_native_recode']['counts'].get('STRICT_WIN', 0)}. Unchanged or rejected recodes: {targeted['optional_native_recode']['counts'].get('UNCHANGED_OR_REJECTED', 0)}. A larger or tied native recode is never selected.", "", "## 64 KiB scaling", "", "| Input | Profile | Baseline bytes | Integrated bytes | Δ bytes |", "|---|---|---:|---:|---:|"]
    lines.insert(lines.index("## Optional native recode") + 2, "Scope: one native recoding pass over each frozen baseline CIXG1 selected archive, not every new external backend archive.")
    for item in targeted["scaling_pairs"]:
        lines.append(f"| {item['label']} | {item['profile']} | {item.get('baseline_bytes', '—')} | {item.get('integrated_bytes', '—')} | {item.get('delta_bytes', '—')} |")
    lines += ["", "## Explicit fast shortlist penalties", "", "All diagnostics restore exactly in three repetitions. The 47-byte wrapper is charged separately; these forced routes are outside the production fast shortlist.", "", "| Input | Omitted backend | Standalone B | Wrapper B | Complete B | Selected fast B | Shortlist penalty B |", "|---|---|---:|---:|---:|---:|---:|"]
    for item in targeted["fast_shortlist_diagnostics"]:
        control = next(p for p in measured_portfolios if p['label'] == item['label'] and p['profile'] == 'speed')
        detail = item['reports'][0]
        selected = control['selected_bytes']; complete = detail['framed_bytes']
        lines.append(f"| {item['label']} | {item['backend']} | {detail['standalone_payload']['bytes']} | {detail['wrapper_bytes']} | {complete} | {selected} | {max(0, selected - complete)} |")
    lines += ["", "## Scope and limits", "", "- Exact reconstruction, archive hashes, three retained repetitions, source-inaccessible decode, and selected-minimum assertions are required for every qualified row.", "- Count-range is a matched-information size control that computes exact rank before arithmetic sequence coding. Its timing is not evidence that CIX is faster than range coding.", "- Historic specialized Silesia results and CIXM6 are not folded into these generic portfolio results. Program/runtime footprint is reported separately and this report is not a Hutter package-size claim.", "- Removal ablations are the 198 already executed v2 diagnostics. No additional targeted-removal counterfactual cells were executed or inferred.", ""]
    (output / "REPORT.md").write_text("\n".join(lines))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--backend", type=Path, default=BACKEND)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    report = write_report(args.baseline, args.backend, args.output)
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
