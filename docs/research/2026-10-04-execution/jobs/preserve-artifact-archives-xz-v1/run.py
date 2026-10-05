#!/usr/bin/env python3
"""Lease-gated exact-byte XZ preservation of completed archive directories.

The inputs are already compressed qualification artifacts.  This job never
recompresses their decoded members: it stores each original .tar.gz byte stream
as a regular file in one XZ-compressed tar container.  Original directories are
removed only if reopening the container proves every path, mode, link, and
SHA-256 and the measured filesystem saving is at least MIN_RECLAIM_BYTES.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import tarfile
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
WORK = ROOT / "benchmark-work/native-rc-check-v1"
JOB = Path(__file__).resolve().parent
RAW = JOB / "raw"
RECEIPT = JOB / "receipt.json"
MANIFEST = JOB / "bundle.manifest.json"
RESTORE = JOB / "RESTORE.md"
BUNDLE_ROOT = WORK / "preserved-artifact-archives-xz-v1"
BUNDLE = BUNDLE_ROOT / "preserved-artifacts.tar.xz"
PARTIAL = BUNDLE.with_suffix(BUNDLE.suffix + ".partial")

# This is below the current 4 GB shared-work limit even before deletion.
OUTPUT_CAP_BYTES = 650_000_000
MIN_RECLAIM_BYTES = 150_000_000
XZ = Path("/usr/bin/xz")
SOURCES = (
    WORK / "preserved-sdk-artifacts-v1",
    WORK / "preserved-sdk-artifacts-v2",
    WORK / "preserved-consumer-artifacts-v1",
    WORK / "preserved-consumer-artifacts-v2",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocated(path: Path) -> int:
    return path.lstat().st_blocks * 512


def work_bytes() -> int:
    completed = subprocess.run(
        ["du", "-sx", "-B1", str(WORK)], check=True, text=True, capture_output=True
    )
    return int(completed.stdout.split()[0])


def source_relative(path: Path) -> str:
    return path.relative_to(WORK).as_posix()


def safe_link(path: Path, target: str) -> None:
    if not target or Path(target).is_absolute():
        raise RuntimeError("absolute or empty symlink target: " + source_relative(path))
    resolved = (path.parent / target).resolve(strict=False)
    try:
        resolved.relative_to(WORK)
    except ValueError as error:
        raise RuntimeError("symlink escapes selected artifact roots: " + source_relative(path)) from error


def no_active_users(path: Path) -> None:
    executable = shutil.which("lsof")
    if executable is None:
        raise RuntimeError("lsof is required to reject active artifact users")
    result = subprocess.run([executable, "+D", str(path)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inspect active artifact users: " + result.stderr.strip())
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError("active artifact user prevents replacement: " + result.stdout.splitlines()[0])


def collect_manifest() -> tuple[dict[str, Any], dict[tuple[int, int], str]]:
    entries: list[dict[str, Any]] = []
    selected: dict[tuple[int, int], int] = {}
    first: dict[tuple[int, int], str] = {}
    for root in SOURCES:
        if not root.is_dir() or root.is_symlink() or root.parent != WORK:
            raise RuntimeError("selected root is not an exact non-symlink child of work: " + str(root))
        paths = [root] + sorted(root.rglob("*"), key=lambda item: item.as_posix())
        for path in paths:
            row: dict[str, Any] = {"path": source_relative(path), "mode": stat.S_IMODE(path.lstat().st_mode)}
            if path.is_symlink():
                target = os.readlink(path)
                safe_link(path, target)
                row.update({"type": "symlink", "target": target})
            elif path.is_dir():
                row.update({"type": "directory"})
            elif path.is_file():
                detail = path.stat()
                inode = (detail.st_dev, detail.st_ino)
                row.update({
                    "type": "file", "logical_bytes": detail.st_size,
                    "allocated_bytes": detail.st_blocks * 512,
                    "sha256": sha256(path), "device": detail.st_dev,
                    "inode": detail.st_ino, "link_count": detail.st_nlink,
                })
                selected[inode] = selected.get(inode, 0) + 1
                first.setdefault(inode, row["path"])
            else:
                raise RuntimeError("unsupported selected entry: " + source_relative(path))
            entries.append(row)
    if not entries:
        raise RuntimeError("selected artifact roots are empty")
    # A hard link outside the four roots would make removal alter retained work.
    outside = {inode: [] for inode in selected}
    source_names = set(SOURCES)
    for path in WORK.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        detail = path.stat()
        inode = (detail.st_dev, detail.st_ino)
        if inode not in outside:
            continue
        if not any(path.is_relative_to(root) for root in source_names):
            outside[inode].append(str(path))
    for row in entries:
        if row["type"] != "file":
            continue
        inode = (row["device"], row["inode"])
        if outside[inode] or selected[inode] != row["link_count"]:
            raise RuntimeError("selected artifact hardlink escapes selected roots: " + row["path"])
    return {
        "schema": "cix-preserved-artifact-archives-xz-v1",
        "source_roots": [source_relative(root) for root in SOURCES],
        "entries": entries,
        "selected_allocated_bytes": (
            sum(row["allocated_bytes"] for row in entries if row["type"] == "file"
                and first[(row["device"], row["inode"])] == row["path"])
            + sum(allocated(WORK / row["path"]) for row in entries if row["type"] != "file")
        ),
        "output_cap_bytes": OUTPUT_CAP_BYTES,
        "minimum_reclaim_bytes": MIN_RECLAIM_BYTES,
        "compression": {"tool": str(XZ), "arguments": ["--threads=1", "--check=sha256", "--lzma2=dict=256MiB,pb=0"]},
    }, first


def encoded_manifest(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tar_info(name: str, row: dict[str, Any]) -> tarfile.TarInfo:
    result = tarfile.TarInfo(name)
    result.mode = row["mode"]
    result.uid = result.gid = 0
    result.uname = result.gname = ""
    result.mtime = 0
    return result


def write_bundle(manifest: dict[str, Any], first: dict[tuple[int, int], str]) -> None:
    if not XZ.is_file() or not os.access(XZ, os.X_OK):
        raise RuntimeError("pinned xz executable is unavailable")
    if BUNDLE_ROOT.exists() or BUNDLE.exists() or PARTIAL.exists():
        raise RuntimeError("refuse to overwrite preservation output")
    if work_bytes() + OUTPUT_CAP_BYTES >= 4_000_000_000:
        raise RuntimeError("bounded bundle output cannot be admitted in shared work")
    BUNDLE_ROOT.mkdir(mode=0o700)
    old_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
    if old_limit[1] != resource.RLIM_INFINITY and OUTPUT_CAP_BYTES > old_limit[1]:
        raise RuntimeError("bundle cap exceeds process file-size hard limit")

    def limit_output() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_CAP_BYTES, old_limit[1]))

    with PARTIAL.open("xb") as output:
        process = subprocess.Popen(
            [str(XZ), "--stdout", "--threads=1", "--check=sha256", "--lzma2=dict=256MiB,pb=0"],
            stdin=subprocess.PIPE, stdout=output, stderr=subprocess.PIPE, preexec_fn=limit_output,
        )
        try:
            assert process.stdin is not None
            with tarfile.open(fileobj=process.stdin, mode="w|") as archive:
                for row in manifest["entries"]:
                    info = tar_info(row["path"], row)
                    source = WORK / row["path"]
                    if row["type"] == "directory":
                        info.type = tarfile.DIRTYPE
                        archive.addfile(info)
                    elif row["type"] == "symlink":
                        info.type = tarfile.SYMTYPE
                        info.linkname = row["target"]
                        archive.addfile(info)
                    else:
                        inode = (row["device"], row["inode"])
                        if first[inode] != row["path"]:
                            info.type = tarfile.LNKTYPE
                            info.linkname = first[inode]
                            archive.addfile(info)
                        else:
                            info.size = row["logical_bytes"]
                            with source.open("rb") as body:
                                archive.addfile(info, body)
            process.stdin.close()
            assert process.stderr is not None
            stderr = process.stderr.read()
            returncode = process.wait()
            if returncode != 0:
                raise RuntimeError("xz failed or exceeded its output cap: " + stderr.decode("utf-8", "replace").strip())
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
    if PARTIAL.stat().st_size > OUTPUT_CAP_BYTES:
        raise RuntimeError("bundle exceeds declared output cap")
    PARTIAL.replace(BUNDLE)


def verify_bundle(manifest: dict[str, Any]) -> str:
    expected = manifest["entries"]
    with tarfile.open(BUNDLE, "r:xz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != [row["path"] for row in expected]:
            raise RuntimeError("bundle member order or path differs from manifest")
        first: dict[tuple[int, int], str] = {}
        for row, member in zip(expected, members):
            if stat.S_IMODE(member.mode) != row["mode"]:
                raise RuntimeError("bundle mode differs: " + row["path"])
            if row["type"] == "directory":
                if not member.isdir():
                    raise RuntimeError("bundle directory differs: " + row["path"])
            elif row["type"] == "symlink":
                if not member.issym() or member.linkname != row["target"]:
                    raise RuntimeError("bundle symlink differs: " + row["path"])
            else:
                inode = (row["device"], row["inode"])
                if inode in first:
                    if not member.islnk() or member.linkname != first[inode]:
                        raise RuntimeError("bundle hardlink differs: " + row["path"])
                else:
                    if not member.isfile():
                        raise RuntimeError("bundle regular file differs: " + row["path"])
                    stream = archive.extractfile(member)
                    if stream is None or hashlib.sha256(stream.read()).hexdigest() != row["sha256"]:
                        raise RuntimeError("bundle byte identity differs: " + row["path"])
                    first[inode] = row["path"]
    return sha256(BUNDLE)


def unchanged(manifest: dict[str, Any]) -> bool:
    current, _ = collect_manifest()
    return current == manifest


def references() -> list[str]:
    result = subprocess.run(
        ["rg", "-l", "preserved-(sdk-artifacts|consumer-artifacts)-v[12]", str(ROOT)],
        text=True, capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inventory artifact path references")
    # Receipts under raw/ are historical readers too: retain every direct
    # reference so the replacement receipt makes the restore dependency plain.
    return sorted(result.stdout.splitlines())


def write_restore_instructions(manifest: dict[str, Any]) -> None:
    text = """# Restore preserved artifact archives\n\nThe four original archive directories were replaced only after byte-for-byte verification.\nRestore them before opening a historical receipt that names an original archive path:\n\n```sh\ncd /home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1\ntar -xJf preserved-artifact-archives-xz-v1/preserved-artifacts.tar.xz\n```\n\nThis recreates these paths with their recorded modes and original gzip bytes:\n\n"""
    text += "\n".join("- `" + root + "`" for root in manifest["source_roots"])
    text += "\n\nThe bundle manifest and scheduler receipt record every original SHA-256.\n"
    RESTORE.write_text(text, encoding="utf-8")


def cleanup_bundle() -> None:
    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)


def main() -> None:
    receipt: dict[str, Any] = {"status": "started", "removed_originals": False}
    write_failure = not RECEIPT.exists()
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK.parent != ROOT / "benchmark-work":
            raise RuntimeError("unexpected repository or work root")
        if RECEIPT.exists() or MANIFEST.exists() or RESTORE.exists():
            raise RuntimeError("refuse to overwrite prior preservation evidence")
        for root in SOURCES:
            no_active_users(root)
        manifest, first = collect_manifest()
        tools = (Path(__file__), JOB / "spec.json", XZ)
        inputs_before = {str(path): sha256(path) for path in tools}
        receipt["input_sha256"] = inputs_before
        MANIFEST.write_bytes(encoded_manifest(manifest))
        before = work_bytes()
        reference_inventory = references()
        write_bundle(manifest, first)
        bundle_sha = verify_bundle(manifest)
        bundle_allocated = allocated(BUNDLE)
        reclaim = manifest["selected_allocated_bytes"] - bundle_allocated
        receipt.update({
            "source_manifest": str(MANIFEST), "source_manifest_sha256": sha256(MANIFEST),
            "selected_allocated_bytes": manifest["selected_allocated_bytes"],
            "bundle": str(BUNDLE), "bundle_sha256": bundle_sha,
            "bundle_logical_bytes": BUNDLE.stat().st_size, "bundle_allocated_bytes": bundle_allocated,
            "prospective_reclaim_bytes": reclaim, "retained_work_before_bytes": before,
            "referenced_paths_require_restore": reference_inventory,
            "restore_instruction": str(RESTORE),
        })
        if reclaim < MIN_RECLAIM_BYTES:
            cleanup_bundle()
            receipt.update({"status": "no_gain", "reason": "verified bundle did not meet minimum reclaim", "removed_originals": False})
            return
        for root in SOURCES:
            no_active_users(root)
        if not unchanged(manifest):
            raise RuntimeError("source archive tree changed after bundle verification")
        if inputs_before != {str(path): sha256(path) for path in tools}:
            raise RuntimeError("preservation recipe or compressor changed during operation")
        write_restore_instructions(manifest)
        for root in SOURCES:
            shutil.rmtree(root)
        if any(root.exists() for root in SOURCES):
            raise RuntimeError("original artifact directory removal was incomplete")
        after = work_bytes()
        actual_reclaim = before - after
        if actual_reclaim < MIN_RECLAIM_BYTES:
            raise RuntimeError("post-replacement reclaim fell below required minimum")
        receipt.update({"status": "pass", "removed_originals": True,
                        "retained_work_after_bytes": after, "actual_reclaim_bytes": actual_reclaim,
                        "restore_command": "cd " + str(WORK) + " && tar -xJf " + str(BUNDLE.relative_to(WORK))})
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        if write_failure:
            RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
