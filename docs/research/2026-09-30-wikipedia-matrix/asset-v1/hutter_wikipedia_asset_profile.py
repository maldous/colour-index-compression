#!/usr/bin/env python3
"""Bounded read-only structural census for canonical enwik9.

The census does not transform or compress input.  It reads the full source only
to compute canonical digests, while reserved ranges are deliberately recorded
as hash-only and receive no structural statistics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import time
from collections import Counter
from pathlib import Path


WINDOW = 4 * 1024 * 1024
RESERVED = ((600_000_000, 664_000_000), (900_000_000, 964_000_000))
MAX_LINE = 16 * 1024
MAX_FAMILIES = 100_000
MAX_WINDOW_FAMILIES = 20_000
NUMBER = re.compile(br"(?<![A-Za-z0-9])[-+]?\d{1,18}(?:\.\d{1,12})?(?![A-Za-z0-9])")
LINK = re.compile(br"\[\[[^\]\n]{1,512}\]\]")
INFOBOX = re.compile(br"\{\{\s*[Ii]nfobox\b")
TABLE = re.compile(br"\{\|")
REDIRECT = re.compile(br"<redirect\s+[^>]*?/?>", re.I)
REDIRECT_TITLE = re.compile(br"^\s*#redirect\s*\[\[([^\]\n]{1,512})\]\]", re.I | re.M)
TITLE = re.compile(br"<title>(.*?)</title>", re.S)


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def reserved(offset: int) -> bool:
    return any(start <= offset < end for start, end in RESERVED)


def normalise_line(value: bytes) -> bytes:
    """Byte-only token normalization used solely for repeat census."""
    return NUMBER.sub(b"<N>", LINK.sub(b"<L>", value))


def _add(counter: Counter, first: dict, last: dict, value: bytes, position: int, cap: int) -> bool:
    if value not in counter and len(counter) >= cap:
        return False
    counter[value] += 1
    first.setdefault(value, position)
    last[value] = position
    return True


def _examples(data: bytes, pattern: re.Pattern[bytes], offset: int, limit: int = 5, group: int = 0) -> list[dict]:
    result = []
    for match in pattern.finditer(data):
        if len(result) == limit:
            break
        value = match.group(group)
        result.append({"start": offset + match.start(group), "end": offset + match.end(group), "sha256": sha(value)})
    return result


def _window(data: bytes, offset: int, global_families: Counter, first: dict, last: dict) -> dict:
    rows = {"offset": offset, "length": len(data), "sha256": sha(data), "status": "PROFILED"}
    rows.update({"page_openings": data.count(b"<page>"), "page_closings": data.count(b"</page>"),
                 "paragraph_markers": data.count(b"\n\n"), "infobox_openings": len(INFOBOX.findall(data)),
                 "table_openings": len(TABLE.findall(data)), "redirect_xml_metadata": len(REDIRECT.findall(data)),
                 "redirect_title_directives": len(REDIRECT_TITLE.findall(data)),
                 "title_count": len(TITLE.findall(data)), "link_count": len(LINK.findall(data)),
                 "numeric_token_count": len(NUMBER.findall(data))})
    rows["examples"] = {"infobox": _examples(data, INFOBOX, offset), "table": _examples(data, TABLE, offset),
                         "redirect_xml": _examples(data, REDIRECT, offset), "redirect_title": _examples(data, REDIRECT_TITLE, offset, group=1),
                         "title": _examples(data, TITLE, offset, group=1)}
    local, local_first, local_last = Counter(), {}, {}
    skipped_long = local_capped = global_capped = long_paragraphs = 0
    in_text = False
    cursor = 0
    for line in data.splitlines(keepends=True):
        line_start = offset + cursor; cursor += len(line)
        if b"<text" in line:
            in_text = True
        if in_text and 64 <= len(line.rstrip(b"\r\n")) <= MAX_LINE:
            normalized = normalise_line(line.rstrip(b"\r\n"))
            if len(line) >= 512:
                long_paragraphs += 1
            if not _add(local, local_first, local_last, normalized, line_start, MAX_WINDOW_FAMILIES):
                local_capped += 1
            if not _add(global_families, first, last, normalized, line_start, MAX_FAMILIES):
                global_capped += 1
        elif in_text and len(line.rstrip(b"\r\n")) > MAX_LINE:
            skipped_long += 1
        if b"</text>" in line:
            in_text = False
    repeated = [(count, value) for value, count in local.items() if count > 1]
    repeated.sort(key=lambda pair: (-pair[0], pair[1]))
    rows["body_line_census"] = {"eligible_lines": sum(local.values()), "distinct_normalized_lines": len(local),
                                "repeated_occurrences": sum(count - 1 for count, _value in repeated),
                                "long_body_lines_ge_512": long_paragraphs, "lines_over_16KiB_skipped": skipped_long,
                                "window_family_cap_exclusions": local_capped, "global_family_cap_exclusions": global_capped,
                                "top_repeated_normalized_families": [{"count": count, "first": local_first[value], "last": local_last[value],
                                                                      "span_bytes": local_last[value] - local_first[value], "sha256": sha(value)}
                                                                     for count, value in repeated[:10]]}
    return rows


def profile_asset(path: Path, *, wall_seconds: int = 300) -> dict:
    """Stream a canonical asset with bounded maps and reserved model-free ranges."""
    started = time.monotonic()
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    families, first, last = Counter(), {}, {}
    windows, offset = [], 0
    with path.open("rb") as stream:
        header = stream.read(1024)
        stream.seek(0)
        while True:
            if time.monotonic() - started > wall_seconds:
                raise TimeoutError("asset profile wall budget exhausted")
            block = stream.read(WINDOW)
            if not block:
                break
            md5.update(block); sha1.update(block); sha256.update(block)
            if reserved(offset):
                windows.append({"offset": offset, "length": len(block), "sha256": sha(block), "status": "RESERVED_HASHED_ONLY",
                                "reason": "holdout reserve: canonical hash only; no structural statistics"})
            else:
                windows.append(_window(block, offset, families, first, last))
            offset += len(block)
    repeated = [(count, value) for value, count in families.items() if count > 1]
    repeated.sort(key=lambda pair: (-pair[0], pair[1]))
    elapsed = time.monotonic() - started
    profiled = [row for row in windows if row["status"] == "PROFILED"]
    def recommendation(metric: str, count: int = 4, nested=None) -> list[dict]:
        def value(row):
            return row[nested][metric] if nested else row[metric]
        return [{"offset": row["offset"], "length": row["length"], "sha256": row["sha256"],
                 "observed_value": value(row), "examples": row.get("examples", {})}
                for row in sorted(profiled, key=lambda row: (-value(row), row["offset"]))[:count]]
    def census_score(row):
        census = row["body_line_census"]
        return (census["repeated_occurrences"] + census["long_body_lines_ge_512"]
                + 10 * (row["infobox_openings"] + row["table_openings"] + row["redirect_title_directives"]))
    return {"schema": 1, "provenance": {"input": str(path.resolve()), "input_bytes": offset,
            "header_bytes": len(header), "header_sha256": sha(header), "script_sha256": sha(Path(__file__).read_bytes()),
            "resource_budget": {"cpu": 2, "wall_seconds": wall_seconds, "memory_bytes": 3_000_000_000, "temp_bytes": 100_000_000,
                                "line_bytes_max": MAX_LINE, "normalized_family_cap": MAX_FAMILIES, "window_family_cap": MAX_WINDOW_FAMILIES},
            "elapsed_seconds": elapsed, "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "temporary_bytes_written": 0, "input_policy": "canonical bytes read unchanged; no format normalization or compression"},
            "canonical_hashes": {"md5": md5.hexdigest(), "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()},
            "reserved_ranges": [{"start": start, "end": end, "policy": "hashed only; structural census skipped"} for start, end in RESERVED],
            "windows": windows,
            "structural_window_recommendations": {
                "eligibility_not_gain": "These deterministic rankings use only observed structural census counts before compression. They are candidate locations, not compression-gain claims.",
                "census_rich": [{"offset": row["offset"], "length": row["length"], "sha256": row["sha256"], "observed_score": census_score(row), "examples": row["examples"]}
                                for row in sorted(profiled, key=lambda row: (-census_score(row), row["offset"]))[:4]],
                "long_body_paragraph": recommendation("long_body_lines_ge_512", nested="body_line_census"),
                "redirect_title": recommendation("redirect_title_directives"),
                "table": recommendation("table_openings")},
            "global_normalized_body_line_repeats": {"tracked_family_count": len(families), "family_cap": MAX_FAMILIES,
                "top": [{"count": count, "first": first[value], "last": last[value], "span_bytes": last[value] - first[value], "sha256": sha(value)}
                        for count, value in repeated[:50]],
                "note": "Normalized NUMBER/LINK repeats are structural census candidates, not compression-gain measurements."}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.wall_seconds <= 300:
        raise ValueError("wall_seconds must be 1..300")
    # This process creates no temporary files and its census maps are capped.
    resource.setrlimit(resource.RLIMIT_AS, (3_000_000_000, 3_000_000_000))
    try:
        os.sched_setaffinity(0, {2})
    except OSError:
        pass  # The recorded CPU request remains visible if host affinity differs.
    args.output.write_text(json.dumps(profile_asset(args.input, wall_seconds=args.wall_seconds), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
