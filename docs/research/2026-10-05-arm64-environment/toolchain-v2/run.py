#!/usr/bin/env python3
"""Provision a verified, job-local AArch64 C++ toolchain; never mutate host apt state."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request

AREA = Path(__file__).resolve().parent
PROJECT = AREA.parents[3]
MANIFEST_PATH = AREA / "packages.json"
SPEC_PATH = AREA / "spec.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text())
WORK_PARENT = PROJECT / "benchmark-work/native-rc-check-v1"
WORK = WORK_PARENT / "platform-linux-arm64-user-toolchain-v2"
DOWNLOADS = WORK / "downloads"
PREFIX = WORK / "prefix"
RECEIPT = WORK / "receipt.json"
WORK_CAP = 600_000_000
PREFIX_CAP = 512_000_000
RECEIPT_RESERVE = 8_000_000
AGGREGATE_WORK_CAP = 4_000_000_000
QEMU_MEMBER = "usr/bin/qemu-aarch64-static"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allocated_bytes(root: Path) -> int:
    """Physical allocation, matching the reviewed shared-work accounting helper."""
    completed = subprocess.run(["du", "-sx", "-B1", str(root)], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return int(completed.stdout.split()[0])


def job_input_hashes() -> dict[str, str]:
    paths = [AREA / "run.py", SPEC_PATH, MANIFEST_PATH]
    return {str(path.relative_to(PROJECT)): sha256(path) for path in paths}


def host_tool_hashes() -> dict[str, str]:
    tools = [Path("/usr/bin/dpkg-deb"), Path("/usr/bin/file")]
    if any(not tool.is_file() for tool in tools):
        raise RuntimeError("required host inspection tool is absent")
    return {str(tool): sha256(tool) for tool in tools}


def cix_bridge_hashes() -> dict[str, str]:
    paths = [
        PROJECT / "rust/cix-native/codecs/paq/v215/CMakeLists.txt",
        PROJECT / "rust/cix-native/codecs/paq/v215/paq_v215_bridge.cpp",
        PROJECT / "rust/cix-native/codecs/paq/v216/CMakeLists.txt",
        PROJECT / "rust/cix-native/codecs/paq/v216/paq_v216_bridge.cpp",
    ]
    if any(not path.is_file() for path in paths):
        raise RuntimeError("expected CIX PAQ bridge source is absent")
    return {str(path.relative_to(PROJECT)): sha256(path) for path in paths}


def checked_capacity() -> None:
    actual = allocated_bytes(WORK)
    if actual > WORK_CAP:
        raise RuntimeError(f"job-local work exceeds {WORK_CAP} bytes: {actual}")
    if PREFIX.exists() and allocated_bytes(PREFIX) > PREFIX_CAP:
        raise RuntimeError(f"toolchain prefix exceeds {PREFIX_CAP} bytes")


def download(row: dict[str, object]) -> Path:
    url = str(row["url"])
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "archive.ubuntu.com" or not parsed.path.startswith("/ubuntu/pool/"):
        raise RuntimeError(f"manifest URL outside approved archive: {url}")
    destination = DOWNLOADS / str(row["filename"])
    partial = destination.with_suffix(destination.suffix + ".partial")
    expected_bytes = int(row["compressed_bytes"])
    if destination.exists() or partial.exists():
        raise RuntimeError(f"refusing to reuse package path: {destination}")
    received = 0
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("xb") as output:
        if response.geturl() != url:
            raise RuntimeError(f"redirected input rejected: {response.geturl()}")
        while True:
            chunk = response.read(min(1 << 20, expected_bytes + 1 - received))
            if not chunk:
                break
            received += len(chunk)
            if received > expected_bytes:
                raise RuntimeError(f"download exceeds declared size: {url}")
            digest.update(chunk)
            output.write(chunk)
    if received != expected_bytes or digest.hexdigest() != row["sha256"]:
        raise RuntimeError(f"input identity mismatch: {url}")
    partial.rename(destination)
    checked_capacity()
    return destination


def lexical_target(base: tuple[str, ...], target: str, label: str) -> tuple[str, ...]:
    value = PurePosixPath(target)
    if value.is_absolute() or not target:
        raise RuntimeError(f"unsafe archive link: {label} -> {target}")
    resolved = list(base)
    for part in value.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not resolved:
                raise RuntimeError(f"archive link escapes extraction root: {label} -> {target}")
            resolved.pop()
        else:
            resolved.append(part)
    return tuple(resolved)


def member_name(member: tarfile.TarInfo, previous_symlinks: set[tuple[str, ...]]) -> tuple[str, tuple[str, ...]]:
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"unsafe archive member path: {member.name}")
    parts = tuple(part for part in path.parts if part not in ("", "."))
    if not parts:
        if member.isdir():
            return ".", parts
        raise RuntimeError("empty archive member path")
    # An extractor can follow a previously created parent symlink while creating a later member.
    # Reject that write shape even when the link itself resolves within the prefix.
    if any(parts[:depth] in previous_symlinks for depth in range(1, len(parts))) or (parts in previous_symlinks and not member.issym()):
        raise RuntimeError(f"archive member writes through earlier symlink: {member.name}")
    if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
        raise RuntimeError(f"unsupported special archive member: {member.name}")
    if member.issym():
        lexical_target(parts[:-1], member.linkname, member.name)
        previous_symlinks.add(parts)
    elif member.islnk():
        lexical_target((), member.linkname, member.name)
    return "/".join(parts), parts


def inspect_deb(deb: Path, select_qemu: bool, previous_symlinks: set[tuple[str, ...]]) -> tuple[int, int]:
    """Validate all paths/links and measure payload before any prefix write."""
    process = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(deb)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    total = selected = 0
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            normalized, _ = member_name(member, previous_symlinks)
            if member.isfile():
                total += member.size
                if select_qemu and normalized == QEMU_MEMBER:
                    selected = member.size
    if process.wait() != 0:
        raise RuntimeError(f"cannot inspect Debian archive {deb}")
    if select_qemu and selected == 0:
        raise RuntimeError("qemu-user-static archive lacks qemu-aarch64-static")
    return total, selected if select_qemu else total


def extract_qemu_only(deb: Path) -> None:
    process = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", str(deb)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    selected = False
    previous_symlinks: set[tuple[str, ...]] = set()
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            normalized, _ = member_name(member, previous_symlinks)
            if normalized == QEMU_MEMBER:
                if not member.isfile() or selected:
                    raise RuntimeError("invalid qemu-aarch64-static archive member")
                destination = PREFIX / normalized
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                assert source is not None
                with destination.open("xb") as output:
                    shutil.copyfileobj(source, output, 1 << 20)
                destination.chmod(member.mode)
                selected = True
    if process.wait() != 0 or not selected:
        raise RuntimeError("cannot extract qemu-aarch64-static")


def command(argv: list[str]) -> str:
    completed = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=60, check=True, env={"PATH": f"{PREFIX}/usr/bin:/usr/bin:/bin"})
    return completed.stdout[:4096]


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    if WORK.exists():
        raise RuntimeError(f"refusing to reuse job work: {WORK}")
    existing_work_bytes = allocated_bytes(WORK_PARENT) if WORK_PARENT.exists() else 0
    if existing_work_bytes + WORK_CAP > AGGREGATE_WORK_CAP:
        raise RuntimeError(f"aggregate work admission fails: {existing_work_bytes} + {WORK_CAP} > {AGGREGATE_WORK_CAP}")
    WORK.mkdir(parents=True)
    DOWNLOADS.mkdir()
    receipt: dict[str, object] = {
        "schema": "cix-platform-linux-arm64-user-toolchain-v1",
        "status": "fail",
        "job_inputs_before": job_input_hashes(),
        "cix_bridge_inputs_before": cix_bridge_hashes(),
        "host_tool_inputs_before": host_tool_hashes(),
        "compressed_total_bytes": MANIFEST["compressed_total_bytes"],
        "known_installed_total_bytes": MANIFEST["known_installed_total_bytes"],
        "installed_size_missing_packages": MANIFEST["installed_size_missing_packages"],
        "work_cap_bytes": WORK_CAP,
        "prefix_cap_bytes": PREFIX_CAP,
        "existing_work_bytes_before": existing_work_bytes,
        "aggregate_work_cap_bytes": AGGREGATE_WORK_CAP,
    }
    try:
        rows = MANIFEST["packages"]
        declared = sum(int(row["compressed_bytes"]) for row in rows)
        if declared != MANIFEST["compressed_total_bytes"]:
            raise RuntimeError("manifest compressed total is inconsistent")
        if declared + PREFIX_CAP + RECEIPT_RESERVE > WORK_CAP:
            raise RuntimeError("declared archive closure cannot fit the job capacity")
        downloaded = [(row, download(row)) for row in rows]
        archive_symlinks: set[tuple[str, ...]] = set()
        inspected = {}
        for row, path in downloaded:
            inspected[path.name] = inspect_deb(path, row["package"] == "qemu-user-static", archive_symlinks)
        payloads = {name: values[0] for name, values in inspected.items()}
        extracted_payloads = {name: values[1] for name, values in inspected.items()}
        extracted_total = sum(extracted_payloads.values())
        receipt["archive_payload_bytes"] = payloads
        receipt["selected_extraction_payload_bytes"] = extracted_payloads
        receipt["selected_extraction_payload_total_bytes"] = extracted_total
        if declared + extracted_total + RECEIPT_RESERVE > WORK_CAP:
            raise RuntimeError("measured selected extraction closure cannot fit before extraction")
        PREFIX.mkdir()
        for row, deb in downloaded:
            if row["package"] == "qemu-user-static":
                extract_qemu_only(deb)
            else:
                subprocess.run(["dpkg-deb", "--extract", str(deb), str(PREFIX)], check=True, timeout=60)
            checked_capacity()
        compiler = PREFIX / "usr/bin/aarch64-linux-gnu-g++"
        qemu = PREFIX / "usr/bin/qemu-aarch64-static"
        sysroot = PREFIX
        if not compiler.is_file() or not qemu.is_file() or not (PREFIX / "usr/aarch64-linux-gnu").is_dir():
            raise RuntimeError("relocated compiler, qemu, or AArch64 sysroot missing")
        probe = WORK / "probe.cc"
        binary = WORK / "probe-aarch64"
        probe.write_text("int main() { return 0; }\n")
        compiler_result = command([str(compiler), f"--sysroot={sysroot}", "-o", str(binary), str(probe)])
        qemu_result = command([str(qemu), "--version"])
        file_result = command(["file", str(binary)])
        if "aarch64" not in file_result.lower():
            raise RuntimeError(f"cross compiler did not emit AArch64 ELF: {file_result}")
        receipt["probes"] = {
            "compiler_with_sysroot_prefix": compiler_result,
            "qemu_version": qemu_result,
            "output_file": file_result,
        }
        receipt["package_identities"] = [{
            "package": row["package"], "version": row["version"], "url": row["url"],
            "compressed_bytes": row["compressed_bytes"], "sha256": row["sha256"],
            "archive_sha256": sha256(path), "archive_payload_bytes": payloads[path.name],
            "selected_extraction_payload_bytes": extracted_payloads[path.name],
        } for row, path in downloaded]
        receipt["relocated_compiler_sha256"] = sha256(compiler)
        receipt["relocated_qemu_sha256"] = sha256(qemu)
        receipt["prefix_bytes"] = allocated_bytes(PREFIX)
        receipt["work_bytes"] = allocated_bytes(WORK)
        receipt["job_inputs_after"] = job_input_hashes()
        receipt["cix_bridge_inputs_after"] = cix_bridge_hashes()
        receipt["host_tool_inputs_after"] = host_tool_hashes()
        if receipt["job_inputs_before"] != receipt["job_inputs_after"]:
            raise RuntimeError("job runner, manifest, or spec changed during provisioning")
        if receipt["cix_bridge_inputs_before"] != receipt["cix_bridge_inputs_after"]:
            raise RuntimeError("CIX PAQ bridge inputs changed during provisioning")
        if receipt["host_tool_inputs_before"] != receipt["host_tool_inputs_after"]:
            raise RuntimeError("host inspection tools changed during provisioning")
        receipt["status"] = "pass"
    except Exception as error:
        receipt["error"] = str(error)
        raise
    finally:
        checked_capacity()
        RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
