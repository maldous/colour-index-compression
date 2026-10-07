#!/usr/bin/env python3
"""Root-scheduled, no-build verification of current GPL-3 PAQ notice staging."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT = Path("/home/user/src/colour-index-compression")
JOB = PROJECT / "docs/research/2026-10-04-execution/jobs/provider-notice-gpl3-v1"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/provider-notice-gpl3-v1"
GPL3_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
MAX_EXPORTED_BYTES = 64 * 1024 * 1024
SOURCE_MEMBER_BASELINE_BYTES = 5_653_711
PRIVATE_MARKERS = (
    "/home/user/",
    "benchmark-work/",
    "docs/research/",
    "colour-index-compression/",
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def file_map(inputs: dict[str, Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, path in inputs.items():
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required regular input missing: {name}: {path}")
        result[name] = digest(path)
    return result


def tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def require_no_private_references(root: Path) -> None:
    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(marker in text for marker in PRIVATE_MARKERS):
            found.append(path.relative_to(root).as_posix())
    if found:
        raise RuntimeError("sanitized export retains private references: " + ", ".join(found))


def verify_exported_members(root: Path, export_manifest: dict[str, Any]) -> None:
    members = export_manifest.get("members_sha256")
    if not isinstance(members, dict) or not members:
        raise RuntimeError("export manifest has no member digest map")
    for relative, expected in members.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeError("export manifest has malformed member digest")
        candidate = root / relative
        if not candidate.is_file() or digest(candidate) != expected:
            raise RuntimeError(f"exported member differs from its frozen identity: {relative}")


def verify_current_paq_sources(
    closure_document: dict[str, Any], source_identity: dict[str, Any]
) -> None:
    roots = closure_document.get("paq_source_roots")
    variants = source_identity.get("variants")
    if not isinstance(roots, dict) or not isinstance(variants, list) or len(variants) != 4:
        raise RuntimeError("PAQ source identity does not cover the four selected variants")
    for variant in variants:
        if not isinstance(variant, dict):
            raise RuntimeError("malformed staged PAQ source identity")
        name = variant.get("variant")
        files = variant.get("files")
        source_entry = roots.get(name) if isinstance(name, str) else None
        if not isinstance(source_entry, dict) or not isinstance(files, dict):
            raise RuntimeError(f"staged PAQ source identity has no source map: {name}")
        source_root = Path(str(source_entry.get("path", "")))
        if not source_root.is_absolute() or not source_root.is_dir():
            raise RuntimeError(f"selected PAQ source root unavailable: {name}")
        for relative, expected in files.items():
            candidate = source_root / str(relative)
            if not candidate.is_file() or digest(candidate) != expected:
                raise RuntimeError(f"selected PAQ source changed after staging: {name}/{relative}")


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    if WORK.exists():
        raise RuntimeError(f"work directory already exists: {WORK}")
    WORK.mkdir(parents=True)

    source_root = PROJECT / "rust/cix-native"
    closure = PROJECT / "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4/selected-provider-closure.json"
    notices = source_root / "packaging/notices/provider-notices.json"
    provenance = source_root / "packaging/notices/provider-provenance-v3.json"
    allowlist = source_root / "packaging/export/source-allowlist.json"
    export_tool = source_root / "packaging/export/export_source.py"
    validation_tool = source_root / "packaging/export/validate_source_allowlist.py"
    notice_tool = source_root / "packaging/export/engineering_export_job.py"
    paq_tool = source_root / "packaging/export/stage_provider_sources.py"
    gpl2 = Path("/usr/share/common-licenses/GPL-2")
    gpl3 = source_root / "packaging/notices/licenses/GPL-3.0.txt"
    inputs = {
        "closure": closure,
        "provider_notices": notices,
        "provider_provenance": provenance,
        "source_allowlist": allowlist,
        "export_tool": export_tool,
        "validation_tool": validation_tool,
        "notice_tool": notice_tool,
        "paq_tool": paq_tool,
        "native_license": source_root / "LICENSE",
        "native_readme": source_root / "README.md",
        "third_party_notices": source_root / "THIRD_PARTY_NOTICES.txt",
        "debian_copyright": source_root / "packaging/debian/copyright",
        "debian_rules": source_root / "packaging/debian/rules",
        "root_export_readme": source_root / "packaging/export/ROOT-README.md.in",
        "staging_input": source_root / "packaging/notices/STAGING-INPUT.md",
        "gpl2_text": gpl2,
        "gpl3_text": gpl3,
        "job_spec": JOB / "spec.json",
        "job_script": JOB / "run.py",
        "python": Path("/usr/bin/python3").resolve(),
    }
    receipt: dict[str, Any] = {
        "schema": "cix-provider-notice-gpl3-verification-v1",
        "status": "failed",
        "scope": "source-candidate notice and source-identity staging only; no build, package, final closure, or release acceptance",
        "export_byte_cap": MAX_EXPORTED_BYTES,
        "source_member_baseline_bytes": SOURCE_MEMBER_BASELINE_BYTES,
    }
    receipt_path = WORK / "receipt.json"
    before: dict[str, str] | None = None
    try:
        before = file_map(inputs)
        receipt["inputs_before_sha256"] = before
        if (source_root / "packaging/export/final-dependency-closure.json").exists():
            raise RuntimeError("this source-candidate job must not use a final dependency closure")
        sys.path.insert(0, str(source_root / "packaging/export"))
        from engineering_export_job import stage_provider_notices

        export = WORK / "export"
        subprocess.run(
            [
                "/usr/bin/python3",
                str(export_tool),
                "--source-root",
                str(source_root),
                "--manifest",
                str(allowlist),
                "--output-directory",
                str(export),
                "--profile",
                "engineering-validation",
            ],
            check=True,
        )
        exported_root = export / "cix-0.1.0"
        identity = stage_provider_notices(closure, notices, exported_root)
        subprocess.run(
            [
                "/usr/bin/python3",
                str(paq_tool),
                "--closure",
                str(closure),
                "--receipt-root",
                str(PROJECT),
                "--export-root",
                str(exported_root),
                "--gpl2-text",
                str(gpl2),
            ],
            check=True,
        )

        closure_document = json.loads(closure.read_text(encoding="utf-8"))
        notice_document = json.loads(notices.read_text(encoding="utf-8"))
        selected = closure_document["providers"]
        if len(selected) != 14 or set(selected) != set(identity["providers"]):
            raise RuntimeError("notice staging did not cover exactly the current fourteen selected providers")
        if identity["unresolved"] != notice_document["unresolved"] or not identity["unresolved"]:
            raise RuntimeError("notice staging changed or removed unresolved provider obligations")

        declared = notice_document["notice_files"]
        if declared.get("licenses/GPL-3.0.txt") != GPL3_SHA256 or digest(gpl3) != GPL3_SHA256:
            raise RuntimeError("GPL-3 notice differs from the canonical selected text")
        for provider in identity["providers"].values():
            for relative in provider["notices"]:
                if relative not in declared:
                    raise RuntimeError(f"provider notice is not declared: {relative}")
        for relative, expected in declared.items():
            staged = exported_root / "third_party/provider-notices" / relative
            if not staged.is_file() or digest(staged) != expected:
                raise RuntimeError(f"staged notice digest mismatch: {relative}")

        staged_identity = json.loads(
            (exported_root / "third_party/provider-notices/PROVIDER-NOTICES.json").read_text(encoding="utf-8")
        )
        if staged_identity["notice_files"] != declared:
            raise RuntimeError("staged notice identity does not bind every declared notice digest")
        source_identity_path = exported_root / "third_party/paq/SOURCE-IDENTITY.json"
        source_identity = json.loads(source_identity_path.read_text(encoding="utf-8"))
        verify_current_paq_sources(closure_document, source_identity)

        export_manifest_path = exported_root / "EXPORT-MANIFEST.json"
        export_manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
        if (export_manifest.get("profile") != "engineering-validation" or
                export_manifest.get("dependency_closure_status") != "engineering_validation_not_release" or
                not export_manifest.get("source_export_only")):
            raise RuntimeError("export was not kept in source-candidate engineering-validation mode")
        verify_exported_members(exported_root, export_manifest)
        exported_bytes = tree_bytes(exported_root)
        if exported_bytes > MAX_EXPORTED_BYTES:
            raise RuntimeError(f"export exceeds {MAX_EXPORTED_BYTES} byte cap: {exported_bytes}")
        require_no_private_references(exported_root)

        after = file_map(inputs)
        if after != before:
            raise RuntimeError("source or tool input changed during verification")
        receipt.update(
            status="passed",
            selected_provider_count=len(selected),
            unresolved=identity["unresolved"],
            staged_notice_files=declared,
            exported_bytes=exported_bytes,
            export_manifest_sha256=digest(export_manifest_path),
            staged_provider_identity_sha256=digest(
                exported_root / "third_party/provider-notices/PROVIDER-NOTICES.json"
            ),
            staged_paq_source_identity_sha256=digest(source_identity_path),
            inputs_after_sha256=after,
        )
        (WORK / "PASS").write_text(
            "current 14-provider notice and PAQ source-identity staging passed; no build performed\n",
            encoding="utf-8",
        )
    except Exception as error:
        receipt["error_type"] = type(error).__name__
        receipt["error"] = str(error)
        raise
    finally:
        try:
            after_final = file_map(inputs)
            receipt["inputs_after_sha256"] = after_final
            receipt["inputs_stable"] = before is not None and after_final == before
        except Exception as snapshot_error:
            receipt["inputs_after_error_type"] = type(snapshot_error).__name__
            receipt["inputs_after_error"] = str(snapshot_error)
            receipt["inputs_stable"] = False
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
