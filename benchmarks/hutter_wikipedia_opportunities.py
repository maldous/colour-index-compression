#!/usr/bin/env python3
"""Profile bounded byte-level Wikipedia relations without compressing anything.

The profiler reads only the declared development regions.  It uses D2's exact
page/value extraction as an observation adapter, never as an XML serializer;
all body patterns are deliberately approximate byte regularities, not claims
about semantic XML or a prebuilt corpus model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

from benchmarks.hutter_structure_columns import extract_columns


RANGES = ((0, 4 * 1024 * 1024), (100_000_000, 4 * 1024 * 1024), (400_000_000, 4 * 1024 * 1024))
URL = re.compile(br"https?://([^/\s|}\]<>]+)", re.I)
LINK = re.compile(br"\[\[[^\]\n]{1,512}\]\]")
NUMBER = re.compile(br"(?<![A-Za-z0-9])[-+]?\d{1,18}(?:\.\d{1,12})?(?![A-Za-z0-9])")
TEMPLATE = re.compile(br"\{\{[^{}\n]{1,512}\}\}")
REF = re.compile(br"<ref(?:\s[^<>]{0,256})?>.{0,2048}?</ref\s*>|<ref(?:\s[^<>]{0,256})?/\s*>", re.I | re.S)
FIELD = re.compile(br"(?m)^\s*\|\s*([^=\n|]{1,96})\s*=\s*([^\n]{0,1024})$")
CATEGORY = re.compile(br"\[\[Category:[^\]\n]{1,512}\]\]", re.I)
INTERLANG = re.compile(br"\[\[[a-z]{2,12}(?:-[a-z0-9]{2,12})?:[^\]\n]{1,512}\]\]", re.I)
REDIRECT = re.compile(br"(?im)^\s*#redirect\s*\[\[")
INFOBOX = re.compile(br"\{\{\s*infobox(?:[ _][^\n{|}]{0,128})?", re.I)
TABLE_START = re.compile(br"(?m)^\s*\{\|")
TABLE_ROW = re.compile(br"(?m)^\s*\|-?")

DEFINITIONS = {
    "repeated_line_family": "UTF-8-agnostic byte lines up to 512 bytes normalized by replacing bounded links, URLs and numeric tokens; counts only repeated normalized forms.",
    "repeated_paragraph_family": "Byte paragraphs split on blank lines, at most 1,024 bytes, with the same link/URL/numeric normalization.",
    "template_occurrence": "Non-nested single-line {{...}} byte spans up to 512 bytes; nested/multiline templates are excluded.",
    "infobox_field": "Article text with a byte-level {{Infobox prefix and newline |key=value fields up to the stated bounds; no template parser is assumed.",
    "wikitable": "Lines beginning {| and |- or | by simple byte regex; nested/template table syntax is not interpreted.",
    "numeric_field": "Bounded |key=value lines with at least one decimal-like byte token; relations are only an opportunity, not measured predictability.",
    "title_reuse": "D2 title column values repeated within the same page-skeleton column.",
    "redirect": "Case-insensitive byte lines beginning #REDIRECT followed by [[.",
    "contributor_pair": "Within a D2 skeleton, first title and first contributor slot zipped by page occurrence; no identity resolution or external knowledge.",
    "category_interlang": "Literal [[Category:...]] and bounded language-prefix [[xx:...]] spans.",
    "url_citation": "HTTP(S) domain bytes and bounded <ref>...</ref> or self-closing ref spans.",
    "xml_wikitext_topology": "D2 page skeleton/slot layout plus body marker presence; it does not parse or normalize XML/wikitext.",
}

MECHANISMS = {
    "repeated_line_family": "Bounded line-family dictionary plus exact member/escape stream, selected only after physical framing comparison.",
    "repeated_paragraph_family": "Bounded paragraph skeleton/reference stream with raw exceptions and explicit boundaries.",
    "template_occurrence": "Template terminal/field layout stream with raw nested or multiline exceptions.",
    "infobox_field": "Validated infobox field columns keyed by exact field-name bytes; preserve unknown/nested syntax literally.",
    "wikitable": "Validated row/cell column streams with raw fallback for nested or malformed tables.",
    "numeric_field": "Per-field canonical-number validation followed by causal delta/error stream and raw spelling escapes.",
    "title_reuse": "D2 short title column composition/order coding with a matched arithmetic control and charged counts.",
    "redirect": "Redirect target field stream with a literal fallback for noncanonical syntax.",
    "contributor_pair": "Per-skeleton title/contributor relation model only after matching raw field columns and explicit exception stream.",
    "category_interlang": "Category/language-prefix terminal stream with complete raw link escapes.",
    "url_citation": "Domain/citation layout columns plus raw URL/citation escape payloads.",
    "xml_wikitext_topology": "D2 skeleton-relative field columns; then condition value coder on skeleton/slot class.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(value: bytes) -> bytes:
    value = LINK.sub(b"<LINK>", value)
    value = URL.sub(b"<URL>", value)
    return NUMBER.sub(b"<NUM>", value)


def body_profile(identifier: tuple[int, int, int], value: bytes) -> tuple[dict[str, int], set[str], Counter, Counter, Counter]:
    """Return per-body occurrence counts and category membership only."""
    categories: set[str] = set()
    counts: dict[str, int] = {}
    domains = Counter(URL.findall(value))
    fields = FIELD.findall(value)
    template_count = len(TEMPLATE.findall(value))
    if template_count: categories.add("template_occurrence")
    if INFOBOX.search(value) and fields: categories.add("infobox_field")
    if TABLE_START.search(value) or TABLE_ROW.search(value): categories.add("wikitable")
    if any(NUMBER.search(field_value) for _, field_value in fields): categories.add("numeric_field")
    if REDIRECT.search(value): categories.add("redirect")
    if CATEGORY.search(value) or INTERLANG.search(value): categories.add("category_interlang")
    refs = REF.findall(value)
    if domains or refs: categories.add("url_citation")
    lines = [line for line in value.splitlines() if line and len(line) <= 512]
    paragraphs = [part for part in value.split(b"\n\n") if part and len(part) <= 1024]
    if lines: categories.add("repeated_line_family")
    if paragraphs: categories.add("repeated_paragraph_family")
    counts.update(template_occurrence=template_count, infobox_field=len(fields) if INFOBOX.search(value) else 0,
                  wikitable=int(bool(TABLE_START.search(value) or TABLE_ROW.search(value))),
                  numeric_field=sum(1 for _, field_value in fields if NUMBER.search(field_value)),
                  redirect=int(bool(REDIRECT.search(value))), category_interlang=len(CATEGORY.findall(value)) + len(INTERLANG.findall(value)),
                  url_citation=sum(domains.values()) + len(refs), lines=len(lines), paragraphs=len(paragraphs))
    field_names = Counter(key.strip().lower() for key, _ in fields)
    return counts, categories, domains, field_names, Counter(normalized(line) for line in lines) + Counter(normalized(part) for part in paragraphs)


def profile_region(data: bytes) -> dict:
    extracted = extract_columns(data)
    body_columns = [column for column in extracted["columns"] if column["field_class"] == "articletext"]
    memberships: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
    occurrences = Counter()
    domain_counts = Counter()
    field_names = Counter()
    line_families = Counter()
    paragraph_families = Counter()
    for column in body_columns:
        for index, value in enumerate(column["values"]):
            identifier = (column["skeleton_id"], column["slot_ordinal"], index)
            counts, categories, domains, names, _ = body_profile(identifier, value)
            for category in categories: memberships[category].add(identifier)
            occurrences.update({key: value for key, value in counts.items() if key not in ("lines", "paragraphs")})
            domain_counts.update(domains); field_names.update(names)
            line_families.update(normalized(line) for line in value.splitlines() if line and len(line) <= 512)
            paragraph_families.update(normalized(part) for part in value.split(b"\n\n") if part and len(part) <= 1024)
    topology = {"skeletoncount": extracted["skeletoncount"], "slotcolumns": extracted["slotcolumns"],
                "pages": extracted["pages"], "literal_exception_bytes": len(extracted["literal_exceptions"]),
                "articletext_columns": len(body_columns), "articletext_occurrences": sum(column["value_count"] for column in body_columns)}
    title_columns = [column for column in extracted["columns"] if column["field_class"] == "title"]
    contributor_columns = [column for column in extracted["columns"] if column["field_class"] == "contributor"]
    title_repeat = sum(column["repeated_occurrences"] for column in title_columns)
    pairs = 0
    for skeleton in {column["skeleton_id"] for column in extracted["columns"]}:
        titles = [column for column in title_columns if column["skeleton_id"] == skeleton]
        contributors = [column for column in contributor_columns if column["skeleton_id"] == skeleton]
        if titles and contributors:
            pairs += min(len(titles[0]["values"]), len(contributors[0]["values"]))
    memberships["xml_wikitext_topology"].update((column["skeleton_id"], column["slot_ordinal"], 0) for column in body_columns)
    result = {}
    for name in DEFINITIONS:
        if name == "repeated_line_family":
            repeated = {k: v for k, v in line_families.items() if v >= 2}
            result[name] = {"coverage_body_occurrences": len(memberships[name]), "occurrences": sum(repeated.values()),
                            "distinct_values": len(line_families), "structural_variation": "normalized bounded lines", "repeated_families": len(repeated)}
        elif name == "repeated_paragraph_family":
            repeated = {k: v for k, v in paragraph_families.items() if v >= 2}
            result[name] = {"coverage_body_occurrences": len(memberships[name]), "occurrences": sum(repeated.values()),
                            "distinct_values": len(paragraph_families), "structural_variation": "normalized bounded paragraphs", "repeated_families": len(repeated)}
        else:
            result[name] = {"coverage_body_occurrences": len(memberships[name]), "occurrences": occurrences[name] if name in occurrences else (title_repeat if name == "title_reuse" else pairs if name == "contributor_pair" else topology["articletext_occurrences"] if name == "xml_wikitext_topology" else 0),
                            "distinct_values": len(domain_counts) if name == "url_citation" else len(field_names) if name in ("infobox_field", "numeric_field") else None,
                            "structural_variation": "byte-level bounded detector; see documented definition"}
    # The union has a single well-defined universe: D2 article-text values.
    # Title reuse and contributor pairs are page-column observations and are
    # deliberately reported outside this union.
    union_categories = [name for name in memberships if name not in ("title_reuse", "contributor_pair")]
    union = set().union(*(memberships[name] for name in union_categories)) if union_categories else set()
    overlaps = {f"{left}|{right}": len(memberships[left] & memberships[right])
                for index, left in enumerate(DEFINITIONS) for right in list(DEFINITIONS)[index + 1:]
                if memberships[left] and memberships[right]}
    return {"topology": topology, "opportunities": result,
            "coverage_union_body_occurrences": len(union), "coverage_overlap_pairs": overlaps,
            "top_domains_counted": len(domain_counts), "top_field_names_counted": len(field_names),
            "profile_note": "Coverage union is over D2 articletext field occurrences, not unique pages; title reuse and contributor pairs use page-column occurrences and are excluded from that union. Categories overlap and are not additive."}


def run(input_path: Path, output_path: Path, budget_seconds: float = 30.0) -> dict:
    if not 0 < budget_seconds <= 30:
        raise ValueError("opportunity profile budget must be within 30 seconds")
    os.sched_setaffinity(0, {16, 18})
    started = time.monotonic()
    regions = []
    with input_path.open("rb") as source:
        for offset, length in RANGES:
            source.seek(offset)
            data = source.read(length)
            if len(data) != length:
                raise ValueError("canonical input too short for declared region")
            if time.monotonic() - started > budget_seconds:
                raise TimeoutError("opportunity profile budget exhausted")
            regions.append({"offset": offset, "bytes": length, "sha256": sha(data), "profile": profile_region(data)})
    result = {"schema": "cix-wikipedia-body-opportunities-v1", "status": "PROFILE_ONLY_NOT_COMPRESSION",
              "input": str(input_path.resolve()), "ranges": [{"offset": offset, "bytes": length} for offset, length in RANGES],
              "holdouts_read": False, "backend": "NONE", "paq": "NOT_RUN", "budget_seconds": budget_seconds,
              "actual_cpu_affinity": sorted(os.sched_getaffinity(0)), "elapsed_seconds": time.monotonic() - started,
              "definitions": DEFINITIONS, "proposed_mechanisms": MECHANISMS,
              "metadata_cost": "NOT_MEASURED", "incremental_paq_gain": "NOT_MEASURED",
              "regions": regions,
              "limitations": ["Approximate byte detectors; no XML/wikitext parser or reserialization.", "No compressed asset, entropy estimate, or comparability claim.", "Coverage categories overlap and must not be summed.", "No numeric, relation, title, contributor or text coding was performed."]}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-seconds", type=float, default=30.0)
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, args.budget_seconds), sort_keys=True))


if __name__ == "__main__":
    main()
