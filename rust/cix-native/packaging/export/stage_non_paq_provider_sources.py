#!/usr/bin/env python3
"""Stage receipt-verified available non-PAQ provider source inputs.

The tool has two deliberate outcomes.  It copies the complete retained libjxl
source tree and the frozen CIX spatial bridge snapshot only after every listed
file and selected ELF binding has been checked.  It records, but does not call
source closure for, the verified CharLS and OpenJPEG binary package inputs.
Those source packages are not present in the retained evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any


NON_PAQ_PROVIDER_KEYS = (
    "CIX_RUNTIME_JXL_BRIDGE",
    "CIX_RUNTIME_SPATIAL_BRIDGE",
    "CIX_RUNTIME_JXL_LIBRARY",
    "CIX_RUNTIME_JXL_THREADS_LIBRARY",
    "CIX_RUNTIME_JXL_CMS_LIBRARY",
    "CIX_RUNTIME_BROTLIDEC_LIBRARY",
    "CIX_RUNTIME_BROTLIENC_LIBRARY",
    "CIX_RUNTIME_BROTLICOMMON_LIBRARY",
    "CIX_RUNTIME_CHARLS_LIBRARY",
    "CIX_RUNTIME_OPENJPEG_LIBRARY",
)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def regular_file(path: Path, label: str) -> Path:
    """Require a non-symlink regular file."""
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a non-symlink regular file: {path}")
    return path


def safe_relative(value: str) -> PurePosixPath:
    """Reject paths that could escape an explicitly selected input root."""
    relative = PurePosixPath(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return relative


def receipt_path(receipt_root: Path, value: object) -> Path:
    """Resolve an evidence receipt only below the supplied evidence root."""
    if not isinstance(value, str):
        raise ValueError("receipt path must be a string")
    root = receipt_root.resolve()
    candidate = root.joinpath(*safe_relative(value).parts).resolve()
    if root not in candidate.parents:
        raise ValueError(f"receipt path escapes evidence root: {value}")
    return candidate


def load_receipt(
    descriptor: dict[str, Any], receipt_root: Path, required_map_key: str | None = None
) -> Any:
    """Hash-bind one JSON receipt and return its decoded object."""
    path = receipt_path(receipt_root, descriptor.get("path"))
    regular_file(path, "evidence receipt")
    expected = descriptor.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"receipt has no SHA-256: {path}")
    if sha256_file(path) != expected:
        raise ValueError(f"evidence receipt hash mismatch: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, (dict, list)):
        raise ValueError(f"evidence receipt is not JSON data: {path}")
    if required_map_key is not None:
        if not isinstance(document, dict):
            raise ValueError(f"evidence receipt is not an object: {path}")
        mapped = document.get(required_map_key)
        if not isinstance(mapped, dict) or not mapped:
            raise ValueError(f"evidence receipt has no {required_map_key} map: {path}")
    return document


def verified_file_map(document: dict[str, Any], map_key: str) -> dict[str, str]:
    """Validate a receipt file map before looking at any source member."""
    value = document.get(map_key)
    if not isinstance(value, dict):
        raise ValueError(f"receipt has no {map_key} map")
    result: dict[str, str] = {}
    for name, digest in value.items():
        if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("malformed source receipt file map")
        safe_relative(name)
        result[name] = digest
    if not result:
        raise ValueError("empty source receipt file map")
    return result


def verify_tree(source_root: Path, expected_files: dict[str, str]) -> dict[str, Path]:
    """Verify each receipt member before any copy occurs."""
    if not source_root.is_absolute() or not source_root.is_dir() or source_root.is_symlink():
        raise ValueError(f"source root must be an absolute non-symlink directory: {source_root}")
    verified: dict[str, Path] = {}
    for name, expected in sorted(expected_files.items()):
        source = regular_file(source_root.joinpath(*safe_relative(name).parts), "source member")
        if sha256_file(source) != expected:
            raise ValueError(f"source member hash mismatch: {source}")
        verified[name] = source
    return verified


def copy_verified(destination: Path, verified: dict[str, Path]) -> dict[str, str]:
    """Copy exactly pre-verified members and bind each staged hash."""
    if destination.exists():
        raise ValueError(f"staging destination already exists: {destination}")
    destination.mkdir(parents=True)
    copied: dict[str, str] = {}
    for name, source in sorted(verified.items()):
        target = destination.joinpath(*safe_relative(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied[name] = sha256_file(target)
        if copied[name] != sha256_file(source):
            raise ValueError(f"staged source member hash mismatch: {target}")
    return copied


def selected_provider_hashes(closure_path: Path, metadata: dict[str, Any]) -> dict[str, str]:
    """Validate selected non-PAQ ELF files against the frozen closure."""
    regular_file(closure_path, "selected provider closure")
    closure_digest = sha256_file(closure_path)
    expected_closure = metadata.get("selected_closure", {}).get("sha256")
    if closure_digest != expected_closure:
        raise ValueError("selected provider closure hash differs from source-input manifest")
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    if closure.get("schema") != "cix-engineering-provider-closure-v1":
        raise ValueError("unsupported selected provider closure schema")
    if closure.get("status") != "engineering_inputs_selected":
        raise ValueError("selected engineering provider closure is required")
    providers = closure.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("selected provider closure has no provider map")
    hashes: dict[str, str] = {}
    for key in NON_PAQ_PROVIDER_KEYS:
        entry = providers.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f"selected closure missing {key}")
        selected = regular_file(Path(str(entry.get("path", ""))), key)
        expected = entry.get("sha256")
        if not isinstance(expected, str) or sha256_file(selected) != expected:
            raise ValueError(f"selected provider hash mismatch: {key}")
        hashes[key] = expected
    return hashes


def verify_jxl_bindings(metadata: dict[str, Any], installed: dict[str, Any], selected: dict[str, str]) -> None:
    """Require the installed receipt to bind each selected JXL-family ELF."""
    installed_hashes = verified_file_map(installed, "sha256")
    bindings = metadata["jxl_source"].get("selected_provider_install_members")
    if not isinstance(bindings, dict):
        raise ValueError("JXL source metadata has no installed provider bindings")
    for provider, installed_member in bindings.items():
        if provider not in selected or not isinstance(installed_member, str):
            raise ValueError(f"invalid JXL installed provider binding: {provider}")
        if installed_hashes.get(installed_member) != selected[provider]:
            raise ValueError(f"JXL installed receipt does not bind selected provider: {provider}")


def verify_jxl_source_identity(metadata: dict[str, Any], receipt: dict[str, Any]) -> None:
    """Bind the declared JXL revision and recursive submodules to its receipt."""
    source = metadata.get("jxl_source")
    if not isinstance(source, dict):
        raise ValueError("JXL source metadata is missing")
    if receipt.get("head") != source.get("commit"):
        raise ValueError("JXL source receipt head differs from declared commit")
    status = receipt.get("submodule_status")
    submodules = source.get("required_submodules")
    if not isinstance(status, str) or not isinstance(submodules, dict) or not submodules:
        raise ValueError("JXL source submodule identity is incomplete")
    for path, commit in submodules.items():
        if not isinstance(path, str) or not isinstance(commit, str):
            raise ValueError("malformed JXL submodule identity")
        if f"{commit} {path}" not in status:
            raise ValueError(f"JXL receipt does not bind submodule {path}")


def verify_spatial_binding(binding: Any, spatial: dict[str, Any], selected: dict[str, str]) -> None:
    """Require the retained review to bind the frozen spatial snapshot to its ELF."""
    if not isinstance(binding, dict):
        raise ValueError("spatial binary binding receipt is not an object")
    recorded = binding.get("spatial_selected_binary_binding")
    if not isinstance(recorded, dict):
        raise ValueError("spatial binary binding receipt has no selected binding")
    artifact = recorded.get("selected_artifact")
    source = recorded.get("source_snapshot")
    if not isinstance(artifact, dict) or not isinstance(source, dict):
        raise ValueError("spatial binary binding receipt is incomplete")
    if artifact.get("sha256") != selected.get("CIX_RUNTIME_SPATIAL_BRIDGE"):
        raise ValueError("spatial binding receipt does not match selected ELF")
    expected_files = spatial.get("required_source_files")
    if not isinstance(expected_files, dict):
        raise ValueError("spatial source file map missing")
    for name, digest in expected_files.items():
        receipt_field = {
            "codecs/spatial/CMakeLists.txt": "source_cmakelists_sha256",
            "codecs/spatial/cix_spatial_bridge.cpp": "source_cpp_sha256",
        }.get(name)
        if receipt_field is not None and source.get(receipt_field) != digest:
            raise ValueError(f"spatial binding receipt does not bind {name}")


def verify_package_inputs(metadata: dict[str, Any], archive_root: Path, selected: dict[str, str]) -> dict[str, Any]:
    """Verify retained .deb inputs without mislabelling them as source archives."""
    if not archive_root.is_absolute() or not archive_root.is_dir() or archive_root.is_symlink():
        raise ValueError("codec archive root must be an absolute non-symlink directory")
    verified: dict[str, Any] = {}
    entries = metadata.get("binary_package_inputs")
    if not isinstance(entries, dict):
        raise ValueError("non-PAQ metadata has no binary package inputs")
    for component, entry in entries.items():
        if not isinstance(entry, dict):
            raise ValueError(f"malformed package input: {component}")
        provider = entry.get("selected_provider")
        if not isinstance(provider, str) or selected.get(provider) != entry.get("selected_artifact_sha256"):
            raise ValueError(f"selected artifact binding mismatch: {component}")
        packages = entry.get("packages")
        if not isinstance(packages, dict) or set(packages) != {"runtime", "development"}:
            raise ValueError(f"runtime/development package pair required: {component}")
        verified_packages: dict[str, dict[str, str]] = {}
        for kind, package in packages.items():
            if not isinstance(package, dict):
                raise ValueError(f"malformed {kind} package: {component}")
            filename = package.get("archive_filename")
            expected = package.get("sha256")
            if not isinstance(filename, str) or not isinstance(expected, str):
                raise ValueError(f"package identity incomplete: {component}/{kind}")
            archive = regular_file(archive_root / safe_relative(filename), "package archive")
            if sha256_file(archive) != expected:
                raise ValueError(f"package archive hash mismatch: {archive}")
            verified_packages[kind] = {
                "name": str(package.get("name")),
                "version": str(package.get("version")),
                "architecture": str(package.get("architecture")),
                "repository_filename": str(package.get("repository_filename")),
                "archive_filename": filename,
                "sha256": expected,
            }
        verified[component] = {
            "selected_provider": provider,
            "selected_artifact_sha256": entry["selected_artifact_sha256"],
            "verified_binary_packages": verified_packages,
            "source_status": "not_present: source-package locator, digest, and package-to-ELF mapping remain required",
        }
    return verified


def verify_package_receipts(
    metadata: dict[str, Any], package_receipt: Any, install_receipt: Any
) -> None:
    """Require package metadata to agree with both retained package receipts."""
    if not isinstance(package_receipt, list):
        raise ValueError("codec package receipt must be a list")
    if not isinstance(install_receipt, dict) or not isinstance(install_receipt.get("packages"), list):
        raise ValueError("codec installation receipt has no package list")

    def package_index(values: list[Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
        indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
        for value in values:
            if not isinstance(value, dict):
                raise ValueError("malformed codec package receipt entry")
            identity = (value.get("name"), value.get("version"), value.get("architecture"))
            if not all(isinstance(item, str) for item in identity):
                raise ValueError("codec package receipt has incomplete package identity")
            indexed[identity] = value
        return indexed

    package_indexed = package_index(package_receipt)
    install_indexed = package_index(install_receipt["packages"])
    entries = metadata.get("binary_package_inputs")
    if not isinstance(entries, dict):
        raise ValueError("non-PAQ metadata has no binary package inputs")
    for component, entry in entries.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("packages"), dict):
            raise ValueError(f"malformed package input: {component}")
        for package in entry["packages"].values():
            if not isinstance(package, dict):
                raise ValueError(f"malformed package entry: {component}")
            identity = (package.get("name"), package.get("version"), package.get("architecture"))
            expected = {
                "sha256": package.get("sha256"),
                "filename": package.get("repository_filename"),
            }
            for receipt_name, indexed in (("package", package_indexed), ("installation", install_indexed)):
                observed = indexed.get(identity)
                if not isinstance(observed, dict) or any(observed.get(key) != value for key, value in expected.items()):
                    raise ValueError(f"{receipt_name} receipt does not bind {component} package {identity[0]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--jxl-source-root", type=Path, required=True)
    parser.add_argument("--spatial-snapshot-root", type=Path, required=True)
    parser.add_argument("--codec-archive-root", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--require-source-complete", action="store_true")
    args = parser.parse_args()

    regular_file(args.metadata, "non-PAQ source metadata")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    if metadata.get("schema") != "cix-non-paq-provider-source-inputs-v1":
        raise ValueError("unsupported non-PAQ source metadata schema")
    evidence = metadata.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("non-PAQ source metadata has no evidence map")

    selected = selected_provider_hashes(args.closure.resolve(), metadata)
    jxl_source = load_receipt(evidence["jxl_source_receipt"], args.receipt_root.resolve(), "sha256")
    jxl_install = load_receipt(evidence["jxl_install_receipt"], args.receipt_root.resolve(), "sha256")
    spatial_source = load_receipt(evidence["spatial_source_receipt"], args.receipt_root.resolve(), "sha256")
    spatial_binding = load_receipt(evidence["spatial_binary_binding"], args.receipt_root.resolve())
    codec_packages = load_receipt(evidence["codec_packages"], args.receipt_root.resolve())
    codec_install = load_receipt(evidence["codec_install"], args.receipt_root.resolve())

    verify_jxl_source_identity(metadata, jxl_source)
    verify_jxl_bindings(metadata, jxl_install, selected)
    spatial = metadata.get("spatial_bridge")
    if not isinstance(spatial, dict) or spatial.get("selected_artifact_sha256") != selected.get("CIX_RUNTIME_SPATIAL_BRIDGE"):
        raise ValueError("spatial selected artifact binding mismatch")
    verify_spatial_binding(spatial_binding, spatial, selected)
    spatial_expected = spatial.get("required_source_files")
    if not isinstance(spatial_expected, dict):
        raise ValueError("spatial source file map missing")
    source_map = verified_file_map(spatial_source, "sha256")
    if any(source_map.get(name) != digest for name, digest in spatial_expected.items()):
        raise ValueError("spatial source receipt does not bind every required bridge member")

    unresolved = metadata.get("remaining_source_obligations")
    if not isinstance(unresolved, list) or not unresolved:
        raise ValueError("remaining source obligations must be explicit")
    if args.require_source_complete:
        raise ValueError("source-complete staging is blocked: CharLS/OpenJPEG source inputs are not retained")
    verify_package_receipts(metadata, codec_packages, codec_install)
    packages = verify_package_inputs(metadata, args.codec_archive_root.resolve(), selected)
    jxl_verified = verify_tree(
        args.jxl_source_root.resolve(), verified_file_map(jxl_source, "sha256")
    )
    spatial_verified = verify_tree(args.spatial_snapshot_root.resolve(), spatial_expected)

    output = args.export_root.resolve() / "third_party" / "non-paq-sources"
    if output.exists():
        raise ValueError(f"non-PAQ staging destination already exists: {output}")
    output.mkdir(parents=True)
    jxl_copied = copy_verified(output / "libjxl-v0.12.0", jxl_verified)
    spatial_copied = copy_verified(output / "cix-spatial-bridge-snapshot", spatial_verified)
    identity = {
        "schema": "cix-non-paq-engineering-source-identity-v1",
        "status": "engineering_source_inputs_incomplete_not_release_closure",
        "selected_provider_hashes": selected,
        "jxl_source_file_count": len(jxl_copied),
        "jxl_source_files": jxl_copied,
        "spatial_snapshot_files": spatial_copied,
        "verified_binary_package_inputs": packages,
        "remaining_source_obligations": unresolved,
        "non_claim": "Verified binary packages are recorded as binary inputs only. This staging result does not establish source closure, package redistribution terms, or release acceptance."
    }
    (output / "SOURCE-IDENTITY.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
