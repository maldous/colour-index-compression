#!/usr/bin/env python3
"""Preserve four inactive native-work trees before returning their space.

The archive is a byte-preserving cache replacement.  It is created, bounded,
and reopened before any source root is removed.  The original roots remain if
the compressed result does not meet the required reclaim threshold.
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
RECEIPT = JOB / "receipt.json"
MANIFEST = JOB / "manifest.json"
RESTORE = JOB / "RESTORE.md"
BUNDLE_DIR = WORK / "preserve-inactive-native-trees-v1"
BUNDLE = BUNDLE_DIR / "inactive-native-trees.tar.xz"
PARTIAL = BUNDLE.with_suffix(BUNDLE.suffix + ".partial")
XZ = Path("/usr/bin/xz")
LIMIT = 4_000_000_000
OUTPUT_CAP = 180_000_000
MIN_RECLAIM = 100_000_000
SOURCES = (
    WORK / "python-host-sdk-v1",
    WORK / "native-final-source-v3",
    WORK / "runtime-closure-v1",
    WORK / "runtime-closure-v2",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def work_bytes() -> int:
    completed = subprocess.run(
        ["du", "-sx", "-B1", str(WORK)], check=True, text=True, capture_output=True
    )
    return int(completed.stdout.split()[0])


def relative(path: Path) -> str:
    return path.relative_to(WORK).as_posix()


def no_active_users(root: Path) -> None:
    lsof = shutil.which("lsof")
    if lsof is None:
        raise RuntimeError("lsof is required to reject active preservation inputs")
    result = subprocess.run([lsof, "+D", str(root)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inspect active users: " + result.stderr.strip())
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError("active artifact user prevents preservation: " + result.stdout.splitlines()[0])


def collect_manifest() -> tuple[dict[str, Any], dict[tuple[int, int], str]]:
    entries: list[dict[str, Any]] = []
    appearances: dict[tuple[int, int], int] = {}
    first: dict[tuple[int, int], str] = {}
    selected: set[tuple[int, int]] = set()
    non_file_allocated = 0
    for root in SOURCES:
        if not root.is_dir() or root.is_symlink() or root.parent != WORK:
            raise RuntimeError("source is not an exact work-root child: " + str(root))
        for path in [root, *sorted(root.rglob("*"), key=lambda item: item.as_posix())]:
            detail = path.lstat()
            row: dict[str, Any] = {"path": relative(path), "mode": stat.S_IMODE(detail.st_mode)}
            if path.is_symlink():
                target = os.readlink(path)
                if not target:
                    raise RuntimeError("empty symlink target: " + relative(path))
                # This is an exact preservation archive, so record the link
                # text without resolving it.  The Python host SDK deliberately
                # has /usr/bin/python3 links which must round-trip unchanged.
                row.update({"type": "symlink", "target": target})
                non_file_allocated += detail.st_blocks * 512
            elif path.is_dir():
                row["type"] = "directory"
                non_file_allocated += detail.st_blocks * 512
            elif path.is_file():
                inode = (detail.st_dev, detail.st_ino)
                row.update({
                    "type": "file", "logical_bytes": detail.st_size,
                    "allocated_bytes": detail.st_blocks * 512, "sha256": sha256(path),
                    "device": detail.st_dev, "inode": detail.st_ino, "link_count": detail.st_nlink,
                })
                appearances[inode] = appearances.get(inode, 0) + 1
                if inode not in selected:
                    selected.add(inode)
                    first[inode] = row["path"]
            else:
                raise RuntimeError("unsupported source entry: " + relative(path))
            entries.append(row)
    if not entries:
        raise RuntimeError("selected roots are empty")

    # A selected inode may not be shared with retained work: removing a source
    # root must have a predictable reclaim and must not alter another cache.
    outside: dict[tuple[int, int], list[dict[str, Any]]] = {inode: [] for inode in selected}
    for path in WORK.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        detail = path.stat()
        inode = (detail.st_dev, detail.st_ino)
        if inode in outside and not any(path.is_relative_to(root) for root in SOURCES):
            outside[inode].append({
                "path": relative(path), "mode": stat.S_IMODE(path.lstat().st_mode),
                "logical_bytes": detail.st_size, "allocated_bytes": detail.st_blocks * 512,
                "sha256": sha256(path), "device": detail.st_dev, "inode": detail.st_ino,
                "link_count": detail.st_nlink,
            })
    for row in entries:
        if row["type"] != "file":
            continue
        inode = (row["device"], row["inode"])
        if appearances[inode] + len(outside[inode]) != row["link_count"]:
            raise RuntimeError("selected inode link count is not fully accounted for: " + row["path"])

    # The archive holds every selected byte, including files whose inode also
    # has retained names.  Those shared blocks remain allocated after removal,
    # so do not promise them as reclaimed capacity.
    reclaimable_file_bytes = sum(
        row["allocated_bytes"]
        for row in entries
        if row["type"] == "file"
        and first[(row["device"], row["inode"])] == row["path"]
        and not outside[(row["device"], row["inode"])]
    )
    external_links = [
        {"selected_path": first[inode], "retained_paths": paths}
        for inode, paths in sorted(outside.items(), key=lambda item: first[item[0]]) if paths
    ]

    return ({
        "schema": "cix.preserve-inactive-native-trees.v1",
        "source_roots": [relative(root) for root in SOURCES],
        "entries": entries,
        "selected_allocated_bytes": non_file_allocated + sum(
            row["allocated_bytes"]
            for row in entries
            if row["type"] == "file" and first[(row["device"], row["inode"])] == row["path"]
        ),
        "reclaimable_selected_allocated_bytes": non_file_allocated + reclaimable_file_bytes,
        "external_hardlinks": external_links,
        "output_cap_bytes": OUTPUT_CAP,
        "minimum_reclaim_bytes": MIN_RECLAIM,
        "compression": {"tool": str(XZ), "arguments": ["--threads=1", "--check=sha256", "--lzma2=dict=64MiB,pb=0"]},
    }, first)


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()


def info(name: str, row: dict[str, Any]) -> tarfile.TarInfo:
    entry = tarfile.TarInfo(name)
    entry.mode = row["mode"]
    entry.uid = entry.gid = 0
    entry.uname = entry.gname = ""
    entry.mtime = 0
    return entry


def write_bundle(manifest: dict[str, Any], first: dict[tuple[int, int], str]) -> None:
    if not XZ.is_file() or not os.access(XZ, os.X_OK):
        raise RuntimeError("pinned xz is unavailable")
    if BUNDLE_DIR.exists() or BUNDLE.exists() or PARTIAL.exists():
        raise RuntimeError("refusing to overwrite preservation output")
    if work_bytes() + OUTPUT_CAP >= LIMIT:
        raise RuntimeError("bounded archive cannot be admitted in shared work")
    previous = resource.getrlimit(resource.RLIMIT_FSIZE)
    if previous[1] != resource.RLIM_INFINITY and OUTPUT_CAP > previous[1]:
        raise RuntimeError("output cap exceeds file-size hard limit")

    def cap_output() -> None:
        resource.setrlimit(resource.RLIMIT_FSIZE, (OUTPUT_CAP, previous[1]))

    BUNDLE_DIR.mkdir(mode=0o700)
    with PARTIAL.open("xb") as output:
        process = subprocess.Popen(
            [str(XZ), "--stdout", "--threads=1", "--check=sha256", "--lzma2=dict=64MiB,pb=0"],
            stdin=subprocess.PIPE, stdout=output, stderr=subprocess.PIPE, preexec_fn=cap_output,
        )
        try:
            assert process.stdin is not None
            with tarfile.open(fileobj=process.stdin, mode="w|") as archive:
                for row in manifest["entries"]:
                    entry = info(row["path"], row)
                    path = WORK / row["path"]
                    if row["type"] == "directory":
                        entry.type = tarfile.DIRTYPE
                        archive.addfile(entry)
                    elif row["type"] == "symlink":
                        entry.type = tarfile.SYMTYPE
                        entry.linkname = row["target"]
                        archive.addfile(entry)
                    else:
                        inode = (row["device"], row["inode"])
                        if first[inode] != row["path"]:
                            entry.type = tarfile.LNKTYPE
                            entry.linkname = first[inode]
                            archive.addfile(entry)
                        else:
                            entry.size = row["logical_bytes"]
                            with path.open("rb") as body:
                                archive.addfile(entry, body)
            process.stdin.close()
            assert process.stderr is not None
            stderr = process.stderr.read().decode("utf-8", "replace").strip()
            if process.wait() != 0:
                raise RuntimeError("xz failed or reached output cap: " + stderr)
        except BaseException:
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
    if PARTIAL.stat().st_size > OUTPUT_CAP:
        raise RuntimeError("archive exceeds output cap")
    PARTIAL.replace(BUNDLE)


def verify_bundle(manifest: dict[str, Any]) -> str:
    with tarfile.open(BUNDLE, "r:xz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != [row["path"] for row in manifest["entries"]]:
            raise RuntimeError("archive member order differs from manifest")
        first: dict[tuple[int, int], str] = {}
        for row, member in zip(manifest["entries"], members):
            if stat.S_IMODE(member.mode) != row["mode"]:
                raise RuntimeError("archive mode differs: " + row["path"])
            if row["type"] == "directory" and not member.isdir():
                raise RuntimeError("archive directory differs: " + row["path"])
            elif row["type"] == "symlink":
                if not member.issym() or member.linkname != row["target"]:
                    raise RuntimeError("archive symlink differs: " + row["path"])
            elif row["type"] == "file":
                inode = (row["device"], row["inode"])
                if inode in first:
                    if not member.islnk() or member.linkname != first[inode]:
                        raise RuntimeError("archive hardlink differs: " + row["path"])
                else:
                    body = archive.extractfile(member)
                    if not member.isfile() or body is None or hashlib.sha256(body.read()).hexdigest() != row["sha256"]:
                        raise RuntimeError("archive bytes differ: " + row["path"])
                    first[inode] = row["path"]
    return sha256(BUNDLE)


def unchanged(manifest: dict[str, Any]) -> bool:
    current, _ = collect_manifest()
    return current == manifest


def external_links_unchanged(manifest: dict[str, Any], after_selected_removal: bool = False) -> bool:
    for group in manifest["external_hardlinks"]:
        selected = next(row for row in manifest["entries"] if row["path"] == group["selected_path"])
        selected_link_count = sum(
            1 for row in manifest["entries"]
            if row["type"] == "file"
            and (row["device"], row["inode"]) == (selected["device"], selected["inode"])
        )
        for expected in group["retained_paths"]:
            path = WORK / expected["path"]
            if path.is_symlink() or not path.is_file():
                return False
            detail = path.stat()
            expected_link_count = expected["link_count"] - selected_link_count if after_selected_removal else expected["link_count"]
            if {
                "mode": stat.S_IMODE(path.lstat().st_mode), "logical_bytes": detail.st_size,
                "allocated_bytes": detail.st_blocks * 512, "sha256": sha256(path),
                "device": detail.st_dev, "inode": detail.st_ino, "link_count": detail.st_nlink,
            } != {
                **{key: expected[key] for key in ("mode", "logical_bytes", "allocated_bytes", "sha256", "device", "inode")},
                "link_count": expected_link_count,
            }:
                return False
    return True


def references() -> list[str]:
    expression = "python-host-sdk-v1|native-final-source-v3|runtime-closure-v1|runtime-closure-v2"
    result = subprocess.run(["rg", "-l", expression, str(ROOT)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inventory readers")
    return sorted(result.stdout.splitlines())


def write_restore(manifest: dict[str, Any]) -> None:
    roots = "\n".join("- `" + root + "`" for root in manifest["source_roots"])
    RESTORE.write_text(
        "# Restore inactive native trees\n\n"
        "The roots below were archived only after path, mode, symlink, hardlink, and SHA-256 verification. "
        "Restore them before rerunning a historical job that names one of their paths.\n\n"
        "```sh\ncd " + str(WORK) + "\ntar -xJf " + str(BUNDLE.relative_to(WORK)) + "\n```\n\n"
        "This restores:\n\n" + roots + "\n\n"
        "Some archived files may also have retained hardlink names outside these roots. "
        "Those paths are never modified by restoration: extraction creates an independent byte-identical "
        "file where an external hardlink cannot be re-established without changing retained work.\n",
        encoding="utf-8",
    )


def remove_bundle() -> None:
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)


def main() -> None:
    receipt: dict[str, Any] = {"status": "started", "removed_originals": False}
    create_receipt = not RECEIPT.exists()
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK.parent != ROOT / "benchmark-work":
            raise RuntimeError("unexpected repository or work root")
        if any(path.exists() for path in (RECEIPT, MANIFEST, RESTORE)):
            raise RuntimeError("refusing to overwrite preservation evidence")
        for root in SOURCES:
            no_active_users(root)
        manifest, first = collect_manifest()
        inputs = {str(path): sha256(path) for path in (Path(__file__), JOB / "spec.json", XZ)}
        MANIFEST.write_bytes(manifest_bytes(manifest))
        before = work_bytes()
        reader_paths = references()
        write_bundle(manifest, first)
        bundle_sha = verify_bundle(manifest)
        allocated = BUNDLE.lstat().st_blocks * 512
        prospective = manifest["reclaimable_selected_allocated_bytes"] - allocated
        receipt.update({
            "source_manifest": str(MANIFEST), "source_manifest_sha256": sha256(MANIFEST),
            "source_allocated_bytes": manifest["selected_allocated_bytes"],
            "reclaimable_source_allocated_bytes": manifest["reclaimable_selected_allocated_bytes"],
            "external_hardlinks": manifest["external_hardlinks"],
            "bundle": str(BUNDLE), "bundle_sha256": bundle_sha,
            "bundle_logical_bytes": BUNDLE.stat().st_size, "bundle_allocated_bytes": allocated,
            "prospective_reclaim_bytes": prospective, "work_before_bytes": before,
            "reader_paths_require_restore": reader_paths, "restore_instruction": str(RESTORE),
        })
        if prospective < MIN_RECLAIM:
            remove_bundle()
            receipt.update({"status": "no_gain", "reason": "verified archive did not meet minimum reclaim"})
            return
        for root in SOURCES:
            no_active_users(root)
        if not unchanged(manifest) or not external_links_unchanged(manifest):
            raise RuntimeError("source changed after archive verification")
        if inputs != {str(path): sha256(path) for path in (Path(__file__), JOB / "spec.json", XZ)}:
            raise RuntimeError("recipe or compressor changed during preservation")
        write_restore(manifest)
        for root in SOURCES:
            shutil.rmtree(root)
        if any(root.exists() for root in SOURCES):
            raise RuntimeError("source removal incomplete")
        if not external_links_unchanged(manifest, after_selected_removal=True):
            raise RuntimeError("retained external hardlink changed during selected-root removal")
        after = work_bytes()
        actual = before - after
        if actual < MIN_RECLAIM:
            raise RuntimeError("post-replacement reclaim fell below minimum")
        receipt.update({
            "status": "pass", "removed_originals": True, "work_after_bytes": after,
            "actual_reclaim_bytes": actual,
            "restore_command": "cd " + str(WORK) + " && tar -xJf " + str(BUNDLE.relative_to(WORK)),
        })
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        if create_receipt:
            RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
