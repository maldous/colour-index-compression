#!/usr/bin/env python3
"""Read-only eligibility audit for bounded Wikipedia body and column codecs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks import hutter_wikipedia_body_lines as bodylines
from benchmarks.hutter_structure_columns import extract_columns


RANGES = ((0, 4 * 1024 * 1024), (100_000_000, 4 * 1024 * 1024), (400_000_000, 4 * 1024 * 1024))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "median": None, "max": None, "mean": None}
    return {"count": len(values), "min": min(values), "median": statistics.median(values), "max": max(values),
            "mean": sum(values) / len(values)}


def bodies(data: bytes):
    """Yield complete body bounds and count a trailing incomplete body once."""
    position = body_id = 0
    incomplete = 0
    while True:
        opening = bodylines.TEXT_OPEN.search(data, position)
        if not opening:
            break
        close = data.find(b"</text>", opening.end())
        if close < 0:
            incomplete += len(data) - opening.start()
            break
        yield body_id, opening.end(), close
        body_id += 1
        position = close + len(b"</text>")
    return incomplete


def _families(candidates: list[tuple[int, int, int, bytes, tuple]]) -> tuple[dict, dict[int, str]]:
    grouped: dict[tuple, list[tuple[int, int, int, bytes]]] = defaultdict(list)
    for start, stop, body_id, raw, skeleton in candidates:
        grouped[skeleton].append((start, stop, body_id, raw))
    selected: dict[int, str] = {}
    primary, overlaps = Counter(), Counter()
    selected_sizes, selected_distances = [], []
    for skeleton, members in grouped.items():
        failures = []
        if len(members) < 3: failures.append("family_lt3members")
        if len({member[2] for member in members}) < 2: failures.append("family_lt2bodies")
        if len({member[3] for member in members}) < 2: failures.append("family_lt2distinct_raw")
        if failures:
            primary[failures[0]] += 1
            for failure in failures[1:]: overlaps[f"{failures[0]}|{failure}"] += 1
            continue
        offsets = sorted(member[0] for member in members)
        selected_sizes.extend(member[1] - member[0] for member in members)
        selected_distances.extend(right - left for left, right in zip(offsets, offsets[1:]))
        for start, _stop, _body, _raw in members: selected[start] = "selected"
    return {"candidate_family_count": len(grouped), "selected_family_count": len({key for key, values in grouped.items() if all((len(values) >= 3, len({x[2] for x in values}) >= 2, len({x[3] for x in values}) >= 2))}),
            "primary_family_exclusions": dict(primary), "overlapping_secondary_reasons": dict(overlaps),
            "selected_line_sizes": summary(selected_sizes), "selected_family_distance_bytes": summary(selected_distances)}, selected


def _body_profile(data: bytes, limit: int) -> dict:
    complete_body_bytes = incomplete_boundary_bytes = 0
    counters = Counter()
    candidates: list[tuple[int, int, int, bytes, tuple]] = []
    position = body_id = 0
    while True:
        opening = bodylines.TEXT_OPEN.search(data, position)
        if not opening:
            break
        close = data.find(b"</text>", opening.end())
        if close < 0:
            incomplete_boundary_bytes += len(data) - opening.start(); break
        complete_body_bytes += close - opening.end()
        body = data[opening.end():close]
        at = opening.end()
        for chunk in body.splitlines(keepends=True):
            stop = at + len(chunk)
            if not chunk.endswith(b"\n"):
                counters["unterminated_line_bytes"] += len(chunk); counters["unterminated_lines"] += 1
            else:
                core = chunk.rstrip(b"\r\n")
                if len(core) < 48:
                    counters["line_lt48_bytes"] += len(chunk); counters["line_lt48"] += 1
                elif len(core) > limit:
                    counters["line_gt_limit_bytes"] += len(chunk); counters["line_gt_limit"] += 1
                else:
                    split = bodylines._skeleton(chunk)
                    if split is None:
                        # The precise split keeps no-hole and literal-budget
                        # exclusions distinct, including their rare overlap.
                        token_count = len(list(bodylines.TOKEN.finditer(chunk)))
                        literal = len(chunk) - sum(len(match.group()) for match in bodylines.TOKEN.finditer(chunk))
                        reason = "no_holes" if token_count == 0 else "literal_lt24"
                        counters[reason] += 1; counters[reason + "_bytes"] += len(chunk)
                    else:
                        candidates.append((at, stop, body_id, chunk, split[0]))
            at = stop
        body_id += 1; position = close + len(b"</text>")
    family, selected = _families(candidates)
    selected_bytes = sum(stop - start for start, stop, _body, _raw, _skel in candidates if start in selected)
    return {"line_limit": limit, "complete_body_bytes": complete_body_bytes, "complete_body_count": body_id,
            "incomplete_boundary_excluded_bytes": incomplete_boundary_bytes, "line_policy_exclusions": dict(counters),
            "candidate_line_count": len(candidates), "candidate_line_bytes": sum(stop - start for start, stop, *_ in candidates),
            "selected_source_bytes": selected_bytes, **family,
            "note": "Family exclusions are disjoint by first failed criterion; secondary simultaneous failures are counted separately. Lines excluded by length, termination, missing holes or literal budget never enter a family."}


def _column_profile(data: bytes) -> dict:
    extracted = extract_columns(data)
    all_columns = extracted["columns"]
    nonbody = [column for column in all_columns if column["field_class"] != "articletext"]
    short = [column for column in nonbody if column["eligible_short_field"]]
    palette = [column for column in short if column["distinct_values"] <= 256]
    blocks = [column for column in palette if column["value_count"] >= 4]
    return {"all_raw_columns": len(all_columns), "all_raw_column_table_bytes": sum(column["raw_column_table_bytes"] for column in all_columns),
            "articletext_excluded_columns": len(all_columns) - len(nonbody), "articletext_excluded_raw_column_bytes": sum(column["raw_column_table_bytes"] for column in all_columns if column["field_class"] == "articletext"),
            "nonarticle_raw_columns": len(nonbody), "nonarticle_raw_column_bytes": sum(column["raw_column_table_bytes"] for column in nonbody),
            "value_le_256_columns": len(short), "palette_le_256_columns": len(palette), "count_rank_min4_columns": len(blocks),
            "count_rank_max_block_values": 1024, "count_rank_max_palette": 256, "count_rank_min_values": 4,
            "note": "Raw columns include all exact D2 value tables. Count/rank screening excludes article text, values >256 bytes, palettes >256 and columns with fewer than four values; block processing is bounded to 1,024 values and is not encoded here."}


def profile(data: bytes) -> dict:
    return {"body_512": _body_profile(data, 512), "body_4096_equivalent": _body_profile(data, 4096),
            "body_16384_equivalent": _body_profile(data, 16384), "columns": _column_profile(data),
            "body_codec_never_reaches": ["incomplete <text> boundary material", "unterminated final body lines", "lines shorter than 48 bytes", "lines longer than 512 bytes", "lines without LINK/URL/NUMBER holes", "lines with fewer than 24 literal bytes", "families failing member/body/distinct-raw thresholds", "paragraph structures spanning blank-line boundaries", "arbitrary bounded token sequences not confined to a complete line"],
            "scope_note": "4096/16384 are eligibility-equivalent observations only. No long-line frame was built or encoded."}


def run(input_path: Path, output: Path, budget_seconds: int = 300) -> dict:
    if not 0 < budget_seconds <= 300:
        raise ValueError("audit budget must be 1..300 seconds")
    os.sched_setaffinity(0, {0})
    started = time.monotonic(); regions = []
    with input_path.open("rb") as source:
        for offset, length in RANGES:
            source.seek(offset); data = source.read(length)
            if len(data) != length: raise ValueError("input too short")
            if time.monotonic() - started > budget_seconds: raise TimeoutError("eligibility audit budget exhausted")
            regions.append({"offset": offset, "bytes": length, "sha256": sha_bytes(data), "profile": profile(data)})
    root = Path(__file__).resolve().parents[1]
    result = {"schema": "cix-hutter-wikipedia-eligibility-audit-v1", "status": "READ_ONLY_PROFILE_NOT_COMPRESSION",
              "input": str(input_path.resolve()), "ranges": [{"offset": x, "bytes": y} for x, y in RANGES], "holdouts_read": False,
              "backend": "NONE", "paq": "NOT_RUN", "actual_cpu_affinity": sorted(os.sched_getaffinity(0)), "budget_seconds": budget_seconds,
              "elapsed_seconds": time.monotonic() - started,
              "audit_dependencies_sha256": {str(Path(__file__).relative_to(root)): sha_path(Path(__file__)),
                                              "benchmarks/hutter_wikipedia_body_lines.py": sha_path(root / "benchmarks/hutter_wikipedia_body_lines.py"),
                                              "benchmarks/hutter_structure_columns.py": sha_path(root / "benchmarks/hutter_structure_columns.py")},
              "regions": regions,
              "limitations": ["No encoder, PAQ backend, archive, entropy estimate or compression claim was produced.", "The 4KiB/16KiB rows are static eligibility observations, not codec performance.", "This audit reads only fixed exposed development regions."]}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-seconds", type=int, default=300)
    args = parser.parse_args(); print(json.dumps(run(args.input, args.output, args.budget_seconds), sort_keys=True))


if __name__ == "__main__":
    main()
