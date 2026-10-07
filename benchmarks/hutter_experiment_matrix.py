"""Pure, bounded Hutter experiment-matrix planning and result qualification.

The model deliberately records an absent result as absent.  It does not turn a
size rejection, an unfinished run, a different backend, or a targeted sample
into a promotion candidate.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from benchmarks.hutter_opportunity_inputs import CLASSES as OPPORTUNITY_CLASSES


INPUT_CLASSES = ("representative", "body_skeleton_rich", "infobox_table_rich", "redirect_metadata_rich", "targeted_discovery", "withheld")
REPRESENTATIONS = ("original", "typed_streams", "aligned_columns", "page_skeletons", "body_skeletons")
MECHANISMS = ("none", "dictionary", "count_feedback", "arithmetic_order", "rank_order", "numeric_prediction", "title_link_reference", "structural_prediction")
SCALES = ("correctness", "dev4MiB", "dev16MiB", "bounded_larger")
BACKENDS = ("PAQv216-4", "PAQv216-higher", "alternative_backend")
CONTEXTS = ("reset_empty", "preserve_within_contiguous")
STATUSES = ("QUEUED", "NOT_IMPLEMENTED", "BLOCKED_DEPENDENCY", "INAPPLICABLE", "HOLDOUT_RESERVED", "COMPLETE", "SIZEREJ", "VERIFIED_SCREENING", "SIZE_REJECTED_UNVERIFIED")
EVIDENCE_STRATA = ("synthetic", "targeted_real", "representative_development", "untouched_holdout")
SYNTHETIC_STRENGTHS = ("strong", "weak", "absent")


@dataclass(frozen=True)
class MatrixCell:
    cell_id: str
    input_class: str
    representation: str
    mechanism: str
    scale: str
    backend: str
    context_reset: str
    status: str
    reason: str
    match_class: str
    opportunity_class: str
    evidence_stratum: str
    strength: str

    def as_dict(self) -> dict:
        return asdict(self)


def _compatible(representation: str, mechanism: str, context: str) -> tuple[bool, str]:
    if representation == "original" and mechanism != "none":
        return False, "original bytes are the matched no-representation control"
    # All non-control combinations remain research possibilities.  A missing
    # logical-symbol adapter or causal reference decoder is a dependency, not
    # evidence that the mechanism is impossible.  Every run starts with empty
    # state; within-input state preservation is separately declared by context.
    return True, ""


def define_matrix(inputs: Mapping[str, object] | None = None) -> list[dict]:
    """Return a practical concrete matrix, including visible non-runnable cells.

    ``inputs`` is accepted for a data registry caller but is intentionally not
    inspected here: this module has no authority to read corpus state.
    """
    del inputs
    plans = [
        ("control-representative", "representative", "original", "none", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("typed-representative", "representative", "typed_streams", "structural_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("columns-representative", "representative", "aligned_columns", "dictionary", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("page-representative", "representative", "page_skeletons", "structural_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("body-representative", "representative", "body_skeletons", "dictionary", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("body-rank-representative", "representative", "body_skeletons", "rank_order", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("columns-rank-representative", "representative", "aligned_columns", "rank_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("columns-count-representative", "representative", "aligned_columns", "count_feedback", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("columns-numeric-representative", "representative", "aligned_columns", "numeric_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("body-link-representative", "representative", "body_skeletons", "title_link_reference", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("body-rich", "body_skeleton_rich", "body_skeletons", "dictionary", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("body-rich-rank", "body_skeleton_rich", "body_skeletons", "rank_order", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("infobox-columns", "infobox_table_rich", "aligned_columns", "dictionary", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("infobox-rank", "infobox_table_rich", "aligned_columns", "rank_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("infobox-numeric", "infobox_table_rich", "aligned_columns", "numeric_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("redirect-pages", "redirect_metadata_rich", "page_skeletons", "dictionary", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("redirect-columns", "redirect_metadata_rich", "aligned_columns", "arithmetic_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("targeted-body", "targeted_discovery", "body_skeletons", "dictionary", "correctness", "PAQv216-4", "preserve_within_contiguous"),
        ("targeted-table", "targeted_discovery", "aligned_columns", "rank_order", "correctness", "PAQv216-4", "reset_empty"),
        ("representative-16m", "representative", "body_skeletons", "dictionary", "dev16MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("representative-larger", "representative", "body_skeletons", "dictionary", "bounded_larger", "PAQv216-4", "preserve_within_contiguous"),
        ("withheld-body", "withheld", "body_skeletons", "dictionary", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("withheld-columns", "withheld", "aligned_columns", "rank_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("higher-not-run", "representative", "body_skeletons", "dictionary", "dev4MiB", "PAQv216-higher", "preserve_within_contiguous"),
        ("alternative-not-run", "representative", "body_skeletons", "dictionary", "dev4MiB", "alternative_backend", "preserve_within_contiguous"),
        # Deliberate incompatibilities keep invalid combinations visible.
        ("invalid-original-rank", "representative", "original", "rank_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("invalid-typed-rank", "representative", "typed_streams", "rank_order", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("invalid-link-reset", "representative", "body_skeletons", "title_link_reference", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("invalid-page-link", "representative", "page_skeletons", "title_link_reference", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("columns-arithmetic", "representative", "aligned_columns", "arithmetic_order", "dev16MiB", "PAQv216-4", "reset_empty"),
        # Synthetic strata discriminate mechanism behavior without being
        # presented as representative corpus performance.
        ("bodylines-synthetic-strong", "body_skeleton_rich", "body_skeletons", "dictionary", "correctness", "PAQv216-4", "reset_empty"),
        ("bodylines-synthetic-weak", "body_skeleton_rich", "body_skeletons", "dictionary", "correctness", "PAQv216-4", "reset_empty"),
        ("bodylines-synthetic-absent", "body_skeleton_rich", "body_skeletons", "dictionary", "correctness", "PAQv216-4", "reset_empty"),
        # The next mechanisms are hypotheses, not runnable queue entries.
        ("body-paragraphs-not-implemented", "body_skeleton_rich", "body_skeletons", "structural_prediction", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
        ("infobox-fields-not-implemented", "infobox_table_rich", "aligned_columns", "dictionary", "dev16MiB", "PAQv216-4", "reset_empty"),
        ("wikitable-fields-not-implemented", "infobox_table_rich", "aligned_columns", "structural_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("numeric-fields-not-implemented", "infobox_table_rich", "aligned_columns", "numeric_prediction", "dev4MiB", "PAQv216-4", "reset_empty"),
        ("title-link-not-implemented", "body_skeleton_rich", "body_skeletons", "title_link_reference", "dev4MiB", "PAQv216-4", "preserve_within_contiguous"),
    ]
    known = {
        ("original", "none"),
        ("aligned_columns", "dictionary"),
        ("aligned_columns", "count_feedback"),
        ("aligned_columns", "rank_order"),
        ("body_skeletons", "dictionary"),
    }
    opportunity = {
        ("original", "none"): "repeated_body_families",
        ("aligned_columns", "dictionary"): "field_dictionary_composition",
        ("aligned_columns", "count_feedback"): "field_dictionary_composition",
        ("aligned_columns", "rank_order"): "field_dictionary_composition",
        ("body_skeletons", "dictionary"): "repeated_body_families",
        ("body_skeletons", "title_link_reference"): "title_link_reuse",
        ("aligned_columns", "numeric_prediction"): "numeric_conditional",
        ("aligned_columns", "arithmetic_order"): "field_dictionary_composition",
        ("body_skeletons", "structural_prediction"): "infobox_table_relations",
    }
    cells = []
    for cell_id, input_class, representation, mechanism, scale, backend, context in plans:
        compatible, reason = _compatible(representation, mechanism, context)
        if cell_id.startswith("bodylines-synthetic-"):
            evidence_stratum, strength = "synthetic", cell_id.rsplit("-", 1)[1]
        elif input_class == "withheld":
            evidence_stratum, strength = "untouched_holdout", "reserved"
        elif input_class == "representative":
            evidence_stratum, strength = "representative_development", "mixed"
        else:
            evidence_stratum, strength = "targeted_real", "observed"
        fallback_opportunity = {
            "body_skeleton_rich": "repeated_body_families", "infobox_table_rich": "infobox_table_relations",
            "redirect_metadata_rich": "redirect_metadata", "targeted_discovery": "category_url_topology",
            "representative": "repeated_body_families", "withheld": "repeated_body_families",
        }[input_class]
        opportunity_class = opportunity.get((representation, mechanism), fallback_opportunity)
        if not compatible:
            # A typed stream may later grow a decoder-reconstructible logical
            # symbol adapter; do not call that research direction impossible.
            # The other explicit combinations contradict this matrix's current
            # representation semantics rather than merely lacking code.
            status = "BLOCKED_DEPENDENCY" if representation == "typed_streams" else "INAPPLICABLE"
        elif input_class == "withheld":
            status, reason = "HOLDOUT_RESERVED", "historically read canonical corpus is withheld from adaptive structural tuning until a promotion gate"
        elif backend != "PAQv216-4":
            status, reason = "BLOCKED_DEPENDENCY", "declared backend alternative is intentionally not run in the pinned comparison"
        elif mechanism in ("arithmetic_order", "rank_order", "count_feedback", "numeric_prediction") and representation in ("typed_streams", "page_skeletons", "body_skeletons"):
            status, reason = "BLOCKED_DEPENDENCY", "requires a decoder-reconstructible aligned logical-symbol adapter"
        elif mechanism == "title_link_reference":
            status, reason = "BLOCKED_DEPENDENCY", "requires a causal title/link reference adapter with exact literal escapes"
        elif (representation, mechanism) not in known:
            status, reason = "NOT_IMPLEMENTED", "hypothesis has no decoder-reconstructible implementation yet; it is not queued runnable work"
        else:
            status, reason = "QUEUED", "requires a predeclared matched physical encode/decode experiment"
        match_class = "targeted" if input_class == "targeted_discovery" else "representative" if input_class == "representative" else input_class
        cells.append(MatrixCell(cell_id, input_class, representation, mechanism, scale, backend, context, status, reason, match_class,
                                opportunity_class, evidence_stratum, strength).as_dict())
    return cells


build_matrix = define_matrix


def opportunity_cells() -> list[dict]:
    """Enumerate the compact 7×5×8×4 opportunity coverage matrix.

    These are planning cells, not receipts and not an execution queue.  A
    supported adapter only means a concrete experiment may later be declared;
    it does not imply data, a result, or a stage promotion.
    """
    supported = {
        ("original", "none"),
        ("typed_streams", "structural_prediction"),
        ("page_skeletons", "structural_prediction"),
        ("aligned_columns", "none"),
        ("aligned_columns", "dictionary"),
        ("aligned_columns", "count_feedback"),
        ("aligned_columns", "rank_order"),
        ("body_skeletons", "dictionary"),
    }
    result = []
    for opportunity_class in OPPORTUNITY_CLASSES:
        for representation in REPRESENTATIONS:
            for mechanism in MECHANISMS:
                for scale in SCALES:
                    if representation == "original" and mechanism != "none":
                        status, reason = "INAPPLICABLE", "original bytes are the no-representation control in this matrix"
                    elif (representation, mechanism) in supported:
                        status, reason = "QUEUED", "adapter exists; a concrete input, budget and matched receipt are still required"
                    elif mechanism in ("arithmetic_order", "rank_order", "count_feedback", "numeric_prediction") and representation in ("typed_streams", "page_skeletons", "body_skeletons"):
                        status, reason = "BLOCKED_DEPENDENCY", "needs a decoder-reconstructible aligned logical-symbol adapter"
                    elif mechanism == "title_link_reference":
                        status, reason = "BLOCKED_DEPENDENCY", "needs causal within-page reference state and exact literal escapes"
                    else:
                        status, reason = "NOT_IMPLEMENTED", "no implementation exists; this cell is coverage, not runnable queued work"
                    result.append(MatrixCell(
                        cell_id=f"{opportunity_class}:{representation}:{mechanism}:{scale}", input_class=opportunity_class,
                        representation=representation, mechanism=mechanism, scale=scale, backend="PAQv216-4",
                        context_reset="empty_initial_preserve_contiguous", status=status, reason=reason,
                        match_class=opportunity_class, opportunity_class=opportunity_class,
                        evidence_stratum="matrix_only", strength="not_assessed").as_dict())
    return result


def import_result_row(receipt: Mapping[str, object], identity: Mapping[str, object]) -> dict:
    """Normalize a saved receipt into a matrix row without inventing evidence.

    The caller supplies immutable experiment identity (candidate/input/backend
    etc.).  A receipt must expose both candidate and matched-control physical
    bytes; otherwise the row remains non-complete and cannot be promoted.
    """
    row = dict(receipt)
    row.update(identity)
    candidate_bytes = receipt.get("physical_bytes", receipt.get("archive_bytes"))
    control_bytes = receipt.get("control_physical_bytes", receipt.get("control_archive_bytes"))
    verification = receipt.get("verification")
    verification_ok = verification in ("PASS", "VERIFIED")
    if isinstance(verification, Mapping):
        verification_ok = (verification.get("verified") is True or verification.get("status") in ("PASS", "VERIFIED", "VERIFIED_SCREENING")
                           or verification.get("sha256_match") is True or verification.get("round_trip") is True)
    verified = receipt.get("verified") is True or verification_ok
    if isinstance(candidate_bytes, int) and isinstance(control_bytes, int):
        row["size_delta_bytes"] = candidate_bytes - control_bytes
    else:
        row["size_delta_bytes"] = None
    row["verified"] = verified
    # Preserve native receipt status verbatim, including screening and
    # unverified size rejections.  The qualifier below decides promotion.
    row["status"] = str(receipt.get("status", "COMPLETE"))
    if row["size_delta_bytes"] is None or not verified:
        row["status"] = "BLOCKED_DEPENDENCY" if row["status"] == "COMPLETE" else row["status"]
    return row


def _expected_for(expected_input_ids: Mapping[str, Iterable[str]] | Iterable[str], match_class: str) -> set[str]:
    if isinstance(expected_input_ids, Mapping):
        return set(expected_input_ids.get(match_class, ()))
    return set(expected_input_ids)


def comparison_group(row: Mapping[str, object]) -> tuple:
    """The smallest group within which a size delta may be compared."""
    return tuple(row.get(name) for name in ("candidate_id", "opportunity_class", "match_class", "evidence_stratum", "strength", "backend", "scale", "context_reset", "control_id"))


def summarize_candidate(rows: Iterable[Mapping[str, object]], expected_input_ids: Mapping[str, Iterable[str]] | Iterable[str]) -> list[dict]:
    """Summarize only fully matched, verified improvements; never promote SIZEREJ.

    A row must include candidate_id, input_id, match_class, backend, scale,
    context_reset, status, verified and size_delta_bytes. A negative delta is a
    smaller physical artifact than the matched control.
    """
    groups: dict[tuple, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        key = comparison_group(row)
        groups[key].append(row)
    summaries = []
    for key, grouped in groups.items():
        candidate_id, opportunity_class, match_class, evidence_stratum, strength, backend, scale, context_reset, control_id = key
        expected_key = (opportunity_class, evidence_stratum, strength, backend, scale, match_class)
        expected = _expected_for(expected_input_ids, expected_key) if isinstance(expected_input_ids, Mapping) and expected_key in expected_input_ids else _expected_for(expected_input_ids, str(match_class))
        completed_statuses = ("COMPLETE", "VERIFIED_SCREENING")
        present = {str(row.get("input_id")) for row in grouped if row.get("status") in completed_statuses}
        missing = sorted(expected - present)
        rejected = [str(row.get("input_id")) for row in grouped if row.get("status") in ("SIZEREJ", "SIZE_REJECTED_UNVERIFIED")]
        invalid = [str(row.get("input_id")) for row in grouped if row.get("status") not in completed_statuses or row.get("verified") is not True]
        gains = [row for row in grouped if row.get("status") in completed_statuses and row.get("verified") is True and isinstance(row.get("size_delta_bytes"), (int, float)) and row["size_delta_bytes"] < 0]
        promotable = bool(expected) and not missing and not invalid and not rejected and len(gains) == len(expected)
        summaries.append({"candidate_id": candidate_id, "opportunity_class": opportunity_class, "match_class": match_class,
                          "evidence_stratum": evidence_stratum, "strength": strength, "backend": backend, "scale": scale,
                          "context_reset": context_reset, "control_id": control_id, "expected_input_ids": sorted(expected),
                          "completed_input_ids": sorted(present), "missing_input_ids": missing, "unverified_or_noncomplete_input_ids": sorted(set(invalid)),
                          "size_rejected_input_ids": sorted(set(rejected)), "verified_gain_input_ids": sorted(str(row.get("input_id")) for row in gains),
                          "total_verified_gain_bytes": int(-sum(row["size_delta_bytes"] for row in gains)), "promotable": promotable,
                          "automatic_stage_promotion": False,
                          "reason": "complete verified gain on every expected matched input; human research review is still required" if promotable else "incomplete, unverified, rejected, non-gaining, or match-class-isolated evidence"})
    return sorted(summaries, key=lambda item: (not item["promotable"], -item["total_verified_gain_bytes"], str(item["candidate_id"])))


def rank_groups(rows: Iterable[Mapping[str, object]], expected_input_ids: Mapping[str, Iterable[str]] | Iterable[str]) -> list[dict]:
    """Rank candidates *within*, never across, identical comparison groups."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for summary in summarize_candidate(rows, expected_input_ids):
        key = tuple(summary.get(name) for name in ("opportunity_class", "match_class", "evidence_stratum", "strength", "backend", "scale", "context_reset", "control_id"))
        groups[key].append(summary)
    result = []
    for key in sorted(groups, key=str):
        candidates = sorted(groups[key], key=lambda item: (not item["promotable"], -item["total_verified_gain_bytes"], str(item["candidate_id"])))
        for rank, candidate in enumerate((item for item in candidates if item["promotable"]), start=1):
            candidate["rank_within_comparison_group"] = rank
        for candidate in candidates:
            candidate.setdefault("rank_within_comparison_group", None)
        result.append({"comparison_group": {name: value for name, value in zip(("opportunity_class", "match_class", "evidence_stratum", "strength", "backend", "scale", "context_reset", "control_id"), key)},
                       "candidates": candidates,
                       "note": "Ranks are meaningful only inside this exact input-stratum/backend/scale/context/control group."})
    return result
