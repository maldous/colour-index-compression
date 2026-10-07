#!/usr/bin/env python3
"""Stream a receipt-verified non-PAQ provider source archive without staging a tree.

The caller supplies every source root and receipt explicitly.  This program
copies no working tree: it verifies the declared JXL and spatial file maps,
then streams exactly those files, the retained Debian source inputs, and the
selected provider notice texts into one bounded gzip tar archive.  A read-back
pass verifies each archive member before the caller can record the result.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any, BinaryIO

from stage_non_paq_provider_sources import (
    NON_PAQ_PROVIDER_KEYS,
    load_receipt,
    regular_file,
    safe_relative,
    selected_provider_hashes,
    sha256_file,
    verified_file_map,
    verify_jxl_bindings,
    verify_jxl_source_identity,
    verify_package_inputs,
    verify_package_receipts,
    verify_spatial_binding,
    verify_tree,
)

ARCHIVE_ROOT = "cix-provider-sources-v1"


class BoundedWriter:
    """Reject an archive write before it can exceed its declared byte limit."""

    def __init__(self, destination: BinaryIO, limit: int) -> None:
        if limit <= 0:
            raise ValueError("archive byte limit must be positive")
        self.destination = destination
        self.limit = limit
        self.written = 0

    def write(self, data: bytes) -> int:
        if self.written + len(data) > self.limit:
            raise ValueError("compressed archive exceeds its declared byte limit")
        count = self.destination.write(data)
        if count != len(data):
            raise OSError("short archive write")
        self.written += count
        return count

    def flush(self) -> None:
        self.destination.flush()

    def close(self) -> None:
        self.destination.close()


def source_member_name(prefix: str, relative: str) -> str:
    """Construct one archive member beneath the fixed archive root."""
    return f"{ARCHIVE_ROOT}/{prefix}/{safe_relative(relative).as_posix()}"


def archive_info(name: str, size: int, mode: int = 0o644) -> tarfile.TarInfo:
    """Make a deterministic regular-file tar header."""
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def add_file(
    archive: tarfile.TarFile,
    name: str,
    source: Path,
    expected_sha256: str,
    members: dict[str, str],
    modes: dict[str, int],
) -> None:
    """Add one pre-verified regular source member and record its identity."""
    regular_file(source, f"source archive member {name}")
    if sha256_file(source) != expected_sha256:
        raise ValueError(f"source member hash mismatch before archive write: {source}")
    mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
    with source.open("rb") as stream:
        archive.addfile(archive_info(name, source.stat().st_size, mode), stream)
    members[name] = expected_sha256
    modes[name] = mode


def add_bytes(
    archive: tarfile.TarFile, name: str, data: bytes, members: dict[str, str], modes: dict[str, int]
) -> None:
    """Add generated, deterministic archive metadata."""
    archive.addfile(archive_info(name, len(data)), io.BytesIO(data))
    members[name] = hashlib.sha256(data).hexdigest()
    modes[name] = 0o644


def verify_source_members(source_root: Path, expected_files: dict[str, str]) -> dict[str, tuple[Path, str, str | None]]:
    """Verify receipt-listed regular files and in-tree symlinks without flattening them."""
    root = source_root.resolve()
    if not root.is_dir() or source_root.is_symlink():
        raise ValueError(f"source root must be a direct directory: {source_root}")
    verified: dict[str, tuple[Path, str, str | None]] = {}
    for name, digest in sorted(expected_files.items()):
        source = source_root.joinpath(*safe_relative(name).parts)
        if source.is_symlink():
            target = source.resolve()
            if root not in target.parents or not target.is_file() or target.is_symlink():
                raise ValueError(f"source symlink escapes its source root: {source}")
            if sha256_file(target) != digest:
                raise ValueError(f"source symlink target hash mismatch: {source}")
            verified[name] = (source, digest, os.readlink(source))
        else:
            regular_file(source, "source member")
            if sha256_file(source) != digest:
                raise ValueError(f"source member hash mismatch: {source}")
            verified[name] = (source, digest, None)
    return verified


def add_source_member(
    archive: tarfile.TarFile,
    name: str,
    source: Path,
    expected_sha256: str,
    link_target: str | None,
    members: dict[str, str],
    modes: dict[str, int],
    links: dict[str, str],
) -> None:
    """Add one verified file or preserve its in-tree symbolic-link representation."""
    mode = source.lstat().st_mode & 0o777
    if link_target is not None:
        info = archive_info(name, 0, mode)
        info.type = tarfile.SYMTYPE
        info.linkname = link_target
        archive.addfile(info)
        links[name] = link_target
        modes[name] = mode
        return
    add_file(archive, name, source, expected_sha256, members, modes)


def declared_ubuntu_sources(
    manifest: dict[str, Any], acquisition: dict[str, Any], downloads_root: Path
) -> dict[str, tuple[Path, str]]:
    """Bind each retained Debian descriptor/component archive to its acquisition receipt."""
    if acquisition.get("status") != "pass_source_inputs_retained_not_built":
        raise ValueError("Ubuntu source acquisition receipt is not a successful retained-input result")
    downloaded = acquisition.get("downloaded")
    if not isinstance(downloaded, dict):
        raise ValueError("Ubuntu source acquisition receipt has no downloaded source map")
    result: dict[str, tuple[Path, str]] = {}
    components = manifest.get("components")
    if not isinstance(components, list):
        raise ValueError("Ubuntu source manifest has no component list")
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("malformed Ubuntu source component")
        source = component.get("source")
        files = component.get("files")
        observed = downloaded.get(source)
        if not isinstance(source, str) or not isinstance(files, list) or not isinstance(observed, dict):
            raise ValueError("acquisition receipt does not bind a declared source component")
        for item in files:
            if not isinstance(item, dict):
                raise ValueError("malformed Ubuntu source input")
            role = item.get("role")
            filename = item.get("filename")
            digest = item.get("sha256")
            receipt_item = observed.get(role)
            if not isinstance(role, str) or not isinstance(filename, str) or not isinstance(digest, str):
                raise ValueError("Ubuntu source input identity is incomplete")
            if not isinstance(receipt_item, dict) or receipt_item.get("filename") != filename or receipt_item.get("sha256") != digest:
                raise ValueError(f"acquisition receipt does not bind {filename}")
            source_file = regular_file(downloads_root / safe_relative(filename), "retained Debian source input")
            if sha256_file(source_file) != digest:
                raise ValueError(f"retained Debian source input hash mismatch: {source_file}")
            result[f"debian/{source}/{filename}"] = (source_file, digest)
    return result


def verify_ubuntu_source_to_binary_bindings(
    metadata: dict[str, Any], manifest: dict[str, Any], acquisition: dict[str, Any], package_inputs: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Bind each acquired source tuple to its retained package and selected ELF relation."""
    components = manifest.get("components")
    bindings = acquisition.get("binary_bindings")
    declared = metadata.get("binary_package_inputs")
    if not isinstance(components, list) or not isinstance(bindings, dict) or not isinstance(declared, dict):
        raise ValueError("source-to-binary binding inputs are incomplete")
    result: dict[str, dict[str, str]] = {}
    for component_name, package_input in declared.items():
        if not isinstance(package_input, dict):
            raise ValueError("malformed binary package input")
        source_input = package_input.get("source_package_input")
        if not isinstance(source_input, dict):
            raise ValueError(f"source package locator missing: {component_name}")
        source_name = source_input.get("source_package")
        source_version = source_input.get("source_version")
        matching = [item for item in components if isinstance(item, dict) and item.get("source") == source_name]
        if len(matching) != 1 or matching[0].get("version") != source_version:
            raise ValueError(f"Ubuntu source manifest does not bind {component_name}")
        recorded = bindings.get(source_name)
        packages = package_input.get("packages")
        if not isinstance(recorded, dict) or not isinstance(packages, dict):
            raise ValueError(f"Ubuntu receipt lacks package binding for {component_name}")
        runtime = recorded.get("runtime")
        development = recorded.get("development")
        expected_runtime = packages.get("runtime")
        expected_development = packages.get("development")
        if not all(isinstance(value, dict) for value in (runtime, development, expected_runtime, expected_development)):
            raise ValueError(f"incomplete package binding for {component_name}")
        if runtime.get("archive_sha256") != expected_runtime.get("sha256"):
            raise ValueError(f"runtime package identity mismatch for {component_name}")
        if development.get("archive_sha256") != expected_development.get("sha256"):
            raise ValueError(f"development package identity mismatch for {component_name}")
        selected_hash = package_input.get("selected_artifact_sha256")
        if runtime.get("member_sha256") != selected_hash:
            raise ValueError(f"selected ELF relation mismatch for {component_name}")
        result[component_name] = {
            "source_package": str(source_name),
            "source_version": str(source_version),
            "runtime_package_sha256": str(runtime["archive_sha256"]),
            "development_package_sha256": str(development["archive_sha256"]),
            "selected_elf_sha256": str(runtime["member_sha256"]),
        }
    return result


def selected_notice_files(
    notices_root: Path, selected: dict[str, str]
) -> tuple[dict[str, tuple[Path, str]], bytes]:
    """Verify selected notice texts and create a public, selected-only index."""
    manifest_path = regular_file(notices_root / "provider-notices.json", "provider notice manifest")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    providers = document.get("providers")
    hashes = document.get("notice_files")
    if not isinstance(providers, dict) or not isinstance(hashes, dict):
        raise ValueError("provider notice manifest is incomplete")
    result: dict[str, tuple[Path, str]] = {}
    index_providers: dict[str, dict[str, Any]] = {}
    index_files: dict[str, str] = {}
    for provider in NON_PAQ_PROVIDER_KEYS:
        entry = providers.get(provider)
        if not isinstance(entry, dict) or entry.get("sha256") != selected.get(provider):
            raise ValueError(f"provider notice manifest does not bind {provider}")
        notice_names = entry.get("notices")
        if not isinstance(notice_names, list):
            raise ValueError(f"provider notice list missing for {provider}")
        for value in notice_names:
            if not isinstance(value, str) or not isinstance(hashes.get(value), str):
                raise ValueError("malformed provider notice identity")
            source = regular_file(notices_root / safe_relative(value), "provider notice")
            digest = hashes[value]
            if sha256_file(source) != digest:
                raise ValueError(f"provider notice hash mismatch: {source}")
            result[f"notices/{value}"] = (source, digest)
            index_files[value] = digest
        index_providers[provider] = {"sha256": selected[provider], "notices": notice_names}
    index = {
        "schema": "cix-selected-non-paq-provider-notices-v1",
        "scope": "Selected non-PAQ provider notice identities only.",
        "providers": index_providers,
        "notice_files": index_files,
    }
    return result, (json.dumps(index, indent=2, sort_keys=True) + "\n").encode("utf-8")


def instructions() -> bytes:
    """Explain the archive contents without embedding private workstation paths."""
    return (
        "CIX provider source archive\n\n"
        "This archive contains receipt-verified source inputs for selected non-PAQ Linux providers. "
        "It contains the selected libjxl source map, a frozen CIX spatial bridge snapshot, "
        "and the exact CharLS/OpenJPEG Debian source descriptor, orig, and Debian-delta archives.\n\n"
        "The Debian source inputs can be unpacked in a fresh directory with dpkg-source --no-preparation -x <source>.dsc. "
        "This archive records source identity only. It does not establish a reproducible provider build, redistribution terms, "
        "platform support, or release acceptance.\n"
    ).encode("utf-8")


def readback(
    archive_path: Path, expected: dict[str, str], expected_modes: dict[str, int], expected_links: dict[str, str]
) -> None:
    """Reject unexpected, missing, non-regular, or hash-mismatched archive members."""
    observed: dict[str, str] = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive:
            name = member.name
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or not name.startswith(f"{ARCHIVE_ROOT}/"):
                raise ValueError(f"unsafe archive member after write: {name}")
            if name in observed:
                raise ValueError(f"duplicate archive member: {name}")
            if (member.mode & 0o777) != expected_modes.get(name):
                raise ValueError(f"archive mode mismatch: {name}")
            if name in expected_links:
                if not member.issym() or member.linkname != expected_links[name]:
                    raise ValueError(f"archive symlink mismatch: {name}")
                observed[name] = ""
                continue
            if not member.isfile():
                raise ValueError(f"unexpected non-regular archive member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read archive member: {name}")
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            observed[name] = digest.hexdigest()
    expected_names = set(expected) | set(expected_links)
    if set(observed) != expected_names or any(observed[name] != digest for name, digest in expected.items()):
        missing = sorted(expected_names - set(observed))
        extra = sorted(set(observed) - expected_names)
        raise ValueError(f"archive member identity mismatch; missing={missing[:3]} extra={extra[:3]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--jxl-source-root", type=Path, required=True)
    parser.add_argument("--spatial-snapshot-root", type=Path, required=True)
    parser.add_argument("--codec-archive-root", type=Path, required=True)
    parser.add_argument("--notices-root", type=Path, required=True)
    parser.add_argument("--ubuntu-manifest", type=Path, required=True)
    parser.add_argument("--ubuntu-receipt", type=Path, required=True)
    parser.add_argument("--ubuntu-downloads-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-byte-limit", type=int, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    regular_file(args.metadata, "non-PAQ source metadata")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    if metadata.get("schema") != "cix-non-paq-provider-source-inputs-v1":
        raise ValueError("unsupported non-PAQ source metadata schema")
    evidence = metadata.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("non-PAQ metadata has no evidence map")
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
    if not isinstance(spatial, dict):
        raise ValueError("spatial source metadata is missing")
    verify_spatial_binding(spatial_binding, spatial, selected)
    spatial_files = spatial.get("required_source_files")
    if not isinstance(spatial_files, dict):
        raise ValueError("spatial source file map is missing")
    if any(verified_file_map(spatial_source, "sha256").get(name) != digest for name, digest in spatial_files.items()):
        raise ValueError("spatial source receipt does not bind every selected bridge member")
    verify_package_receipts(metadata, codec_packages, codec_install)
    package_inputs = verify_package_inputs(metadata, args.codec_archive_root.resolve(), selected)

    jxl_expected = verified_file_map(jxl_source, "sha256")
    jxl_files = verify_source_members(args.jxl_source_root.resolve(), jxl_expected)
    spatial_files_verified = verify_tree(args.spatial_snapshot_root.resolve(), spatial_files)
    ubuntu_manifest_path = regular_file(args.ubuntu_manifest, "Ubuntu source manifest")
    ubuntu_receipt_path = regular_file(args.ubuntu_receipt, "Ubuntu source acquisition receipt")
    ubuntu_manifest = json.loads(ubuntu_manifest_path.read_text(encoding="utf-8"))
    ubuntu_receipt = json.loads(ubuntu_receipt_path.read_text(encoding="utf-8"))
    ubuntu_files = declared_ubuntu_sources(ubuntu_manifest, ubuntu_receipt, args.ubuntu_downloads_root.resolve())
    ubuntu_bindings = verify_ubuntu_source_to_binary_bindings(
        metadata, ubuntu_manifest, ubuntu_receipt, package_inputs
    )
    notices, notice_index = selected_notice_files(args.notices_root.resolve(), selected)

    archive_path = args.archive.resolve()
    receipt_path = args.receipt.resolve()
    if archive_path.exists() or receipt_path.exists():
        raise ValueError("archive and receipt destinations must be new")
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    expected: dict[str, str] = {}
    expected_modes: dict[str, int] = {}
    expected_links: dict[str, str] = {}
    with archive_path.open("xb") as destination:
        bounded = BoundedWriter(destination, args.archive_byte_limit)
        with gzip.GzipFile(filename="", mode="wb", fileobj=bounded, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|", format=tarfile.GNU_FORMAT) as archive:
                for name, (source, digest, link_target) in sorted(jxl_files.items()):
                    add_source_member(
                        archive,
                        source_member_name("libjxl-v0.12.0", name),
                        source,
                        digest,
                        link_target,
                        expected,
                        expected_modes,
                        expected_links,
                    )
                for name, source in sorted(spatial_files_verified.items()):
                    add_file(
                        archive,
                        source_member_name("cix-spatial-bridge-snapshot", name),
                        source,
                        spatial_files[name],
                        expected,
                        expected_modes,
                    )
                for relative, (source, digest) in sorted(ubuntu_files.items()):
                    add_file(
                        archive, source_member_name("ubuntu", relative), source, digest, expected, expected_modes
                    )
                for relative, (source, digest) in sorted(notices.items()):
                    add_file(
                        archive, source_member_name("NOTICE", relative), source, digest, expected, expected_modes
                    )
                add_bytes(
                    archive,
                    f"{ARCHIVE_ROOT}/NOTICE/selected-provider-notices.json",
                    notice_index,
                    expected,
                    expected_modes,
                )
                add_bytes(archive, f"{ARCHIVE_ROOT}/README.txt", instructions(), expected, expected_modes)
                identity = {
                "schema": "cix-non-paq-provider-source-archive-v1",
                "scope": "Receipt-verified source inputs only; no provider build or release claim.",
                "selected_provider_hashes": selected,
                "jxl_source_file_count": len(jxl_files),
                "jxl_source_symlinks": {
                    name: {"target": link_target, "target_sha256": digest}
                    for name, (_, digest, link_target) in jxl_files.items()
                    if link_target is not None
                },
                "spatial_snapshot_file_count": len(spatial_files_verified),
                "ubuntu_source_inputs": sorted(ubuntu_files),
                "ubuntu_source_to_binary_bindings": ubuntu_bindings,
                "notice_members": sorted(notices),
                "metadata_sha256": sha256_file(args.metadata),
                "closure_sha256": sha256_file(args.closure),
                "ubuntu_manifest_sha256": sha256_file(ubuntu_manifest_path),
                "ubuntu_receipt_sha256": sha256_file(ubuntu_receipt_path),
            }
                add_bytes(
                    archive,
                    f"{ARCHIVE_ROOT}/SOURCE-IDENTITY.json",
                    (json.dumps(identity, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                    expected,
                    expected_modes,
                )
    readback(archive_path, expected, expected_modes, expected_links)
    archive_sha256 = sha256_file(archive_path)
    receipt = {
        "schema": "cix-non-paq-provider-source-archive-receipt-v1",
        "status": "pass_source_identity_archive_not_reproducible_build",
        "archive": {"path": str(archive_path), "bytes": archive_path.stat().st_size, "sha256": archive_sha256},
        "archive_byte_limit": args.archive_byte_limit,
        "member_count": len(expected),
        "members": expected,
        "member_modes": expected_modes,
        "member_symlinks": expected_links,
        "selected_provider_hashes": selected,
        "ubuntu_source_to_binary_bindings": ubuntu_bindings,
        "non_claim": "This receipt verifies archive member identities only. It does not establish provider build reproducibility, source-to-binary equivalence, redistribution terms, package-manager acceptance, or release acceptance.",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
