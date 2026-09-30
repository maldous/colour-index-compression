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

from benchmarks import hutter_structure as d1
from benchmarks import markup_columns
from benchmarks.hutter_structure_columns import _decode_columns, _page_counts, _parts, _slot_classes, extract_columns


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


def _merge_size(spans: list[tuple[int, int]]) -> int:
    """Return byte coverage of intervals, keeping source byte positions exact."""
    total = end = 0
    for start, stop in sorted(spans):
        if stop <= end:
            continue
        total += stop - max(start, end)
        end = stop
    return total


def _slot_paths(skeleton: bytes) -> list[tuple[bytes, ...]]:
    """Recover a placeholder's tag ancestry from D2's exact skeleton bytes."""
    stack: list[bytes] = []
    raw = bytearray()
    paths: list[tuple[bytes, ...]] = []
    position = 0

    def update_raw() -> None:
        for match in d1.TOKEN.finditer(bytes(raw)):
            markup_columns.update_stack(stack, match.group())
        raw.clear()

    while position < len(skeleton):
        byte = skeleton[position]
        position += 1
        if byte:
            raw.append(byte)
            continue
        if position == len(skeleton):
            raise ValueError("truncated D2 skeleton escape")
        kind = skeleton[position]
        position += 1
        if kind == 0:
            raw.append(0)
        elif kind == 1:
            update_raw()
            paths.append(tuple(stack))
        else:
            raise ValueError("invalid D2 skeleton escape")
    return paths


def _page_records(data: bytes) -> list[dict]:
    """Align decoded D2 slots by physical page order, without reserializing XML."""
    descriptor, dictionary, _literal, column_blob, _pages, _literal_records, _slots = _parts(data)
    skeletons = d1._deserialize_skeletons(dictionary)
    columns = _decode_columns(column_blob, skeletons, _page_counts(descriptor, skeletons))
    classes = {identifier: _slot_classes(skeleton, [columns[identifier, slot] for slot in range(d1._placeholder_count(skeleton))])
               for identifier, skeleton in enumerate(skeletons)}
    paths = {identifier: _slot_paths(skeleton) for identifier, skeleton in enumerate(skeletons)}
    seen = Counter()
    result = []
    position = 0
    while position < len(descriptor):
        kind = descriptor[position]
        position += 1
        if kind == 0:
            _size, position = d1.vdecode(descriptor, position)
            continue
        if kind != 1:
            raise ValueError("invalid D2 descriptor kind")
        identifier, position = d1.vdecode(descriptor, position)
        occurrence = seen[identifier]
        seen[identifier] += 1
        values = [columns[identifier, slot][occurrence] for slot in range(d1._placeholder_count(skeletons[identifier]))]
        first = lambda label: next((values[index] for index, value_class in enumerate(classes[identifier]) if value_class == label), b"")
        contributor_ids = [values[index] for index, path in enumerate(paths[identifier])
                           if b"contributor" in path and path[-1:] == (b"id",)]
        contributor_names = [values[index] for index, path in enumerate(paths[identifier])
                             if b"contributor" in path and path[-1:] in ((b"username",), (b"ip",))]
        result.append({"identifier": (identifier, occurrence), "title": first("title"), "body": first("articletext"),
                       "contributor_pairs": list(zip(contributor_ids, contributor_names)),
                       "contributor_paths": [b"/".join(path).decode("ascii", "backslashreplace") for path in paths[identifier]
                                             if b"contributor" in path and path[-1:] in ((b"id",), (b"username",), (b"ip",))]})
    return result


def _body_spans(value: bytes) -> tuple[dict[str, list[tuple[int, int]]], Counter, Counter, list[tuple[bytes, bytes, int, int]], list[tuple[bytes, bytes, int, int]]]:
    """Bounded raw-byte observations, returning positions rather than rewritten text."""
    spans: dict[str, list[tuple[int, int]]] = defaultdict(list)
    domains, field_names = Counter(), Counter()
    for match in TEMPLATE.finditer(value): spans["template_occurrence"].append(match.span())
    fields = list(FIELD.finditer(value))
    infobox = INFOBOX.search(value)
    if infobox and fields:
        spans["infobox_field"].append(infobox.span())
        spans["infobox_field"].extend(match.span() for match in fields)
        field_names.update(match.group(1).strip().lower() for match in fields)
    for match in fields:
        if NUMBER.search(match.group(2)):
            spans["numeric_field"].append(match.span()); field_names.update((match.group(1).strip().lower(),))
    for regex, category in ((TABLE_START, "wikitable"), (TABLE_ROW, "wikitable"), (REDIRECT, "redirect"), (CATEGORY, "category_interlang"), (INTERLANG, "category_interlang"), (REF, "url_citation")):
        spans[category].extend(match.span() for match in regex.finditer(value))
    for match in URL.finditer(value):
        spans["url_citation"].append(match.span()); domains.update((match.group(1),))
    lines, paragraphs = [], []
    start = 0
    for chunk in value.splitlines(keepends=True):
        stop = start + len(chunk)
        raw = chunk.rstrip(b"\r\n")
        if raw and len(raw) <= 512: lines.append((normalized(raw), raw, start, start + len(raw)))
        start = stop
    start = 0
    for chunk in value.split(b"\n\n"):
        stop = start + len(chunk)
        if chunk and len(chunk) <= 1024: paragraphs.append((normalized(chunk), chunk, start, stop))
        start = stop + 2
    return spans, domains, field_names, lines, paragraphs


def profile_region(data: bytes) -> dict:
    # Keep the public D2 adapter in the observation path.  Page-order recovery
    # below only aligns its decoded slots; it does not reserialize XML.
    extracted = extract_columns(data)
    records = _page_records(data)
    memberships: dict[str, set[tuple[int, int]]] = defaultdict(set)
    spans_by_category: dict[str, dict[tuple[int, int], list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
    domain_counts, field_names = Counter(), Counter()
    line_items: list[tuple[tuple[int, int], bytes, bytes, int, int]] = []
    paragraph_items: list[tuple[tuple[int, int], bytes, bytes, int, int]] = []
    title_opening = title_whole = title_opening_bytes = title_whole_bytes = 0
    pair_counts = Counter(); id_to_names: dict[bytes, set[bytes]] = defaultdict(set); contributor_paths = Counter()
    for record in records:
        identifier, body = record["identifier"], record["body"]
        if body:
            local_spans, domains, names, lines, paragraphs = _body_spans(body)
            for category, spans in local_spans.items():
                if spans:
                    memberships[category].add(identifier)
                    spans_by_category[category][identifier].extend(spans)
            domain_counts.update(domains); field_names.update(names)
            line_items.extend((identifier, *item) for item in lines)
            paragraph_items.extend((identifier, *item) for item in paragraphs)
            memberships["xml_wikitext_topology"].add(identifier)
            spans_by_category["xml_wikitext_topology"][identifier].append((0, len(body)))
        title = record["title"]
        if title and body:
            opening = body.split(b"\n\n", 1)[0]
            at = opening.find(title)
            if at >= 0:
                title_opening += 1; title_opening_bytes += len(title)
            at = body.find(title)
            if at >= 0:
                title_whole += 1; title_whole_bytes += len(title)
                memberships["title_reuse"].add(identifier)
                spans_by_category["title_reuse"][identifier].append((at, at + len(title)))
        for pair in record["contributor_pairs"]:
            pair_counts[pair] += 1; id_to_names[pair[0]].add(pair[1])
        contributor_paths.update(record["contributor_paths"])

    def family(name: str, items: list[tuple[tuple[int, int], bytes, bytes, int, int]]) -> dict:
        raw_counts = Counter(raw for _identifier, _norm, raw, _start, _stop in items)
        variants: dict[bytes, set[bytes]] = defaultdict(set)
        for _identifier, norm, raw, _start, _stop in items: variants[norm].add(raw)
        repeated_raw = {raw for raw, count in raw_counts.items() if count >= 2}
        variable_norms = {norm for norm, raws in variants.items() if len(raws) >= 2}
        exact_members = variable_members = 0
        exact_spans: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        variable_spans: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for identifier, norm, raw, start, stop in items:
            if raw in repeated_raw:
                exact_members += 1; memberships[name].add(identifier); spans_by_category[name][identifier].append((start, stop)); exact_spans[identifier].append((start, stop))
            if norm in variable_norms:
                variable_members += 1; memberships[name].add(identifier); spans_by_category[name][identifier].append((start, stop)); variable_spans[identifier].append((start, stop))
        return {"occurrences": exact_members + variable_members, "distinct_values": len(variants),
                "exact_duplicate_forms": len(repeated_raw), "exact_duplicate_members": exact_members,
                "exact_duplicate_source_bytes": sum(_merge_size(spans) for spans in exact_spans.values()),
                "variable_skeletons": len(variable_norms), "variable_skeleton_members": variable_members,
                "variable_skeleton_source_bytes": sum(_merge_size(spans) for spans in variable_spans.values()),
                "structural_variation": "bounded raw members grouped by link/URL/number-normalized byte skeleton"}

    family_results = {"repeated_line_family": family("repeated_line_family", line_items),
                      "repeated_paragraph_family": family("repeated_paragraph_family", paragraph_items)}
    body_columns = [column for column in extracted["columns"] if column["field_class"] == "articletext"]
    topology = {"skeletoncount": extracted["skeletoncount"], "slotcolumns": extracted["slotcolumns"], "pages": extracted["pages"],
                "literal_exception_bytes": len(extracted["literal_exceptions"]), "articletext_columns": len(body_columns),
                "articletext_occurrences": sum(column["value_count"] for column in body_columns)}
    result = {}
    for name in DEFINITIONS:
        if name in family_results:
            result[name] = {"coverage_body_occurrences": len(memberships[name]), **family_results[name]}
        elif name == "title_reuse":
            result[name] = {"coverage_body_occurrences": len(memberships[name]), "occurrences": title_whole, "distinct_values": None,
                            "opening_body_exact_occurrences": title_opening, "opening_body_exact_bytes": title_opening_bytes,
                            "whole_body_exact_occurrences": title_whole, "whole_body_exact_bytes": title_whole_bytes,
                            "structural_variation": "decoded title bytes searched only in the same decoded page's articletext"}
        elif name == "contributor_pair":
            result[name] = {"coverage_body_occurrences": 0, "occurrences": sum(pair_counts.values()), "distinct_values": len(pair_counts),
                            "repeated_exact_pairs": sum(count for count in pair_counts.values() if count >= 2),
                            "id_to_multiple_username_conflicts": sum(1 for names in id_to_names.values() if len(names) > 1),
                            "source_bytes_covered": sum((len(identifier) + len(username)) * count for (identifier, username), count in pair_counts.items()),
                            "source_byte_scope": "decoded contributor id/username or id/ip slot values, not articletext",
                            "tag_paths": dict(sorted(contributor_paths.items())),
                            "structural_variation": "same-record contributor id/username or id/ip positions, paired in decoded slot order"}
        else:
            source_spans = spans_by_category[name]
            result[name] = {"coverage_body_occurrences": len(memberships[name]),
                            "occurrences": sum(len(spans) for spans in source_spans.values()) if name != "xml_wikitext_topology" else topology["articletext_occurrences"],
                            "distinct_values": len(domain_counts) if name == "url_citation" else len(field_names) if name in ("infobox_field", "numeric_field") else None,
                            "structural_variation": "byte-level bounded detector; see documented definition"}
        result[name].setdefault("source_bytes_covered", sum(_merge_size(spans) for spans in spans_by_category[name].values()))
    # Topology deliberately spans each decoded article body, so including it
    # would make the relation union tautologically cover every body byte.
    body_categories = [name for name in memberships if name not in ("title_reuse", "xml_wikitext_topology")]
    union_members = set().union(*(memberships[name] for name in body_categories)) if body_categories else set()
    union_bytes = sum(_merge_size([span for name in body_categories for span in spans_by_category[name][identifier]]) for identifier in union_members)
    overlaps = {f"{left}|{right}": len(memberships[left] & memberships[right])
                for index, left in enumerate(DEFINITIONS) for right in list(DEFINITIONS)[index + 1:]
                if memberships[left] and memberships[right]}
    return {"topology": topology, "opportunities": result, "coverage_union_body_occurrences": len(union_members),
            "coverage_union_source_bytes": union_bytes, "coverage_overlap_pairs": overlaps,
            "top_domains_counted": len(domain_counts), "top_field_names_counted": len(field_names),
            "profile_note": "Coverage union excludes XML/wikitext topology because that detector intentionally spans every decoded article body. It is exact raw-byte interval coverage over the remaining D2 articletext relations. Title reuse is a separate title-in-same-body query; contributor relations use decoded same-record contributor ID/username pairs."}


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
    result = {"schema": "cix-wikipedia-body-opportunities-v2", "status": "PROFILE_ONLY_NOT_COMPRESSION",
              "input": str(input_path.resolve()), "ranges": [{"offset": offset, "bytes": length} for offset, length in RANGES],
              "holdouts_read": False, "backend": "NONE", "paq": "NOT_RUN", "budget_seconds": budget_seconds,
              "actual_cpu_affinity": sorted(os.sched_getaffinity(0)), "elapsed_seconds": time.monotonic() - started,
              "definitions": DEFINITIONS, "proposed_mechanisms": MECHANISMS,
              "metadata_cost": "NOT_MEASURED", "residual_token_bytes": None, "residual_token_rules": "NOT_MEASURED",
              "incremental_paq_gain": "NOT_MEASURED",
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
