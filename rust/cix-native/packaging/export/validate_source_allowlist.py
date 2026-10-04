#!/usr/bin/env python3
"""Validate a proposed native CIX source-export allowlist without exporting files."""
from __future__ import annotations

import argparse
import json
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any


FULL_ENGINE_PROFILE = "full-engine-rc"
OPTIONAL_PROFILE = "native-core-optional"
SOURCE_MEMBERS_PROFILE = "source-members"


def read_manifest(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "cix-native-source-export-allowlist-v1":
        raise ValueError("unsupported allowlist schema")
    return document


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return has_prefix(path, pattern[:-3])
    return fnmatchcase(path, pattern)


def has_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def source_members(source_root: Path, manifest: dict[str, Any]) -> list[str]:
    allowed = manifest["allowed_globs"]
    excluded_prefixes = manifest["excluded_path_prefixes"]
    excluded_suffixes = tuple(manifest["excluded_suffixes"])
    unexpected: list[str] = []
    selected: list[str] = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source_root).as_posix()
        explicitly_allowed = any(
            not pattern.endswith("/**") and matches(relative, pattern)
            for pattern in allowed
        )
        if any(has_prefix(relative, prefix) for prefix in excluded_prefixes) and not explicitly_allowed:
            continue
        if relative.endswith(excluded_suffixes) and not explicitly_allowed:
            continue
        if any(matches(relative, pattern) for pattern in allowed):
            selected.append(relative)
        else:
            unexpected.append(relative)
    if unexpected:
        raise ValueError("unallowlisted source files: " + ", ".join(unexpected))
    return selected


def validate_dependency_closure(source_root: Path, manifest: dict[str, Any], profile: str) -> str:
    if profile == SOURCE_MEMBERS_PROFILE:
        return "not_checked_source_members_only"
    profiles = manifest["export_profiles"]
    if profile == OPTIONAL_PROFILE:
        return profiles[OPTIONAL_PROFILE]["disposition"]
    if profile != FULL_ENGINE_PROFILE:
        raise ValueError(f"unknown export profile: {profile}")
    receipt = source_root / profiles[FULL_ENGINE_PROFILE]["required_dependency_closure"]
    if not receipt.is_file():
        raise ValueError(f"full-engine RC source export blocked: missing dependency closure receipt: {receipt}")
    closure = json.loads(receipt.read_text(encoding="utf-8"))
    if closure.get("status") != "accepted_full_engine_rc":
        raise ValueError("full-engine RC source export blocked: dependency closure is not accepted_full_engine_rc")
    return "accepted_full_engine_rc"


def validate(source_root: Path, manifest: dict[str, Any], profile: str = SOURCE_MEMBERS_PROFILE) -> dict[str, Any]:
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source root is not a directory: {source_root}")
    expected_root = manifest["source_root"]
    if not source_root.as_posix().endswith(expected_root):
        raise ValueError(f"source root must end with declared {expected_root}: {source_root}")

    required = manifest["required_exact_files"]
    missing_required = [item for item in required if not (source_root / item).is_file()]
    if missing_required:
        raise ValueError(f"required source files missing: {', '.join(missing_required)}")

    closure_status = validate_dependency_closure(source_root, manifest, profile)
    members = source_members(source_root, manifest)
    return {
        "schema": "cix-native-source-export-allowlist-report-v1",
        "status": "validated_source_members_only_not_exported",
        "profile": profile,
        "dependency_closure_status": closure_status,
        "source_root": str(source_root),
        "selected_member_count": len(members),
        "selected_members": members,
        "missing_required": [],
        "unexpected_members": []
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", default=SOURCE_MEMBERS_PROFILE, choices=(SOURCE_MEMBERS_PROFILE, OPTIONAL_PROFILE, FULL_ENGINE_PROFILE))
    parser.add_argument("--report", type=Path, help="optional report destination; no archive is created")
    args = parser.parse_args()
    report = validate(args.source_root, read_manifest(args.manifest), args.profile)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
