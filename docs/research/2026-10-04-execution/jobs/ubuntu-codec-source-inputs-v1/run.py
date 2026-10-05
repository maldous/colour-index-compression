#!/usr/bin/env python3
"""Acquire and stage the exact Ubuntu source inputs for retained codec ELFs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from typing import Any


JOB = Path(__file__).resolve().parent
ROOT = JOB.parents[4]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
WORK_ROOT = ROOT / "benchmark-work/native-rc-check-v1"
WORK = WORK_ROOT / "ubuntu-codec-source-inputs-v1"
DOWNLOADS = WORK / "downloads"
SOURCES = WORK / "sources"
RECEIPT = WORK / "receipt.json"
FAILURE_RECEIPT = JOB / "receipt.json"
MANIFEST = JOB / "sources.json"
SPEC = JOB / "spec.json"
PROVENANCE = ROOT / "docs/research/2026-10-04-execution/reviews/ubuntu-codec-source-provenance-v1.json"
PROVENANCE_MANIFEST = ROOT / "rust/cix-native/packaging/notices/provider-provenance-v3.json"
PACKAGE_ARCHIVES = WORK_ROOT / "codec-sdk-v1/archives"
WORK_CAP = 160_000_000
SHARED_WORK_CAP = 4_000_000_000
RECEIPT_RESERVE = 4_000_000
ARCHIVE_HOST = "archive.ubuntu.com"
TOOLS = {
    "python": Path(sys.executable),
    "dpkg_source": Path("/usr/bin/dpkg-source"),
    "dpkg_deb": Path("/usr/bin/dpkg-deb"),
    "tar": Path("/usr/bin/tar"),
}


def sha256(path: Path) -> str:
    """Hash one direct regular file."""
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"expected direct regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocated_bytes(root: Path) -> int:
    """Count allocated blocks once per inode, including directory entries."""
    total = 0
    seen: set[tuple[int, int]] = set()
    for path in (root, *root.rglob("*")):
        try:
            status = path.lstat()
        except FileNotFoundError:
            raise RuntimeError(f"work root changed while measuring: {path}") from None
        identity = (status.st_dev, status.st_ino)
        if identity not in seen:
            total += status.st_blocks * 512
            seen.add(identity)
    return total


def write_receipt(receipt: dict[str, Any]) -> None:
    """Write a compact receipt inside the fresh job work directory."""
    destination = RECEIPT if WORK.exists() else FAILURE_RECEIPT
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def static_input_hashes() -> dict[str, str]:
    """Bind the runner, declared source tuple and provenance review."""
    paths = (Path(__file__), MANIFEST, SPEC, PROVENANCE, PROVENANCE_MANIFEST)
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def tool_identities() -> dict[str, dict[str, str]]:
    """Bind the real system tools used for descriptor and archive handling."""
    identities: dict[str, dict[str, str]] = {}
    for name, configured in TOOLS.items():
        resolved = configured.resolve(strict=True)
        if not resolved.is_file() or resolved.is_symlink():
            raise RuntimeError(f"required tool is not a resolved regular file: {configured}")
        identities[name] = {
            "configured_path": str(configured),
            "resolved_path": str(resolved),
            "sha256": sha256(resolved),
        }
    return identities


def binary_input_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    """Freeze all four retained binary package identities around the job."""
    hashes: dict[str, str] = {}
    for component in manifest["components"]:
        for key in ("selected_binary", "development_binary"):
            item = component[key]
            path = PACKAGE_ARCHIVES / item["archive"]
            digest = sha256(path)
            if digest != item["archive_sha256"]:
                raise RuntimeError(f"retained binary package hash mismatch: {path}")
            hashes[path.name] = digest
    return hashes


def safe_relative(value: str) -> PurePosixPath:
    """Reject archive paths that are absolute or escape their fresh root."""
    candidate = PurePosixPath(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError(f"unsafe archive member path: {value!r}")
    return PurePosixPath(*[part for part in candidate.parts if part not in ("", ".")])


def resolve_link(parts: tuple[str, ...]) -> str:
    """Resolve a relative link lexically and reject traversal above archive root."""
    resolved: list[str] = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved:
                raise RuntimeError("archive link escapes extraction root")
            resolved.pop()
        else:
            resolved.append(part)
    if not resolved:
        raise RuntimeError("archive link has an empty target")
    return "/".join(resolved)


def safe_link_target(member: tarfile.TarInfo, normalized_name: str) -> str:
    """Resolve a symlink or hardlink according to its tar header semantics."""
    target = PurePosixPath(member.linkname)
    if not member.linkname or target.is_absolute():
        raise RuntimeError(f"unsafe archive link: {member.name} -> {member.linkname}")
    if member.issym():
        return resolve_link(PurePosixPath(normalized_name).parent.parts + target.parts)
    return resolve_link(target.parts)


def inspect_tar(path: Path) -> dict[str, int]:
    """Validate member paths/links and measure data before extraction."""
    members = files = payload_bytes = 0
    kinds: dict[str, str] = {}
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive:
            normalized = safe_relative(member.name).as_posix()
            ancestors = PurePosixPath(normalized).parents
            if any(kinds.get(parent.as_posix()) in {"symlink", "hardlink", "file"} for parent in ancestors):
                raise RuntimeError(f"archive member traverses an earlier link or file: {member.name}")
            if normalized in kinds and not (member.isdir() and kinds[normalized] == "directory"):
                raise RuntimeError(f"archive rewrites an earlier member: {member.name}")
            if member.isdev() or member.isfifo():
                raise RuntimeError(f"unsupported special archive member: {member.name}")
            if member.islnk():
                target = safe_link_target(member, normalized)
                if kinds.get(target) != "file":
                    raise RuntimeError(f"hardlink target is not an earlier regular member: {member.name}")
                kinds[normalized] = "hardlink"
            elif member.issym():
                safe_link_target(member, normalized)
                kinds[normalized] = "symlink"
            elif member.isfile():
                kinds[normalized] = "file"
            elif member.isdir():
                kinds.setdefault(normalized, "directory")
            else:
                raise RuntimeError(f"unsupported archive member type: {member.name}")
            members += 1
            if member.isfile():
                files += 1
                payload_bytes += member.size
    return {"members": members, "files": files, "payload_bytes": payload_bytes}


def expected_url(component: dict[str, Any], item: dict[str, Any]) -> str:
    """Construct the only accepted official Ubuntu pool URL for one input."""
    pool = component.get("pool")
    filename = item.get("filename")
    if not isinstance(pool, str) or not isinstance(filename, str):
        raise RuntimeError("incomplete source input manifest")
    return f"https://{ARCHIVE_HOST}/ubuntu/{pool}/{filename}"


def download(component: dict[str, Any], item: dict[str, Any]) -> Path:
    """Download a bounded, no-redirect source input and verify it before use."""
    url = expected_url(component, item)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ARCHIVE_HOST or not parsed.path.startswith("/ubuntu/pool/"):
        raise RuntimeError(f"source URL outside the approved Ubuntu pool: {url}")
    filename = item.get("filename")
    expected_bytes = item.get("bytes")
    expected_sha256 = item.get("sha256")
    if not isinstance(filename, str) or not isinstance(expected_bytes, int) or not isinstance(expected_sha256, str):
        raise RuntimeError("malformed source input identity")
    destination = DOWNLOADS / filename
    partial = destination.with_name(destination.name + ".partial")
    if destination.exists() or partial.exists():
        raise RuntimeError(f"refusing to reuse source input path: {destination}")
    received = 0
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("xb") as output:
        if response.geturl() != url:
            raise RuntimeError(f"redirected source input rejected: {response.geturl()}")
        while True:
            block = response.read(min(1024 * 1024, expected_bytes + 1 - received))
            if not block:
                break
            received += len(block)
            if received > expected_bytes:
                raise RuntimeError(f"source input exceeds declared length: {url}")
            digest.update(block)
            output.write(block)
    if received != expected_bytes or digest.hexdigest() != expected_sha256:
        raise RuntimeError(f"source input identity mismatch: {url}")
    partial.rename(destination)
    return destination


def dsc_checksums(path: Path, component: dict[str, Any]) -> None:
    """Check descriptor source/version and SHA-256 entries against the manifest."""
    text = path.read_text(encoding="utf-8")
    signed = text.split("-----BEGIN PGP SIGNATURE-----", 1)[0]
    fields: dict[str, str] = {}
    lines = signed.splitlines()
    for line in lines:
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    if fields.get("Source") != component.get("source") or fields.get("Version") != component.get("version"):
        raise RuntimeError("source descriptor package/version mismatch")
    try:
        start = lines.index("Checksums-Sha256:") + 1
    except ValueError as error:
        raise RuntimeError("source descriptor lacks Checksums-Sha256") from error
    checksums: dict[str, tuple[int, str]] = {}
    for line in lines[start:]:
        if not line.startswith(" "):
            break
        fields_in_line = line.split()
        if len(fields_in_line) == 3:
            digest, size, filename = fields_in_line
            checksums[filename] = (int(size), digest)
    for item in component["files"]:
        if item["role"] == "dsc":
            continue
        observed = checksums.get(item["filename"])
        if observed != (item["bytes"], item["sha256"]):
            raise RuntimeError(f"source descriptor does not bind {item['filename']}")


def package_control_and_member(identity: dict[str, Any]) -> dict[str, str]:
    """Bind retained Debian control fields and payload bytes to selected ELFs."""
    archive = PACKAGE_ARCHIVES / identity["archive"]
    if sha256(archive) != identity["archive_sha256"]:
        raise RuntimeError(f"retained binary package hash mismatch: {archive}")
    control = subprocess.run(
        ["dpkg-deb", "-f", str(archive), "Source", "Version"],
        check=True, text=True, capture_output=True, timeout=30,
    ).stdout.splitlines()
    if control != ["Source: " + identity["control_source"], "Version: " + identity["control_version"]]:
        raise RuntimeError(f"retained binary package control identity mismatch: {archive}")
    result: dict[str, str] = {"archive_sha256": identity["archive_sha256"]}
    member = identity.get("member")
    if isinstance(member, str):
        first = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(archive)], stdout=subprocess.PIPE)
        assert first.stdout is not None
        second = subprocess.Popen(["tar", "-xOf", "-", member], stdin=first.stdout, stdout=subprocess.PIPE)
        first.stdout.close()
        assert second.stdout is not None
        digest = hashlib.sha256()
        for block in iter(lambda: second.stdout.read(1024 * 1024), b""):
            digest.update(block)
        if second.wait() != 0 or first.wait() != 0:
            raise RuntimeError(f"cannot stream binary package member: {archive}")
        if digest.hexdigest() != identity["member_sha256"]:
            raise RuntimeError(f"selected ELF relation mismatch: {archive}")
        result.update({"member": member, "member_sha256": digest.hexdigest()})
    return result


def source_tree_map(root: Path) -> dict[str, dict[str, Any]]:
    """Record direct source-tree members after safe isolated extraction."""
    entries: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        status = path.lstat()
        if path.is_symlink():
            entries[relative] = {"type": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            entries[relative] = {"type": "file", "bytes": status.st_size, "sha256": sha256(path)}
        elif not path.is_dir():
            raise RuntimeError(f"unsupported extracted source member: {path}")
    return entries


def main() -> int:
    receipt: dict[str, Any] = {"schema": "cix-ubuntu-codec-source-inputs-v1", "status": "started"}
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or not WORK_ROOT.is_dir() or WORK.exists():
            raise RuntimeError("unexpected repository/work root or existing job directory")
        inputs_before = static_input_hashes()
        tools_before = tool_identities()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        components = manifest.get("components")
        if manifest.get("status") != "prepared_not_acquired" or not isinstance(components, list) or len(components) != 2:
            raise RuntimeError("unsupported source input manifest")
        binaries_before = binary_input_hashes(manifest)
        existing = allocated_bytes(WORK_ROOT)
        if existing + WORK_CAP > SHARED_WORK_CAP:
            raise RuntimeError(f"aggregate work admission fails: {existing} + {WORK_CAP} > {SHARED_WORK_CAP}")
        declared = sum(item["bytes"] for component in components for item in component["files"])
        if declared + RECEIPT_RESERVE > WORK_CAP:
            raise RuntimeError("declared source downloads exceed the local work cap")
        WORK.mkdir(mode=0o700)
        DOWNLOADS.mkdir(mode=0o700)
        SOURCES.mkdir(mode=0o700)
        receipt.update({
            "input_sha256_before": inputs_before,
            "tool_identities_before": tools_before,
            "binary_package_sha256_before": binaries_before,
            "existing_work_allocated_bytes": existing,
            "work_cap_bytes": WORK_CAP,
            "shared_work_cap_bytes": SHARED_WORK_CAP,
            "declared_download_bytes": declared,
        })
        downloaded: dict[str, dict[str, Path]] = {}
        for component in components:
            name = component["source"]
            downloaded[name] = {item["role"]: download(component, item) for item in component["files"]}
            dsc_checksums(downloaded[name]["dsc"], component)
            if allocated_bytes(WORK) > WORK_CAP:
                raise RuntimeError("source downloads exceeded the local work cap")
        inspections: dict[str, dict[str, dict[str, int]]] = {}
        unpacked_bytes = 0
        for component in components:
            name = component["source"]
            inspected = {role: inspect_tar(downloaded[name][role]) for role in ("orig", "debian")}
            inspections[name] = inspected
            unpacked_bytes += sum(value["payload_bytes"] for value in inspected.values())
        if declared + unpacked_bytes + RECEIPT_RESERVE > WORK_CAP:
            raise RuntimeError("measured source extraction closure exceeds the local work cap")
        binary_bindings: dict[str, Any] = {}
        for component in components:
            binary_bindings[component["source"]] = {
                "runtime": package_control_and_member(component["selected_binary"]),
                "development": package_control_and_member(component["development_binary"]),
            }
        trees: dict[str, Any] = {}
        for component in components:
            name = component["source"]
            target = SOURCES / name
            subprocess.run(
                ["dpkg-source", "--no-preparation", "-x", str(downloaded[name]["dsc"]), str(target)],
                cwd=DOWNLOADS, check=True, stdin=subprocess.DEVNULL, timeout=120,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
            if not target.is_dir() or target.is_symlink():
                raise RuntimeError(f"source extraction did not create a direct directory: {target}")
            trees[name] = source_tree_map(target)
            if allocated_bytes(WORK) > WORK_CAP:
                raise RuntimeError("source extraction exceeded the local work cap")
        if allocated_bytes(WORK_ROOT) > SHARED_WORK_CAP:
            raise RuntimeError("source acquisition exceeded the shared work cap")
        inputs_after = static_input_hashes()
        if inputs_after != inputs_before:
            raise RuntimeError("runner, source tuple, spec, or provenance changed during acquisition")
        tools_after = tool_identities()
        if tools_after != tools_before:
            raise RuntimeError("descriptor or archive tool identity changed during acquisition")
        binaries_after = binary_input_hashes(manifest)
        if binaries_after != binaries_before:
            raise RuntimeError("retained binary package identities changed during acquisition")
        receipt.update({
            "status": "pass_source_inputs_retained_not_built",
            "input_sha256_after": inputs_after,
            "tool_identities_after": tools_after,
            "binary_package_sha256_after": binaries_after,
            "downloaded": {
                name: {role: {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
                       for role, path in roles.items()}
                for name, roles in downloaded.items()
            },
            "tar_inspection": inspections,
            "binary_bindings": binary_bindings,
            "source_trees": trees,
            "work_allocated_bytes": allocated_bytes(WORK),
            "non_claim": "Source inputs were retained and identity-bound only; no codec library was rebuilt or qualified for reproducibility."
        })
        return 0
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        write_receipt(receipt)


if __name__ == "__main__":
    raise SystemExit(main())
