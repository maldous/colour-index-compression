"""Deterministic, realistic Wikipedia-like inputs for opportunity screening.

These are shared mechanism controls, not corpus substitutes.  Each strength is
generated from the same seed and parameters.  ``absent`` removes the relation
under test while retaining a normal MediaWiki XML container and wikitext.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


CLASSES = (
    "repeated_body_families", "field_dictionary_composition",
    "infobox_table_relations", "numeric_conditional", "title_link_reuse",
    "redirect_metadata", "category_url_topology",
)
STRENGTHS = ("strong", "weak", "absent")
FREQUENCIES = ("uniform", "skewed", "balanced")
VARIATION_TYPES = ("numeric", "entity", "layout", "mixed")


def _normalise(spec: dict) -> dict:
    if not isinstance(spec, dict) or spec.get("opportunity") not in CLASSES:
        raise ValueError("unknown opportunity class")
    result = {
        "opportunity": spec["opportunity"], "strength": spec.get("strength", "strong"),
        "target_bytes": int(spec.get("target_bytes", 49152)),
        "repetition": int(spec.get("repetition", 8)),
        "variation": int(spec.get("variation", 3)),
        "distance": int(spec.get("distance", 5)), "noise": int(spec.get("noise", 2)),
        "dictionary_cardinality": int(spec.get("dictionary_cardinality", 7)),
        "frequency": spec.get("frequency", "uniform"),
        "variation_type": spec.get("variation_type", "mixed"),
        "exception_rate_permille": int(spec.get("exception_rate_permille", 25)),
        "prose_mixture_permille": int(spec.get("prose_mixture_permille", 150)),
        "seed": int(spec.get("seed", 1)),
    }
    if (result["strength"] not in STRENGTHS or result["frequency"] not in FREQUENCIES
            or result["variation_type"] not in VARIATION_TYPES
            or not 32768 <= result["target_bytes"] <= 16 * 1024 * 1024):
        raise ValueError("invalid strength or target_bytes")
    if any(result[x] <= 0 for x in ("repetition", "variation", "distance", "dictionary_cardinality")):
        raise ValueError("invalid opportunity parameters")
    if result["noise"] < 0:
        raise ValueError("invalid noise")
    if not 0 <= result["exception_rate_permille"] <= 1000 or not 0 <= result["prose_mixture_permille"] <= 1000:
        raise ValueError("invalid permille rate")
    return result


def _word(rng: random.Random, length: int = 8) -> str:
    return "".join(chr(97 + rng.randrange(26)) for _ in range(length))


def _family(spec: dict, index: int) -> tuple[int, bool]:
    """Schedule reusable-family bursts separated by actual unrelated records."""
    cycle = spec["repetition"] + spec["distance"]
    block, within = divmod(index, cycle)
    if spec["strength"] == "absent" or within >= spec["repetition"]:
        return index, False
    card = spec["dictionary_cardinality"]
    if spec["frequency"] == "balanced":
        family = block % card
    elif spec["frequency"] == "uniform":
        # Independent deterministic draws give an actual uniform source,
        # unlike the previous balanced round-robin alias.
        family = random.Random((spec["seed"] << 17) ^ block).randrange(card)
    else:
        # Deliberately skewed but still non-degenerate family distribution.
        family = 0 if block % 4 else 1 + (block // 4) % max(1, card - 1)
    return family, True


def _relationship(spec: dict, index: int, scheduled: bool) -> bool:
    if spec["strength"] == "absent" or not scheduled:
        return False
    exception = ((index * 1103515245 + spec["seed"]) % 1000) < spec["exception_rate_permille"]
    # Weak forms have deliberately more independently selected exceptions.
    weak_break = spec["strength"] == "weak" and index % spec["variation"] == 0
    return not exception and not weak_break


def _shape(spec: dict, index: int) -> tuple[int, str, bool]:
    """Return a page family and literal template.

    ``repetition`` is consecutive pages from a family; ``distance`` is a
    causal link/metadata target offset.  It does not alter family run length.
    ``variation`` is the weak-form template count; ``noise`` adds weak-form
    variants and bounds numeric residuals.
    """
    if spec["strength"] == "absent":
        return index, f"unique-literal-{index:06d}", False
    family, scheduled = _family(spec, index)
    if not scheduled:
        return family, f"unrelated-literal-{index:06d}", False
    if spec["strength"] == "strong":
        return family, "fixed-encyclopedia-literal", True
    variants = spec["variation"] * (spec["noise"] + 1)
    if spec["variation_type"] == "numeric":
        return family, f"weak-number-{index % variants:03d}", True
    if spec["variation_type"] == "entity":
        return family, f"weak-entity-{index % variants:03d}", True
    if spec["variation_type"] == "layout":
        return family, f"weak-layout-{index % variants:03d}", True
    return family, f"weak-mixed-{index % variants:03d}", True


def _variation(spec: dict, index: int) -> tuple[str, str]:
    """A paid byte-level variation at every strength, including strong."""
    variant = index % spec["variation"]
    kind = spec["variation_type"]
    if kind == "numeric":
        return f"|revision-code={variant}\n", ""
    if kind == "entity":
        return f"[[District-{variant:03d}]]\n", ""
    if kind == "layout":
        return "{{nowrap|reference}}\n" if variant % 2 else "{{small|reference}}\n", ""
    return f"[[District-{variant:03d}]]\n", f"|revision-code={variant}\n"


def _independent_prose(spec: dict, index: int) -> str:
    """Unrelated natural-looking prose, independently seeded per page."""
    chooser = (index * 2654435761 + spec["seed"]) % 1000
    if chooser >= spec["prose_mixture_permille"]:
        return ""
    rng = random.Random((spec["seed"] << 20) ^ index)
    words = " ".join(_word(rng, 4 + rng.randrange(6)) for _ in range(6 + spec["noise"]))
    return f"This independent editorial note describes {words}.\n"


def _wikitext(spec: dict, index: int, family: int, literal: str, scheduled: bool, rng: random.Random) -> tuple[str, dict]:
    strength, kind = spec["strength"], spec["opportunity"]
    card = spec["dictionary_cardinality"]
    target = (family + 1) % card
    title = f"Town-{family:04d}" if strength != "absent" else f"Entry-{index:06d}"
    related = _relationship(spec, index, scheduled)
    before, after = _variation(spec, index)
    diagnostic: dict[str, object] = {"family": family, "literal": literal, "relationship": related,
                                     "scheduled": scheduled}

    if kind == "repeated_body_families":
        if not related:
            census = f"The {_word(rng)} survey of [[Town-{index:06d}]] recorded {1000 + index} {_word(rng)} residents."
        else:
            census = f"The census of [[Town-{family:04d}]] recorded {1000 + family} residents and {90 + family} homes."
        diagnostic["body_family_key"] = family if related else index
        text = f"'''{title}''' is a settlement.\n{before}{census}\n{literal}\n{after}"
    elif kind == "field_dictionary_composition":
        field = family if related else index
        diagnostic["field_dictionary_key"] = field
        country = field % card if related else field
        text = (f"{{{{Infobox settlement\n|name={title}\n|country=Country-{country:03d}\n"
                f"|type=District-{field if not related else field % 5}\n}}}}\n{before}{literal}\n{after}")
    elif kind == "infobox_table_relations":
        row_target = target if related else (index * 17 + 3)
        diagnostic["table_relation"] = row_target == target
        text = (f"{{{{Infobox town\n|name={title}\n|population={1000 + family}\n|area={10 + family}\n}}}}\n"
                f"{{| class=\"wikitable\"\n|-\n| [[Town-{row_target:04d}]] || County-{row_target % card:03d}\n|}}\n{before}{literal}\n{after}")
    elif kind == "numeric_conditional":
        a, b = 100 + family * 7, 40 + (index % 11)
        residual = rng.randrange(spec["noise"] + 1) if related else 0
        expected = a + b + residual
        total = expected if related else rng.randrange(100000, 200000)
        if not related and total == expected:  # Preserve the absent control deterministically.
            total += 1
        diagnostic.update({"numeric_expected": expected, "numeric_total": total,
                           "numeric_relation": total == expected, "numeric_residual": residual})
        text = (f"{{{{Infobox town\n|name={title}\n|a={a}\n|b={b}\n|residual={residual}\n|total={total}\n}}}}\n"
                f"The documented total is {total}.\n{before}{literal}\n{after}")
    elif kind == "title_link_reuse":
        link = title if related else f"Topic-{index * 13 + 1:06d}"
        diagnostic["title_link_relation"] = link == title
        text = f"'''{title}''' is linked to [[{link}]] and [[Topic-{target:04d}]].\n{before}{literal}\n{after}"
    elif kind == "redirect_metadata":
        redirect_key = target if related else index * 19 + 7
        metadata_key = target if related else index
        diagnostic["redirect_metadata_relation"] = redirect_key == metadata_key
        text = f"#REDIRECT [[Canonical-{redirect_key:04d}]]\n<!-- maintainer=Editor-{metadata_key:04d} -->\n{before}{literal}\n{after}"
    else:
        category = target if related else index
        domain = target if related else index * 23 + 1
        diagnostic["category_url_relation"] = category == domain
        text = (f"'''{title}'''\n[[Category:District-{category:04d}]]\n"
                f"https://district-{domain:04d}.example/wiki/{title}\n{before}{literal}\n{after}")
    prose = _independent_prose(spec, index)
    return title, diagnostic | {"text_bytes": len(text.encode()), "independent_prose": bool(prose)}, text + prose


def _page(spec: dict, index: int, rng: random.Random) -> tuple[bytes, dict]:
    family, literal, scheduled = _shape(spec, index)
    title, diagnostic, text = _wikitext(spec, index, family, literal, scheduled, rng)
    username = f"Editor-{family:04d}" if spec["strength"] != "absent" else f"Editor-{index:06d}"
    page = (
        f"<page><title>{title}</title><id>{100000 + index}</id><revision>"
        f"<id>{200000 + index}</id><timestamp>2020-01-01T00:00:{index % 60:02d}Z</timestamp>"
        f"<contributor><username>{username}</username><id>{300000 + family}</id></contributor>"
        f"<text xml:space=\"preserve\">{text}</text></revision></page>\n"
    ).encode()
    return page, diagnostic | {"title": title, "username": username}


def _realise(spec: dict) -> tuple[bytes, dict]:
    rng = random.Random(spec["seed"])
    opening, closing = b"<mediawiki>\n", b"</mediawiki>\n"
    out = bytearray(opening); rows: list[dict] = []; index = 0
    while True:
        page, row = _page(spec, index, rng)
        if len(out) + len(page) + len(closing) > spec["target_bytes"]:
            break
        out.extend(page); rows.append(row | {"record_sha256": hashlib.sha256(page).hexdigest()}); index += 1
    filler = spec["target_bytes"] - len(out) - len(closing)
    out.extend(b" " * filler); out.extend(closing)
    if len(out) != spec["target_bytes"] or not rows:
        raise AssertionError("exact input size failure")
    literals = [str(row["literal"]) for row in rows]
    scheduled = [row for row in rows if row["scheduled"]]
    family_rows: dict[int, list[dict]] = {}
    for row in scheduled:
        family_rows.setdefault(int(row["family"]), []).append(row)
    related_indices = [index for index, row in enumerate(rows) if row["scheduled"]]
    intervening = [right - left - 1 for left, right in zip(related_indices, related_indices[1:]) if right - left > 1]
    diagnostics = {
        "page_count": len(rows), "filler_bytes": filler,
        "realized_family_cardinality": len({row["family"] for row in rows}),
        "literal_repeat_occurrences": len(literals) - len(set(literals)),
        "realized_literal_variants": len(set(literals)),
        "unique_raw_record_fraction_permille": 1000 * len({row["record_sha256"] for row in rows}) // len(rows),
        "relationship_rows": len(rows),
        "relationship_true_rows": sum(bool(row["relationship"]) for row in rows),
        "independent_prose_rows": sum(bool(row["independent_prose"]) for row in rows),
        "scheduled_family_rows": len(scheduled),
        "realized_family_counts": {str(key): len(value) for key, value in sorted(family_rows.items())},
        "families_with_at_least_three_members": sum(len(value) >= 3 for value in family_rows.values()),
        "families_with_two_distinct_raw_records": sum(
            len({row["record_sha256"] for row in value}) >= 2 for value in family_rows.values()),
        "measured_intervening_unrelated_record_gaps": intervening,
        "parameter_definitions": {
            "repetition": "consecutive pages per reusable family",
            "variation": "weak-form variation cardinality",
            "distance": "family-to-target offset in linked or correlated fields",
            "noise": "maximum numeric residual and weak-form variant multiplier",
            "dictionary_cardinality": "number of reusable page families",
            "frequency": "uniform/balanced round-robin or deterministic skewed family selection",
            "variation_type": "weak-form numeric, entity, layout, or mixed variation",
            "exception_rate_permille": "deterministic relationship exceptions per thousand pages",
            "prose_mixture_permille": "independently generated unrelated prose pages per thousand",
        },
    }
    for relation in ("table_relation", "numeric_relation", "title_link_relation",
                     "redirect_metadata_relation", "category_url_relation"):
        present = [bool(row[relation]) for row in rows if relation in row]
        if present:
            diagnostics[relation + "_true_rows"] = sum(present)
            diagnostics[relation + "_rows"] = len(present)
    return bytes(out), diagnostics


def generate(spec: dict) -> bytes:
    """Materialize one exact-size shared input without any corpus read."""
    return _realise(_normalise(spec))[0]


def default_specs(target_bytes: int = 49152) -> list[dict]:
    if not 32768 <= target_bytes <= 16 * 1024 * 1024:
        raise ValueError("default target must be 32 KiB-16 MiB")
    result = []
    for index, opportunity in enumerate(CLASSES):
        shared_seed = 1000 + 17 * index
        for strength in STRENGTHS:
            result.append({"opportunity": opportunity, "strength": strength, "target_bytes": target_bytes,
                           "repetition": 8, "variation": 3, "distance": 5, "noise": 2,
                           "dictionary_cardinality": 7, "frequency": "uniform", "variation_type": "mixed",
                           "exception_rate_permille": 25, "prose_mixture_permille": 150, "seed": shared_seed})
    return result


def one_factor_sweep_specs(target_bytes: int = 32768) -> list[dict]:
    """Bounded strong-form screening matrix: one controlled change per class.

    The caller may request up to 16 MiB for a staged trial, but this function
    merely returns specifications and never materializes their bytes.
    """
    baseline = {
        "target_bytes": target_bytes, "strength": "strong", "repetition": 8,
        "variation": 3, "distance": 5, "noise": 2, "dictionary_cardinality": 7,
        "frequency": "uniform", "variation_type": "mixed", "exception_rate_permille": 25,
        "prose_mixture_permille": 150,
    }
    factors = {
        "repetition": (1, 16), "distance": (1, 17), "dictionary_cardinality": (2, 31),
        "frequency": ("skewed", "balanced"), "variation": (1, 7),
        "variation_type": ("numeric", "layout"), "noise": (0, 8),
        "exception_rate_permille": (0, 150), "prose_mixture_permille": (0, 500),
        "target_bytes": (65536, 131072),
    }
    output: list[dict] = []
    for index, opportunity in enumerate(CLASSES):
        seed = 7000 + index
        for key, values in factors.items():
            for value in values:
                output.append(baseline | {"opportunity": opportunity, "seed": seed, key: value})
    return output


def provenance(spec: dict) -> dict:
    normal = _normalise(spec)
    data, diagnostics = _realise(normal)
    return {"spec": normal, "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "input_sha256": hashlib.sha256(data).hexdigest(), "input_bytes": len(data),
            "mechanistic_diagnostics": diagnostics}
