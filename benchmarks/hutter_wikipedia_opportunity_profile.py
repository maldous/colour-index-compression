#!/usr/bin/env python3
"""Locate reversible Wikipedia structure in already exposed development ranges.

This is a read-only structural locator.  It neither compresses data nor selects
regions by compressed size.  Every reported byte interval is absolute in the
source supplied to :func:`profile`; counts describe observed byte patterns, not
predicted compression gains or numerical dependencies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from benchmarks import hutter_structure_columns as columns
from benchmarks import hutter_wikipedia_body_lines as body


DEV_RANGES = {0, 100_000_000, 400_000_000}
DEV_LENGTH = 4 * 1024 * 1024
INFOBOX = re.compile(br"\{\{\s*[Ii]nfobox\b")
TABLE = re.compile(br"\{\|")
LINK = re.compile(br"\[\[([^\]\n]{1,512})\]\]")
URL = body.URL
REDIRECT = re.compile(br"<redirect\s+[^>]*?/?>", re.I)
TAG_PATTERNS = {
    "title": re.compile(br"<title>(.*?)</title>", re.S),
    "timestamp": re.compile(br"<timestamp>(.*?)</timestamp>", re.S),
    "id_tag": re.compile(br"<id>(.*?)</id>", re.S),
    "username": re.compile(br"<username>(.*?)</username>", re.S),
    "ip": re.compile(br"<ip>(.*?)</ip>", re.S),
}


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ranges(matches, absolute_offset: int, *, group: int = 0) -> list[dict[str, int]]:
    return [{"start": absolute_offset + match.start(group), "end": absolute_offset + match.end(group)} for match in matches]


def _variation(values: list[bytes]) -> dict:
    distinct = len(set(values))
    lengths = [len(value) for value in values]
    return {
        "count": len(values),
        "distinct": distinct,
        "repeated_occurrences": len(values) - distinct,
        "value_bytes": sum(lengths),
        "min_value_bytes": min(lengths) if lengths else 0,
        "max_value_bytes": max(lengths) if lengths else 0,
    }


def _interval_stats(groups: dict[str, list[dict[str, int]]]) -> dict:
    intervals = [(item["start"], item["end"]) for values in groups.values() for item in values if item["end"] > item["start"]]
    occurrence_bytes = sum(end - start for start, end in intervals)
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    union = sum(end - start for start, end in merged)
    return {
        "interval_occurrences": len(intervals),
        "occurrence_bytes": occurrence_bytes,
        "union_bytes": union,
        "overlap_bytes": occurrence_bytes - union,
        "merged_range_count": len(merged),
    }


def _column_summary(data: bytes) -> dict:
    """Use the existing D2 discovery without assigning a post-PAQ benefit."""
    exposed = columns.extract_columns(data)
    by_class: dict[str, dict] = {}
    for row in exposed["columns"]:
        field = row["field_class"]
        target = by_class.setdefault(field, {"value_count": 0, "distinct_values": set(), "value_bytes": 0,
                                               "repeated_occurrences_within_column": 0,
                                               "eligible_short_columns": 0, "column_count": 0})
        values = row["values"]
        target["value_count"] += len(values)
        target["distinct_values"].update(values)
        target["value_bytes"] += sum(map(len, values))
        target["repeated_occurrences_within_column"] += row["repeated_occurrences"]
        target["eligible_short_columns"] += int(row["eligible_short_field"])
        target["column_count"] += 1
    result = []
    for field, row in sorted(by_class.items()):
        unique = row.pop("distinct_values")
        row["field_class"] = field
        row["distinct_values"] = len(unique)
        row["repeated_occurrences_within_class"] = row["value_count"] - len(unique)
        result.append(row)
    return {"complete_pages": exposed["pages"], "skeleton_count": exposed["skeletoncount"],
            "slot_column_count": exposed["slotcolumns"], "field_classes": result,
            "note": "D2 discovery gives raw structural field counts only; it does not establish a PAQ or numeric-model gain."}


def profile(data: bytes, absolute_offset: int) -> dict:
    """Return exact structural evidence for ``data`` at an absolute source offset."""
    if absolute_offset < 0:
        raise ValueError("absolute_offset must be nonnegative")
    body_families, _unused = body._select(data)
    body_rows, body_ranges = [], []
    for skeleton, members in body_families:
        ranges = [{"start": absolute_offset + start, "end": absolute_offset + stop} for start, stop, *_rest in members]
        body_ranges.extend(ranges)
        hole_values = [hole for _start, _stop, _body, _raw, holes in members for hole in holes]
        body_rows.append({"family_sha256": _sha(repr(skeleton).encode()), "member_count": len(members),
                          "body_count": len({member[2] for member in members}), "ranges": ranges,
                          "holes": _variation(hole_values)})

    infobox = list(INFOBOX.finditer(data)); tables = list(TABLE.finditer(data)); redirects = list(REDIRECT.finditer(data))
    links = list(LINK.finditer(data)); urls = list(URL.finditer(data)); numbers = list(body.NUMBER.finditer(data))
    categories = [match for match in links if match.group(1).strip().lower().startswith(b"category:")]
    link_values, url_values, category_values = [m.group(1) for m in links], [m.group() for m in urls], [m.group(1) for m in categories]
    groups = {
        "repeated_body_family_members": body_ranges,
        "infobox_openings": _ranges(infobox, absolute_offset),
        "table_openings": _ranges(tables, absolute_offset),
        "numeric_tokens": _ranges(numbers, absolute_offset),
        "links": _ranges(links, absolute_offset),
        "categories": _ranges(categories, absolute_offset),
        "urls": _ranges(urls, absolute_offset),
        "redirect_metadata": _ranges(redirects, absolute_offset),
    }
    fields = []
    for name, pattern in TAG_PATTERNS.items():
        matches = list(pattern.finditer(data))
        values = [match.group(1) for match in matches]
        ranges = _ranges(matches, absolute_offset, group=1)
        groups["field_" + name] = ranges
        fields.append({"field": name, **_variation(values), "value_ranges": ranges})
    return {
        "schema": 1,
        "provenance": {
            "script_sha256": _sha(Path(__file__).read_bytes()),
            "absolute_offset": absolute_offset,
            "input_bytes": len(data),
            "input_sha256": _sha(data),
            "config": {"body_rule_set": body.RULES.decode(), "infobox_pattern": "{{Infobox", "table_pattern": "{|",
                       "numeric_pattern": body.NUMBER.pattern.decode(), "development_range_selection": "pre-exposed only; no compression-size selection"},
        },
        "body_line_families": {"family_count": len(body_rows), "member_count": len(body_ranges), "families": body_rows,
                               "note": "Only complete <text> bodies and existing body-line eligibility are included."},
        "markup_locations": {
            "infobox": {**_variation([m.group() for m in infobox]), "ranges": groups["infobox_openings"]},
            "table": {**_variation([m.group() for m in tables]), "ranges": groups["table_openings"]},
            "redirect_metadata": {**_variation([m.group() for m in redirects]), "ranges": groups["redirect_metadata"]},
        },
        "references_topology": {
            "links": {**_variation(link_values), "ranges": groups["links"]},
            "categories": {**_variation(category_values), "ranges": groups["categories"]},
            "urls": {**_variation(url_values), "ranges": groups["urls"]},
            "note": "Counts identify repeated target/value opportunities only; no graph or compression benefit is inferred."},
        "numeric_evidence": {**_variation([m.group() for m in numbers]), "ranges": groups["numeric_tokens"],
                            "note": "Raw token locations; no numerical correlation or predictor claim is made."},
        "field_dictionary_repetition": {"tag_fields": fields, "d2_complete_page_columns": _column_summary(data)},
        "union_and_overlap": _interval_stats(groups),
        "location_scope": "All ranges are absolute source byte offsets within this already exposed development region. Overlap is byte-interval overlap, not an additive compression estimate.",
    }


def compact_locations(result: dict, max_per_class: int = 20) -> dict:
    """Return a publication view with exact counts and representative ranges.

    ``profile`` retains every discovered interval for programmatic follow-up.
    This view keeps the public matrix reviewable: it retains the exact total
    count used by every aggregate and at most ``max_per_class`` ranges for each
    class.  The union/overlap totals were calculated before truncation.
    """
    if max_per_class <= 0:
        raise ValueError("max_per_class must be positive")
    output = json.loads(json.dumps(result))

    def trim(row: dict, key: str) -> None:
        ranges = row.pop(key, [])
        row["exact_location_count"] = len(ranges)
        row["representative_ranges"] = ranges[:max_per_class]

    families = output["body_line_families"].pop("families")
    output["body_line_families"]["exact_family_count"] = len(families)
    output["body_line_families"]["representative_families"] = []
    for family in families[:max_per_class]:
        trim(family, "ranges")
        output["body_line_families"]["representative_families"].append(family)
    for row in output["markup_locations"].values():
        trim(row, "ranges")
    for row in output["references_topology"].values():
        if isinstance(row, dict) and "ranges" in row:
            trim(row, "ranges")
    trim(output["numeric_evidence"], "ranges")
    for field in output["field_dictionary_repetition"]["tag_fields"]:
        trim(field, "value_ranges")
    output["location_detail_policy"] = {
        "exact_counts_and_aggregates": "computed over every detected location",
        "representative_locations_per_class": max_per_class,
        "full_location_enumeration": "available only from rerunning the provenance-pinned profile script on the same exposed range",
    }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--length", type=int, default=DEV_LENGTH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.offset not in DEV_RANGES or args.length != DEV_LENGTH:
        raise ValueError("only existing exposed 4 MiB development ranges 0, 100M, and 400M are allowed")
    with args.input.open("rb") as stream:
        stream.seek(args.offset); data = stream.read(args.length)
    if len(data) != args.length:
        raise ValueError("development range is truncated")
    args.output.write_text(json.dumps(compact_locations(profile(data, args.offset)), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
