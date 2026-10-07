#!/usr/bin/env python3
"""Read-only consistency checks for the execution planning crosswalk.

This validator deliberately checks planning metadata only.  It does not change
the coordinator ledger, accept an RC row, or run a build, test, or benchmark.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLANNING_SCHEMA = "cix.execution-dependency-blockers.v1"
COORDINATOR_SCHEMA = "cix-cross-session-requirements-v1"
ALLOWED_EXTERNAL_STARTS = {"separate_user_resume"}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def require_list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return []
    return value


def require_id_list(value: Any, label: str, errors: list[str]) -> list[str]:
    entries = require_list(value, label, errors)
    if not all(isinstance(entry, str) and entry for entry in entries):
        errors.append(f"{label} must contain non-empty string IDs")
        return []
    return entries


def add_edge(
    graph: dict[str, set[str]], source: str, prerequisite: str
) -> None:
    # A prerequisite must precede its dependent.  The direction makes cycle
    # diagnostics read in execution order, while preserving cycle detection.
    graph.setdefault(prerequisite, set()).add(source)
    graph.setdefault(source, set())


def find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    trail: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        trail.append(node)
        for next_node in sorted(graph[node]):
            if state.get(next_node, 0) == 1:
                start = trail.index(next_node)
                return trail[start:] + [next_node]
            if state.get(next_node, 0) == 0:
                cycle = visit(next_node)
                if cycle:
                    return cycle
        trail.pop()
        state[node] = 2
        return None

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            cycle = visit(node)
            if cycle:
                return cycle
    return None


def validate(planning: dict[str, Any], coordinator: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if planning.get("schema") != PLANNING_SCHEMA:
        errors.append(f"unexpected planning schema: {planning.get('schema')!r}")
    if coordinator.get("schema") != COORDINATOR_SCHEMA:
        errors.append(f"unexpected coordinator schema: {coordinator.get('schema')!r}")

    stages = require_list(planning.get("stages"), "stages", errors)
    requirements = require_list(planning.get("requirements"), "requirements", errors)
    investigations = require_list(
        planning.get("additional_investigations"), "additional_investigations", errors
    )
    obligations = require_list(
        planning.get("owned_external_obligation_nodes"),
        "owned_external_obligation_nodes",
        errors,
    )

    def indexed(items: list[Any], label: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append(f"{label} contains an item without a string id")
                continue
            item_id = item["id"]
            if item_id in result:
                errors.append(f"duplicate {label} id: {item_id}")
            result[item_id] = item
        return result

    stage_by_id = indexed(stages, "stage")
    requirement_by_id = indexed(requirements, "requirement")
    investigation_by_id = indexed(investigations, "investigation")
    obligation_by_id = indexed(obligations, "owned external obligation")

    known = set(stage_by_id) | set(requirement_by_id) | set(investigation_by_id) | set(obligation_by_id)
    if len(known) != (
        len(stage_by_id) + len(requirement_by_id) + len(investigation_by_id) + len(obligation_by_id)
    ):
        errors.append("stage, requirement, investigation and obligation IDs must be globally unique")

    # Cohort members are collapsed to their stage before construction edges are
    # checked.  Acceptance backedges remain outside this graph by design.
    cohort_member_to_stage: dict[str, str] = {}
    for stage_id, stage in stage_by_id.items():
        mode = stage.get("execution_mode")
        if mode is not None and mode not in {
            "coordinated_construction_cohort",
            "construction_then_coordinated_acceptance",
        }:
            errors.append(f"stage {stage_id} has unknown execution_mode {mode!r}")
        if mode == "coordinated_construction_cohort":
            for member in require_id_list(stage.get("members"), f"stage {stage_id}.members", errors):
                if member in cohort_member_to_stage:
                    errors.append(f"cohort member {member} occurs in multiple construction cohorts")
                cohort_member_to_stage[member] = stage_id

    def collapsed(node: str) -> str:
        return cohort_member_to_stage.get(node, node)

    graph: dict[str, set[str]] = {collapsed(node): set() for node in known}
    # Keep raw pairs for the semantic check below.  Collapsing a cohort is
    # correct for scheduling-cycle detection, but it may merge two distinct
    # members: one can consume a construction input while another returns it
    # as final acceptance evidence.  That is not an acceptance edge being
    # treated as a start edge.
    raw_construction_pairs: set[tuple[str, str]] = set()
    raw_acceptance_pairs: set[tuple[str, str]] = set()

    def collect_edges(item_id: str, item: dict[str, Any], label: str) -> None:
        source = collapsed(item_id)
        graph.setdefault(source, set())
        for prerequisite in require_id_list(
            item.get("planning_prerequisite_edges", item.get("construction_prerequisite_edges", [])),
            f"{label} {item_id} construction edges",
            errors,
        ):
            if prerequisite not in known and prerequisite not in ALLOWED_EXTERNAL_STARTS:
                errors.append(f"{label} {item_id} has unknown construction edge {prerequisite}")
                continue
            target = collapsed(prerequisite)
            if target == source:
                continue
            raw_construction_pairs.add((item_id, prerequisite))
            add_edge(graph, source, target)
        for backedge in require_id_list(item.get("acceptance_backedges", []), f"{label} {item_id} acceptance backedges", errors):
            if backedge not in known:
                errors.append(f"{label} {item_id} has unknown acceptance backedge {backedge}")
                continue
            raw_acceptance_pairs.add((item_id, backedge))

    for stage_id, stage in stage_by_id.items():
        source = collapsed(stage_id)
        graph.setdefault(source, set())
        for prerequisite in require_id_list(stage.get("entry_edges", []), f"stage {stage_id} entry edges", errors):
            if prerequisite not in known and prerequisite not in ALLOWED_EXTERNAL_STARTS:
                errors.append(f"stage {stage_id} has unknown entry edge {prerequisite}")
                continue
            target = collapsed(prerequisite)
            if target != source:
                raw_construction_pairs.add((stage_id, prerequisite))
                add_edge(graph, source, target)
        for backedge in require_id_list(stage.get("acceptance_backedges", []), f"stage {stage_id} acceptance backedges", errors):
            if backedge not in known:
                errors.append(f"stage {stage_id} has unknown acceptance backedge {backedge}")
                continue
            raw_acceptance_pairs.add((stage_id, backedge))

    for item_id, item in requirement_by_id.items():
        collect_edges(item_id, item, "requirement")
    for item_id, item in investigation_by_id.items():
        collect_edges(item_id, item, "investigation")
    for item_id, item in obligation_by_id.items():
        collect_edges(item_id, item, "owned external obligation")

    overlap = raw_construction_pairs & raw_acceptance_pairs
    if overlap:
        pairs = ", ".join(f"{source}->{target}" for source, target in sorted(overlap))
        errors.append(f"acceptance backedges were also used as construction starts: {pairs}")

    cycle = find_cycle(graph)
    if cycle:
        errors.append("construction graph cycle after cohort collapse: " + " -> ".join(cycle))

    coordinator_required = require_id_list(
        coordinator.get("pre_benchmark_prerequisites"),
        "coordinator pre_benchmark_prerequisites",
        errors,
    )
    coordinator_obligations = require_id_list(
        coordinator.get("pre_benchmark_external_obligations"),
        "coordinator pre_benchmark_external_obligations",
        errors,
    )
    rc51 = requirement_by_id.get("RC51")
    if rc51 is None:
        errors.append("planning requirements omit RC51")
    else:
        expected = coordinator_required + coordinator_obligations
        actual = require_id_list(
            rc51.get("planning_prerequisite_edges"),
            "RC51 planning_prerequisite_edges",
            errors,
        )
        if actual != expected:
            errors.append(
                "RC51 prerequisites drift from coordinator order/content: "
                f"expected {expected!r}, got {actual!r}"
            )

    coordinator_obligation_by_id = indexed(
        require_list(coordinator.get("external_obligations"), "coordinator external_obligations", errors),
        "coordinator external obligation",
    )
    if set(obligation_by_id) != set(coordinator_obligations):
        errors.append(
            "local owned external obligation IDs drift from coordinator pre-benchmark obligations: "
            f"expected {sorted(coordinator_obligations)!r}, got {sorted(obligation_by_id)!r}"
        )
    for obligation_id in coordinator_obligations:
        local = obligation_by_id.get(obligation_id)
        canonical = coordinator_obligation_by_id.get(obligation_id)
        if local is None or canonical is None:
            continue
        for field, local_field in (("parent", "parent"), ("dependent_ids", "dependent_ids"), ("requirement", "promise"), ("status", "status")):
            if local.get(local_field) != canonical.get(field):
                errors.append(
                    f"{obligation_id} {local_field} drifts from coordinator {field}: "
                    f"expected {canonical.get(field)!r}, got {local.get(local_field)!r}"
                )
        if not isinstance(local.get("owner"), str) or not local["owner"]:
            errors.append(f"{obligation_id} requires an explicit planning owner")
        if not isinstance(local.get("evidence_target"), str) or not local["evidence_target"]:
            errors.append(f"{obligation_id} requires an explicit evidence target")

    return errors


def main() -> int:
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--planning",
        type=Path,
        default=script.parent.parent / "dependency-blockers.json",
        help="execution planning crosswalk JSON",
    )
    parser.add_argument(
        "--coordinator",
        type=Path,
        default=script.parent.parent.parent / "2026-10-04-rc-reconciliation" / "requirements.json",
        help="authoritative coordinator requirements JSON",
    )
    args = parser.parse_args()
    try:
        errors = validate(read_json(args.planning), read_json(args.coordinator))
    except ValueError as exc:
        print(f"planning graph validation failed: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("planning graph validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("planning graph validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
